"""
Commande Django personnalisée : peuple la base avec un jeu de données complet et
réaliste — patients, médecins (avec spécialités), réceptionnistes, disponibilités,
et des rendez-vous couvrant les trois statuts clés (en attente, annulé, terminé
avec consultation et prescription), pour disposer immédiatement d'une démonstration
complète sans devoir tout créer manuellement.

Exécution :  python manage.py seed
"""
import unicodedata
from datetime import datetime, time, timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from sante.models import (
    Utilisateur, Patient, Medecin, DisponibiliteMedecin,
    RendezVous, Consultation, Prescription, LignePrescription, Medicament,
)

MOT_DE_PASSE_DEMO = "motdepasse123"


def slug_email(prenom, nom, domaine):
    """Construit un email ASCII propre à partir d'un nom/prénom accentué."""
    texte = f"{prenom}.{nom}".lower().replace(" ", "-")
    texte = unicodedata.normalize("NFKD", texte).encode("ascii", "ignore").decode("ascii")
    return f"{texte}@{domaine}"


def jour_ouvre(offset_jours, heure, minute=0):
    """Renvoie une date/heure garantie tombée un jour ouvré (lundi-vendredi)."""
    jour = timezone.localdate() + timedelta(days=offset_jours)
    pas = 1 if offset_jours >= 0 else -1
    while jour.weekday() >= 5:  # 5 = samedi, 6 = dimanche
        jour += timedelta(days=pas)
    return timezone.make_aware(datetime.combine(jour, time(heure, minute)))


