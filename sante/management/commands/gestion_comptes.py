"""
Commande Django personnalisée pour créer un compte Médecin ou Réceptionniste
supplémentaire (rôles volontairement sans auto-inscription — voir ENF-02).

Exécution :  python manage.py gestion_comptes
"""
from django.core.management.base import BaseCommand
from sante.models import Utilisateur, Medecin


class Command(BaseCommand):
    help = "Crée un compte Médecin ou Réceptionniste supplémentaire, de façon interactive."

    def handle(self, *args, **options):
        self.stdout.write("=== Création d'un compte médecin ou réceptionniste ===\n")

        role_saisi = input("Rôle (1 = Médecin, 2 = Réceptionniste) : ").strip()
        email = input("Email : ").strip()
        mot_de_passe = input("Mot de passe : ").strip()
        nom = input("Nom : ").strip()
        prenom = input("Prénom : ").strip()

        if Utilisateur.objects.filter(email=email).exists():
            self.stdout.write(self.style.ERROR(f"Un compte existe déjà avec l'email {email}."))
            return

        if role_saisi == "1":
            specialite = input("Spécialité (ex. Cardiologie) : ").strip()
            numero_ordre = input("Numéro d'ordre (optionnel, Entrée pour ignorer) : ").strip() or None

            utilisateur = Utilisateur.objects.create_user(
                email=email, password=mot_de_passe, nom=nom, prenom=prenom,
                role=Utilisateur.Role.MEDECIN,
            )
            Medecin.objects.create(utilisateur=utilisateur, specialite=specialite, numero_ordre=numero_ordre)
            self.stdout.write(self.style.SUCCESS(f"\nMédecin créé : {prenom} {nom} ({email})"))
            self.stdout.write("Pensez à déclarer ses disponibilités via POST /medecins/moi/disponibilites.")

        elif role_saisi == "2":
            Utilisateur.objects.create_user(
                email=email, password=mot_de_passe, nom=nom, prenom=prenom,
                role=Utilisateur.Role.RECEPTIONNISTE,
            )
            self.stdout.write(self.style.SUCCESS(f"\nRéceptionniste créé(e) : {prenom} {nom} ({email})"))

        else:
            self.stdout.write(self.style.ERROR("Rôle invalide. Relancez la commande et entrez 1 ou 2."))
