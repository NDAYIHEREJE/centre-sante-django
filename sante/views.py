"""
Vues de l'API — Gestion d'un centre de santé / clinique (portail patient).
Équivalent Django du main.py de la version FastAPI (mêmes routes, même contrat d'API,
pour rester compatible avec le frontend déjà livré).
"""
from datetime import datetime

from django.db import transaction
from django.shortcuts import render
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError, NotFound, PermissionDenied
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate

from .models import (
    Utilisateur, Patient, Medecin, DisponibiliteMedecin,
    RendezVous, Consultation, Prescription, LignePrescription, Medicament,
)
from .serializers import (
    UtilisateurSerializer, InscriptionPatientSerializer,
    RendezVousSerializer, DemandeRDVSerializer,
    PrescriptionInSerializer, PrescriptionOutSerializer,
)
from .permissions import role_requis
from . import services


def accueil(request):
    """Sert la page d'accueil du frontend (index.html) — fusion frontend/backend."""
    return render(request, "index.html")


# =========================================================
# Authentification — EF-01 : Inscription / Connexion
# =========================================================

@api_view(["POST"])
@permission_classes([AllowAny])
def inscription_patient(request):
    serializer = InscriptionPatientSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    donnees = serializer.validated_data

    if Utilisateur.objects.filter(email=donnees["email"]).exists():
        raise ValidationError({"detail": "Un compte existe déjà avec cet email"})

    with transaction.atomic():
        utilisateur = Utilisateur.objects.create_user(
            email=donnees["email"],
            password=donnees["mot_de_passe"],
            nom=donnees["nom"],
            prenom=donnees["prenom"],
            telephone=donnees.get("telephone", ""),
            role=Utilisateur.Role.PATIENT,
        )
        Patient.objects.create(
            utilisateur=utilisateur,
            date_naissance=donnees.get("date_naissance"),
            adresse=donnees.get("adresse", ""),
        )

    return Response(UtilisateurSerializer(utilisateur).data, status=201)