class Command(BaseCommand):
    help = "Peuple la base avec un jeu de données complet (patients, médecins, réceptionnistes, RDV)."

    def handle(self, *args, **options):
        self.creer_medicaments()
        medecins = self.creer_medecins()
        self.creer_receptionnistes()
        patients = self.creer_patients()
        self.creer_rendez_vous(patients, medecins)

        self.stdout.write(self.style.SUCCESS(
            f"\nDonnées de démonstration prêtes — mot de passe commun : {MOT_DE_PASSE_DEMO}\n"
            "Consultez la liste des comptes créés ci-dessus pour les emails exacts."
        ))

    # -----------------------------------------------------------------
    def creer_medicaments(self):
        medicaments = [
            ("Paracétamol 500mg", "Antalgique / antipyrétique"),
            ("Amoxicilline 500mg", "Antibiotique"),
            ("Ibuprofène 400mg", "Anti-inflammatoire"),
            ("Collyre antiseptique", "Usage ophtalmologique"),
            ("Vitamine D", "Complément"),
            ("Anxiolytique léger", "Usage psychologique, sur prescription"),
            ("Fluoride dentaire", "Usage dentaire préventif"),
        ]
        for nom, description in medicaments:
            Medicament.objects.get_or_create(nom=nom, defaults={"description": description})
        self.stdout.write(self.style.SUCCESS(f"{len(medicaments)} médicaments prêts."))

    # -----------------------------------------------------------------
    def creer_medecins(self):
        donnees = [
            ("Désiré", "NDAYUBAHA", "Ophtalmologue"),
            ("Isaac", "ITANGAKUBUNTU", "Gynécologue"),
            ("Athanase", "NIYUBAHWE", "Pédiatre"),
            ("Janvier", "NDAYISABA", "Psychologue"),
            ("Don Dane", "IRAKIZA UWASE", "Dentiste"),
            ("Raissa Ange", "Bénit", "Neurologue"),
            ("Ferdinand", "MINANI", "Généraliste"),
        ]
        medecins = {}
        for prenom, nom, specialite in donnees:
            email = slug_email(prenom, nom, "medecin.centre-sante.bi")
            utilisateur, cree = Utilisateur.objects.get_or_create(
                email=email,
                defaults=dict(nom=nom, prenom=prenom, role=Utilisateur.Role.MEDECIN),
            )
            if cree:
                utilisateur.set_password(MOT_DE_PASSE_DEMO)
                utilisateur.save(update_fields=["password"])
                Medecin.objects.create(utilisateur=utilisateur, specialite=specialite)
                for jour in range(0, 5):  # lundi à vendredi
                    for heure_debut, heure_fin in [(8, 12), (14, 16)]:
                        DisponibiliteMedecin.objects.create(
                            medecin_id=utilisateur.id, jour_semaine=jour,
                            heure_debut=time(heure_debut, 0), heure_fin=time(heure_fin, 0),
                            duree_creneau_minutes=30,
                        )
                self.stdout.write(self.style.SUCCESS(f"Médecin créé : {email} — Dr {prenom} {nom} ({specialite})"))
            else:
                self.stdout.write(f"Médecin déjà existant : {email}")
            medecins[f"{prenom} {nom}"] = Medecin.objects.get(utilisateur__email=email)
        return medecins

    # -----------------------------------------------------------------
    def creer_receptionnistes(self):
        donnees = [
            ("Didas", "NDUWAMUNGU"),
            ("Patrice", "NDUWUMUKAMA"),
            ("Vianney", "NDUWIMANA"),
        ]
        for prenom, nom in donnees:
            email = slug_email(prenom, nom, "reception.centre-sante.bi")
            utilisateur, cree = Utilisateur.objects.get_or_create(
                email=email,
                defaults=dict(nom=nom, prenom=prenom, role=Utilisateur.Role.RECEPTIONNISTE),
            )
            if cree:
                utilisateur.set_password(MOT_DE_PASSE_DEMO)
                utilisateur.save(update_fields=["password"])
                self.stdout.write(self.style.SUCCESS(f"Réceptionniste créé(e) : {email} — {prenom} {nom}"))
            else:
                self.stdout.write(f"Réceptionniste déjà existant(e) : {email}")

    # -----------------------------------------------------------------
    def creer_patients(self):
        donnees = [
            ("Ornella", "KANKINDI"),
            ("Fabrice", "NDAYISHIMEZE"),
            ("Evodie", "NZIMA"),
            ("Divin", "NIYERA"),
            ("Pacifique", "NIYOKWIZERA"),
            ("Levis", "TUYISAVYE"),
            ("Aime Saisel", "NDUWAYO"),
            ("Grace", "NIYONGABO"),
            ("Emmanuel", "BARANDEREKA"),
            ("Clémence", "NDAYIZEYE"),
        ]
        patients = {}
        for prenom, nom in donnees:
            email = slug_email(prenom, nom, "patient.centre-sante.bi")
            utilisateur, cree = Utilisateur.objects.get_or_create(
                email=email,
                defaults=dict(nom=nom, prenom=prenom, role=Utilisateur.Role.PATIENT),
            )
            if cree:
                utilisateur.set_password(MOT_DE_PASSE_DEMO)
                utilisateur.save(update_fields=["password"])
                Patient.objects.create(utilisateur=utilisateur)
                self.stdout.write(self.style.SUCCESS(f"Patient créé : {email} — {prenom} {nom}"))
            else:
                self.stdout.write(f"Patient déjà existant : {email}")
            patients[f"{prenom} {nom}"] = Patient.objects.get(utilisateur__email=email)
        return patients

    # -----------------------------------------------------------------
    def creer_rendez_vous(self, patients, medecins):
        """
        Crée un jeu de rendez-vous couvrant les trois statuts demandés :
        EN_ATTENTE, ANNULE, TERMINE (avec Consultation + Prescription),
        plus quelques CONFIRME pour compléter la démonstration.
        """
        if RendezVous.objects.exists():
            self.stdout.write("Des rendez-vous existent déjà — aucun nouveau rendez-vous créé (évite les doublons).")
            return

        # (patient, médecin, offset_jours, heure, statut, motif, avec_prescription)
        plan = [
            ("Ornella KANKINDI", "Isaac ITANGAKUBUNTU", -10, 9, "TERMINE", "Consultation de suivi", True),
            ("Ornella KANKINDI", "Ferdinand MINANI", 3, 10, "ANNULE", "Contrôle général", False),

            ("Fabrice NDAYISHIMEZE", "Désiré NDAYUBAHA", 5, 9, "CONFIRME", "Douleurs oculaires", False),
            ("Fabrice NDAYISHIMEZE", "Don Dane IRAKIZA UWASE", 2, 14, "EN_ATTENTE", "Douleur dentaire", False),

            ("Evodie NZIMA", "Janvier NDAYISABA", 1, 15, "EN_ATTENTE", "Suivi psychologique", False),

            ("Divin NIYERA", "Don Dane IRAKIZA UWASE", -6, 8, "TERMINE", "Détartrage", False),
            ("Divin NIYERA", "Désiré NDAYUBAHA", 7, 9, "CONFIRME", "Contrôle de la vue", False),

            ("Pacifique NIYOKWIZERA", "Ferdinand MINANI", -3, 10, "ANNULE", "Fièvre persistante", False),

            ("Levis TUYISAVYE", "Raissa Ange Bénit", 4, 14, "EN_ATTENTE", "Migraines fréquentes", False),

            ("Aime Saisel NDUWAYO", "Athanase NIYUBAHWE", -8, 9, "TERMINE", "Consultation pédiatrique", True),

            # --- Enregistrements supplémentaires (dont plusieurs "aujourd'hui" pour peupler le tableau de bord) ---
            ("Grace NIYONGABO", "Isaac ITANGAKUBUNTU", 0, 10, "EN_ATTENTE", "Consultation gynécologique", False),
            ("Grace NIYONGABO", "Ferdinand MINANI", -12, 11, "TERMINE", "Bilan de santé général", True),

            ("Emmanuel BARANDEREKA", "Raissa Ange Bénit", 0, 15, "CONFIRME", "Suivi migraines", False),
            ("Emmanuel BARANDEREKA", "Athanase NIYUBAHWE", -4, 10, "ANNULE", "Consultation pédiatrique", False),

            ("Clémence NDAYIZEYE", "Don Dane IRAKIZA UWASE", 9, 9, "EN_ATTENTE", "Contrôle dentaire", False),
            ("Clémence NDAYIZEYE", "Désiré NDAYUBAHA", -14, 10, "TERMINE", "Suivi ophtalmologique", True),

            ("Fabrice NDAYISHIMEZE", "Ferdinand MINANI", 0, 9, "TERMINE", "Contrôle de routine", False),
        ]

        prescriptions_medicaments = {
            "Ornella KANKINDI": [("Collyre antiseptique", "1 goutte matin et soir, 5 jours", "5 jours")],
            "Aime Saisel NDUWAYO": [
                ("Paracétamol 500mg", "Selon poids, si fièvre", "3 jours"),
                ("Vitamine D", "1 dose hebdomadaire", "4 semaines"),
            ],
            "Grace NIYONGABO": [("Ibuprofène 400mg", "1 comprimé si douleur, max 3/jour", "5 jours")],
            "Clémence NDAYIZEYE": [("Collyre antiseptique", "2 gouttes matin et soir, 7 jours", "7 jours")],
        }

        compteur = {"TERMINE": 0, "ANNULE": 0, "EN_ATTENTE": 0, "CONFIRME": 0}

        for nom_patient, nom_medecin, offset, heure, statut, motif, _avec_presc in plan:
            patient = patients[nom_patient]
            medecin = medecins[nom_medecin]
            date_heure = jour_ouvre(offset, heure)

            rdv = RendezVous.objects.create(
                patient=patient, medecin=medecin, date_heure=date_heure,
                statut=statut, motif=motif,
            )
            compteur[statut] += 1

            if statut == "TERMINE":
                consultation = Consultation.objects.create(
                    rendez_vous=rdv,
                    compte_rendu=f"Consultation réalisée — motif initial : {motif}. Aucune complication notée.",
                )
                lignes = prescriptions_medicaments.get(nom_patient)
                if lignes:
                    prescription = Prescription.objects.create(consultation=consultation)
                    for nom_med, posologie, duree in lignes:
                        LignePrescription.objects.create(
                            prescription=prescription,
                            medicament=Medicament.objects.get(nom=nom_med),
                            posologie=posologie, duree_traitement=duree,
                        )

        self.stdout.write(self.style.SUCCESS(
            f"Rendez-vous créés : {compteur['EN_ATTENTE']} en attente, {compteur['CONFIRME']} confirmés, "
            f"{compteur['ANNULE']} annulés, {compteur['TERMINE']} terminés (avec consultation, "
            f"dont {sum(1 for p in prescriptions_medicaments)} avec prescription)."
        ))
