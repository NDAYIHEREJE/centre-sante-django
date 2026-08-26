"""
Vues réservées à l'espace Administrateur (rôle ADMINISTRATEUR) :
gestion des comptes et rôles, tableau de bord, supervision transverse
des rendez-vous, recherche patient, référentiel médicaments.
"""
from datetime import timedelta

from django.db import transaction
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError, NotFound

from .models import (
    Utilisateur, Patient, Medecin, RendezVous, Consultation,
    Prescription, Medicament, DisponibiliteMedecin,
)
from .permissions import role_requis

EST_ADMIN = role_requis(Utilisateur.Role.ADMINISTRATEUR)


# =========================================================
# Gestion des comptes et des rôles
# =========================================================

@api_view(["GET", "POST"])
@permission_classes([EST_ADMIN])
def utilisateurs_collection(request):
    if request.method == "GET":
        qs = Utilisateur.objects.all().order_by("-date_creation")
        role = request.query_params.get("role")
        actif = request.query_params.get("actif")
        if role:
            qs = qs.filter(role=role)
        if actif is not None:
            qs = qs.filter(is_active=(actif == "true"))
        return Response([
            {
                "id": u.id, "email": u.email, "nom": u.nom, "prenom": u.prenom,
                "role": u.role, "is_active": u.is_active,
                "date_creation": u.date_creation.isoformat(),
            }
            for u in qs
        ])

    # POST — création d'un compte, tout rôle confondu
    donnees = request.data
    role = donnees.get("role")
    if role not in Utilisateur.Role.values:
        raise ValidationError({"detail": "Rôle invalide"})
    if not donnees.get("mot_de_passe"):
        raise ValidationError({"detail": "Un mot de passe initial est requis"})
    if Utilisateur.objects.filter(email=donnees.get("email")).exists():
        raise ValidationError({"detail": "Un compte existe déjà avec cet email"})

    with transaction.atomic():
        utilisateur = Utilisateur.objects.create_user(
            email=donnees["email"],
            password=donnees["mot_de_passe"],
            nom=donnees.get("nom", ""),
            prenom=donnees.get("prenom", ""),
            role=role,
        )
        if role == Utilisateur.Role.PATIENT:
            Patient.objects.create(utilisateur=utilisateur)
        elif role == Utilisateur.Role.MEDECIN:
            Medecin.objects.create(
                utilisateur=utilisateur,
                specialite=donnees.get("specialite") or "Non renseignée",
            )

    return Response({"id": utilisateur.id, "message": "Compte créé"}, status=201)


@api_view(["PATCH"])
@permission_classes([EST_ADMIN])
def utilisateur_detail(request, utilisateur_id):
    try:
        utilisateur = Utilisateur.objects.get(id=utilisateur_id)
    except Utilisateur.DoesNotExist:
        raise NotFound("Utilisateur introuvable")

    donnees = request.data
    for champ in ("nom", "prenom", "telephone"):
        if champ in donnees:
            setattr(utilisateur, champ, donnees[champ])

    if "is_active" in donnees:
        utilisateur.is_active = bool(donnees["is_active"])

    nouveau_role = donnees.get("role")
    if nouveau_role and nouveau_role != utilisateur.role:
        if nouveau_role not in Utilisateur.Role.values:
            raise ValidationError({"detail": "Rôle invalide"})
        utilisateur.role = nouveau_role
        # Création du profil manquant si on promeut vers Patient/Médecin.
        # (Par simplicité, un profil existant lors d'un changement de rôle
        # n'est jamais supprimé automatiquement — évite toute perte de données.)
        if nouveau_role == Utilisateur.Role.PATIENT and not Patient.objects.filter(utilisateur=utilisateur).exists():
            Patient.objects.create(utilisateur=utilisateur)
        elif nouveau_role == Utilisateur.Role.MEDECIN and not Medecin.objects.filter(utilisateur=utilisateur).exists():
            Medecin.objects.create(utilisateur=utilisateur, specialite="Non renseignée")

    utilisateur.save()
    return Response({"id": utilisateur.id, "message": "Utilisateur mis à jour"})


@api_view(["POST"])
@permission_classes([EST_ADMIN])
def reinitialiser_mot_de_passe(request, utilisateur_id):
    try:
        utilisateur = Utilisateur.objects.get(id=utilisateur_id)
    except Utilisateur.DoesNotExist:
        raise NotFound("Utilisateur introuvable")

    nouveau = request.data.get("nouveau_mot_de_passe")
    if not nouveau or len(nouveau) < 6:
        raise ValidationError({"detail": "Le nouveau mot de passe doit contenir au moins 6 caractères"})

    utilisateur.set_password(nouveau)
    utilisateur.save(update_fields=["password"])
    return Response({"message": "Mot de passe réinitialisé"})


# =========================================================
# Tableau de bord — indicateurs clés
# =========================================================