@api_view(["POST"])
@permission_classes([AllowAny])
def connexion(request):
    """
    Accepte le même format que l'OAuth2PasswordRequestForm de FastAPI
    (form-urlencoded avec les champs 'username' et 'password'), pour rester
    compatible avec le frontend déjà livré.
    """
    email = request.data.get("username") or request.data.get("email")
    mot_de_passe = request.data.get("password")

    utilisateur = authenticate(request, username=email, password=mot_de_passe)
    if utilisateur is None:
        return Response({"detail": "Email ou mot de passe incorrect"}, status=401)
    if not utilisateur.is_active:
        return Response({"detail": "Compte désactivé"}, status=403)

    token = RefreshToken.for_user(utilisateur)
    return Response({
        "access_token": str(token.access_token),
        "token_type": "bearer",
        "role": utilisateur.role,
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def mon_profil(request):
    return Response(UtilisateurSerializer(request.user).data)


# =========================================================
# Disponibilités du médecin — EF-11
# =========================================================

@api_view(["POST", "GET"])
@permission_classes([role_requis(Utilisateur.Role.MEDECIN)])
def mes_disponibilites(request):
    if request.method == "GET":
        dispos = DisponibiliteMedecin.objects.filter(medecin_id=request.user.id)
        return Response([
            {
                "id": d.id, "jour_semaine": d.jour_semaine,
                "heure_debut": d.heure_debut.strftime("%H:%M"),
                "heure_fin": d.heure_fin.strftime("%H:%M"),
                "duree_creneau_minutes": d.duree_creneau_minutes,
            }
            for d in dispos
        ])

    # POST — déclarer une nouvelle plage de disponibilité
    jour_semaine = int(request.data.get("jour_semaine"))
    duree = int(request.data.get("duree_creneau_minutes", 30))
    try:
        heure_debut = datetime.strptime(request.data.get("heure_debut"), "%H:%M").time()
        heure_fin = datetime.strptime(request.data.get("heure_fin"), "%H:%M").time()
    except (ValueError, TypeError):
        raise ValidationError({"detail": "heure_debut/heure_fin doivent être au format HH:MM"})

    if not (0 <= jour_semaine <= 6):
        raise ValidationError({"detail": "jour_semaine doit être compris entre 0 (lundi) et 6 (dimanche)"})

    dispo = DisponibiliteMedecin.objects.create(
        medecin_id=request.user.id, jour_semaine=jour_semaine,
        heure_debut=heure_debut, heure_fin=heure_fin, duree_creneau_minutes=duree,
    )
    return Response({"id": dispo.id, "message": "Disponibilité enregistrée"}, status=201)


# =========================================================
# Référentiel des médicaments — nécessaire pour le formulaire de prescription
# =========================================================

@api_view(["GET"])
@permission_classes([role_requis(Utilisateur.Role.MEDECIN, Utilisateur.Role.ADMINISTRATEUR)])
def lister_medicaments(request):
    return Response([{"id": m.id, "nom": m.nom} for m in Medicament.objects.all().order_by("nom")])


# =========================================================
# Annuaire des médecins
# =========================================================

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def lister_medecins(request):
    medecins = Medecin.objects.select_related("utilisateur").all()
    return Response([
        {
            "id": m.utilisateur_id,
            "nom": m.utilisateur.nom,
            "prenom": m.utilisateur.prenom,
            "specialite": m.specialite,
        }
        for m in medecins
    ])


# =========================================================
# Disponibilités — EF-03 : Consulter les disponibilités
# =========================================================

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def disponibilites_medecin(request, medecin_id):
    if not Medecin.objects.filter(utilisateur_id=medecin_id).exists():
        raise NotFound("Médecin introuvable")

    jour_str = request.query_params.get("jour")
    if not jour_str:
        raise ValidationError({"detail": "Le paramètre 'jour' (YYYY-MM-DD) est requis"})
    jour = datetime.strptime(jour_str, "%Y-%m-%d").date()

    creneaux = services.calculer_creneaux_libres(medecin_id, jour)
    return Response([{"date_heure": c.isoformat()} for c in creneaux])


# =========================================================
# Rendez-vous — EF-04 : Demander un RDV / EF-05 : Valider un RDV
# =========================================================

@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def rendez_vous_collection(request):
    if request.method == "POST":
        # Réservé au patient — la vérification de rôle est faite ici plutôt que dans le
        # décorateur de permission, car GET et POST ont des règles d'accès différentes.
        if request.user.role != Utilisateur.Role.PATIENT:
            raise PermissionDenied("Seul un patient peut demander un rendez-vous.")

        serializer = DemandeRDVSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        donnees = serializer.validated_data
        rdv = services.creer_demande_rdv(
            patient_id=request.user.id,
            medecin_id=donnees["medecin_id"],
            date_heure=donnees["date_heure"],
            motif=donnees.get("motif"),
        )
        return Response(RendezVousSerializer(rdv).data, status=201)

    # GET — RBAC : un patient ne voit que ses propres RDV ; un médecin voit les siens ;
    # la réceptionniste et l'administrateur voient tous les RDV (vue transverse).
    requete = RendezVous.objects.all()
    if request.user.role == Utilisateur.Role.PATIENT:
        requete = requete.filter(patient_id=request.user.id)
    elif request.user.role == Utilisateur.Role.MEDECIN:
        requete = requete.filter(medecin_id=request.user.id)

    statut = request.query_params.get("statut")
    if statut:
        requete = requete.filter(statut=statut)

    return Response(RendezVousSerializer(requete.order_by("date_heure"), many=True).data)


@api_view(["PATCH"])
@permission_classes([role_requis(
    Utilisateur.Role.MEDECIN, Utilisateur.Role.RECEPTIONNISTE, Utilisateur.Role.ADMINISTRATEUR
)])
def changer_statut_rendez_vous(request, rdv_id):
    """
    Validation/annulation réservée au médecin, à la réceptionniste et à l'administrateur (RBAC).
    L'administrateur peut en plus réaffecter le RDV à un autre médecin (champ optionnel
    'nouveau_medecin_id'), utile en cas d'absence imprévue d'un praticien.
    """
    try:
        rdv = RendezVous.objects.get(id=rdv_id)
    except RendezVous.DoesNotExist:
        raise NotFound("Rendez-vous introuvable")

    nouveau_medecin_id = request.data.get("nouveau_medecin_id")
    if nouveau_medecin_id is not None:
        if request.user.role != Utilisateur.Role.ADMINISTRATEUR:
            raise PermissionDenied("Seul un administrateur peut réaffecter un rendez-vous.")
        if not Medecin.objects.filter(utilisateur_id=nouveau_medecin_id).exists():
            raise NotFound("Médecin de réaffectation introuvable")
        rdv.medecin_id = nouveau_medecin_id
        rdv.save(update_fields=["medecin_id"])

    nouveau_statut = request.data.get("statut")
    if nouveau_statut:
        rdv = services.changer_statut_rdv(rdv, nouveau_statut)
    return Response(RendezVousSerializer(rdv).data)


# =========================================================
# Consultations & Prescriptions — EF-07 / EF-08
# =========================================================

@api_view(["POST"])
@permission_classes([role_requis(Utilisateur.Role.MEDECIN)])
def enregistrer_consultation(request, rdv_id):
    try:
        rdv = RendezVous.objects.get(id=rdv_id, medecin_id=request.user.id)
    except RendezVous.DoesNotExist:
        raise NotFound("Rendez-vous introuvable")

    compte_rendu = request.data.get("compte_rendu", "")
    with transaction.atomic():
        consultation = Consultation.objects.create(rendez_vous=rdv, compte_rendu=compte_rendu)
        rdv.statut = RendezVous.Statut.TERMINE
        rdv.save(update_fields=["statut"])

    return Response({"id": consultation.id, "message": "Consultation enregistrée"}, status=201)


@api_view(["POST"])
@permission_classes([role_requis(Utilisateur.Role.MEDECIN)])
def rediger_prescription(request):
    serializer = PrescriptionInSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    donnees = serializer.validated_data

    try:
        consultation = Consultation.objects.get(id=donnees["consultation_id"])
    except Consultation.DoesNotExist:
        raise NotFound("Consultation introuvable")

    with transaction.atomic():
        prescription = Prescription.objects.create(consultation=consultation)
        for ligne in donnees["lignes"]:
            LignePrescription.objects.create(
                prescription=prescription,
                medicament_id=ligne["medicament_id"],
                posologie=ligne["posologie"],
                duree_traitement=ligne.get("duree_traitement"),
            )

    return Response(PrescriptionOutSerializer(prescription).data, status=201)


@api_view(["GET"])
@permission_classes([role_requis(Utilisateur.Role.PATIENT)])
def mes_prescriptions(request):
    """EF-09 : le patient consulte/télécharge l'historique de ses prescriptions."""
    prescriptions = Prescription.objects.filter(
        consultation__rendez_vous__patient_id=request.user.id
    ).distinct()
    return Response(PrescriptionOutSerializer(prescriptions, many=True).data)
