"""
Logique métier (couche service) : calcul des créneaux disponibles,
transitions d'état du RendezVous — équivalent Django du crud.py de la version FastAPI.
"""
from datetime import datetime, timedelta

from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError, APIException

from .models import DisponibiliteMedecin, RendezVous


class CreneauIndisponible(APIException):
    status_code = 409
    default_detail = "Ce créneau vient d'être réservé par un autre patient. Merci d'en choisir un autre."
    default_code = "creneau_indisponible"


def calculer_creneaux_libres(medecin_id, jour):
    """
    Calcule les créneaux libres d'un médecin pour une journée donnée :
    (créneaux définis par ses disponibilités récurrentes) MOINS (créneaux déjà pris
    par un RDV actif, c'est-à-dire ni ANNULE).
    """
    jour_semaine = jour.weekday()  # 0 = lundi

    disponibilites = DisponibiliteMedecin.objects.filter(medecin_id=medecin_id, jour_semaine=jour_semaine)
    if not disponibilites.exists():
        return []

    debut_jour = datetime.combine(jour, datetime.min.time())
    fin_jour = datetime.combine(jour, datetime.max.time())

    rdv_existants = RendezVous.objects.filter(
        medecin_id=medecin_id,
        date_heure__gte=debut_jour,
        date_heure__lte=fin_jour,
    ).exclude(statut=RendezVous.Statut.ANNULE)
    heures_prises = {rdv.date_heure.replace(tzinfo=None) for rdv in rdv_existants}

    maintenant = timezone.now().replace(tzinfo=None)
    creneaux_libres = []
    for dispo in disponibilites:
        curseur = datetime.combine(jour, dispo.heure_debut)
        fin = datetime.combine(jour, dispo.heure_fin)
        pas = timedelta(minutes=dispo.duree_creneau_minutes)
        while curseur + pas <= fin:
            if curseur not in heures_prises and curseur > maintenant:
                creneaux_libres.append(curseur)
            curseur += pas

    return sorted(creneaux_libres)


def creer_demande_rdv(patient_id, medecin_id, date_heure, motif=None):
    """
    Crée une demande de RDV (statut EN_ATTENTE).
    S'appuie sur la contrainte UNIQUE(medecin, date_heure) en base pour garantir
    l'absence de double réservation, même en cas de requêtes concurrentes.
    """
    try:
        with transaction.atomic():
            rdv = RendezVous.objects.create(
                patient_id=patient_id,
                medecin_id=medecin_id,
                date_heure=date_heure,
                motif=motif,
                statut=RendezVous.Statut.EN_ATTENTE,
            )
        return rdv
    except IntegrityError:
        raise CreneauIndisponible()


# Table des transitions autorisées — traduction directe du diagramme d'état-transition (§3.4)
TRANSITIONS_AUTORISEES = {
    RendezVous.Statut.EN_ATTENTE: {RendezVous.Statut.CONFIRME, RendezVous.Statut.ANNULE},
    RendezVous.Statut.CONFIRME: {RendezVous.Statut.ANNULE, RendezVous.Statut.EN_COURS},
    RendezVous.Statut.EN_COURS: {RendezVous.Statut.TERMINE},
    RendezVous.Statut.ANNULE: set(),
    RendezVous.Statut.TERMINE: set(),
}


def changer_statut_rdv(rdv, nouveau_statut):
    """Applique une transition d'état en respectant strictement le diagramme d'état-transition."""
    if nouveau_statut not in TRANSITIONS_AUTORISEES[rdv.statut]:
        raise ValidationError(
            {"detail": f"Transition invalide : {rdv.statut} -> {nouveau_statut}"}
        )
    rdv.statut = nouveau_statut
    rdv.save(update_fields=["statut"])
    return rdv