@api_view(["GET"])
@permission_classes([EST_ADMIN])
def tableau_de_bord(request):
    maintenant = timezone.now()
    aujourdhui = timezone.localdate()
    debut_semaine = aujourdhui - timedelta(days=aujourdhui.weekday())
    fin_semaine = debut_semaine + timedelta(days=6)

    def compter_par_statut(queryset):
        resultat = {s: 0 for s in RendezVous.Statut.values}
        for rdv in queryset.values_list("statut", flat=True):
            resultat[rdv] = resultat.get(rdv, 0) + 1
        return resultat

    rdv_aujourdhui = RendezVous.objects.filter(date_heure__date=aujourdhui)
    rdv_semaine = RendezVous.objects.filter(
        date_heure__date__gte=debut_semaine, date_heure__date__lte=fin_semaine
    )

    nouveaux_patients_7j = Utilisateur.objects.filter(
        role=Utilisateur.Role.PATIENT, date_creation__gte=maintenant - timedelta(days=7)
    ).count()

    rdv_annules_30j = RendezVous.objects.filter(
        statut=RendezVous.Statut.ANNULE, date_creation__gte=maintenant - timedelta(days=30)
    ).count()

    # Taux d'occupation par médecin sur la semaine en cours.
    taux_occupation = []
    for medecin in Medecin.objects.select_related("utilisateur").all():
        total_creneaux = 0
        for dispo in DisponibiliteMedecin.objects.filter(medecin=medecin):
            minutes_dispo = (
                dispo.heure_fin.hour * 60 + dispo.heure_fin.minute
                - dispo.heure_debut.hour * 60 - dispo.heure_debut.minute
            )
            if dispo.duree_creneau_minutes > 0:
                total_creneaux += max(minutes_dispo // dispo.duree_creneau_minutes, 0)

        rdv_pris = RendezVous.objects.filter(
            medecin=medecin, date_heure__date__gte=debut_semaine, date_heure__date__lte=fin_semaine
        ).exclude(statut=RendezVous.Statut.ANNULE).count()

        taux = round((rdv_pris / total_creneaux) * 100, 1) if total_creneaux > 0 else 0.0
        taux_occupation.append({
            "medecin": f"Dr {medecin.utilisateur.prenom} {medecin.utilisateur.nom}",
            "specialite": medecin.specialite,
            "creneaux_semaine": total_creneaux,
            "rdv_pris_semaine": rdv_pris,
            "taux_occupation_pct": taux,
        })

    # Alerte : demandes en attente depuis plus de 48h.
    seuil_alerte = maintenant - timedelta(hours=48)
    demandes_en_attente_longues = RendezVous.objects.filter(
        statut=RendezVous.Statut.EN_ATTENTE, date_creation__lt=seuil_alerte
    ).count()

    return Response({
        "rdv_aujourdhui": compter_par_statut(rdv_aujourdhui),
        "rdv_semaine": compter_par_statut(rdv_semaine),
        "nouveaux_patients_7j": nouveaux_patients_7j,
        "rdv_annules_30j": rdv_annules_30j,
        "taux_occupation_par_medecin": taux_occupation,
        "alertes": {
            "demandes_en_attente_plus_48h": demandes_en_attente_longues,
            # Aucun conflit de créneau n'est possible par construction : la contrainte
            # UNIQUE(medecin, date_heure) en base l'empêche (voir ENF-04, §3.7).
            "conflits_creneaux": 0,
        },
    })


# =========================================================
# Supervision transverse — recherche et dossier patient
# =========================================================

@api_view(["GET"])
@permission_classes([EST_ADMIN])
def rechercher_patients(request):
    terme = request.query_params.get("q", "").strip()
    qs = Patient.objects.select_related("utilisateur").all()
    if terme:
        qs = qs.filter(utilisateur__nom__icontains=terme) | qs.filter(utilisateur__prenom__icontains=terme) \
            | qs.filter(utilisateur__email__icontains=terme)
    return Response([
        {
            "id": p.utilisateur_id, "nom": p.utilisateur.nom, "prenom": p.utilisateur.prenom,
            "email": p.utilisateur.email,
        }
        for p in qs[:30]
    ])


@api_view(["GET"])
@permission_classes([EST_ADMIN])
def dossier_patient(request, patient_id):
    try:
        patient = Patient.objects.select_related("utilisateur").get(utilisateur_id=patient_id)
    except Patient.DoesNotExist:
        raise NotFound("Patient introuvable")

    rendez_vous = RendezVous.objects.filter(patient=patient).order_by("-date_heure")
    prescriptions = Prescription.objects.filter(
        consultation__rendez_vous__patient=patient
    ).select_related("consultation").prefetch_related("lignes__medicament")

    return Response({
        "patient": {
            "id": patient.utilisateur_id, "nom": patient.utilisateur.nom,
            "prenom": patient.utilisateur.prenom, "email": patient.utilisateur.email,
        },
        "rendez_vous": [
            {
                "id": r.id, "medecin_id": r.medecin_id, "date_heure": r.date_heure.isoformat(),
                "statut": r.statut, "motif": r.motif,
            }
            for r in rendez_vous
        ],
        "prescriptions": [
            {
                "id": pr.id, "date_prescription": pr.date_prescription.isoformat(),
                "lignes": [
                    {"medicament": l.medicament.nom, "posologie": l.posologie}
                    for l in pr.lignes.all()
                ],
            }
            for pr in prescriptions
        ],
    })


# =========================================================
# Référentiel médicaments — CRUD
# =========================================================

@api_view(["POST"])
@permission_classes([EST_ADMIN])
def creer_medicament(request):
    nom = request.data.get("nom", "").strip()
    if not nom:
        raise ValidationError({"detail": "Le nom du médicament est requis"})
    medicament = Medicament.objects.create(nom=nom, description=request.data.get("description", ""))
    return Response({"id": medicament.id, "nom": medicament.nom}, status=201)


@api_view(["DELETE"])
@permission_classes([EST_ADMIN])
def supprimer_medicament(request, medicament_id):
    try:
        Medicament.objects.get(id=medicament_id).delete()
    except Medicament.DoesNotExist:
        raise NotFound("Médicament introuvable")
    return Response(status=204)
