"""
Modèles Django — traduction directe du diagramme de classes UML
(Utilisateur / Patient / Medecin / RendezVous / Consultation / Prescription / Medicament).
"""
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.db import models


class UtilisateurManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("L'email est obligatoire")
        email = self.normalize_email(email)
        utilisateur = self.model(email=email, **extra_fields)
        utilisateur.set_password(password)
        utilisateur.save(using=self._db)
        return utilisateur

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("role", Utilisateur.Role.ADMINISTRATEUR)
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email, password, **extra_fields)


class Utilisateur(AbstractBaseUser, PermissionsMixin):
    class Role(models.TextChoices):
        PATIENT = "PATIENT", "Patient"
        MEDECIN = "MEDECIN", "Médecin"
        RECEPTIONNISTE = "RECEPTIONNISTE", "Réceptionniste"
        ADMINISTRATEUR = "ADMINISTRATEUR", "Administrateur"

    email = models.EmailField(unique=True)
    nom = models.CharField(max_length=100)
    prenom = models.CharField(max_length=100)
    telephone = models.CharField(max_length=30, blank=True, null=True)
    role = models.CharField(max_length=20, choices=Role.choices)
    date_creation = models.DateTimeField(auto_now_add=True)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)  # nécessaire pour l'accès à /admin

    objects = UtilisateurManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["nom", "prenom"]

    def __str__(self):
        return f"{self.prenom} {self.nom} ({self.role})"


class Patient(models.Model):
    utilisateur = models.OneToOneField(Utilisateur, primary_key=True, on_delete=models.CASCADE, related_name="patient")
    date_naissance = models.DateField(blank=True, null=True)
    adresse = models.CharField(max_length=255, blank=True, null=True)
    antecedents = models.TextField(blank=True, null=True)
    allergies = models.TextField(blank=True, null=True)

    def __str__(self):
        return str(self.utilisateur)


class Medecin(models.Model):
    utilisateur = models.OneToOneField(Utilisateur, primary_key=True, on_delete=models.CASCADE, related_name="medecin")
    specialite = models.CharField(max_length=100)
    numero_ordre = models.CharField(max_length=50, unique=True, blank=True, null=True)

    def __str__(self):
        return f"Dr {self.utilisateur.prenom} {self.utilisateur.nom} — {self.specialite}"


class DisponibiliteMedecin(models.Model):
    medecin = models.ForeignKey(Medecin, on_delete=models.CASCADE, related_name="disponibilites")
    jour_semaine = models.SmallIntegerField(help_text="0 = lundi ... 6 = dimanche")
    heure_debut = models.TimeField()
    heure_fin = models.TimeField()
    duree_creneau_minutes = models.SmallIntegerField(default=30)

    def __str__(self):
        return f"{self.medecin} — jour {self.jour_semaine} {self.heure_debut}-{self.heure_fin}"


class RendezVous(models.Model):
    class Statut(models.TextChoices):
        EN_ATTENTE = "EN_ATTENTE", "En attente"
        CONFIRME = "CONFIRME", "Confirmé"
        ANNULE = "ANNULE", "Annulé"
        EN_COURS = "EN_COURS", "En cours"
        TERMINE = "TERMINE", "Terminé"

    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="rendez_vous")
    medecin = models.ForeignKey(Medecin, on_delete=models.CASCADE, related_name="rendez_vous")
    date_heure = models.DateTimeField()
    statut = models.CharField(max_length=20, choices=Statut.choices, default=Statut.EN_ATTENTE)
    motif = models.CharField(max_length=255, blank=True, null=True)
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Traduction directe de la contrainte UNIQUE(medecin_id, date_heure) — ENF-04
        constraints = [
            models.UniqueConstraint(fields=["medecin", "date_heure"], name="uq_medecin_creneau"),
        ]

    def __str__(self):
        return f"RDV #{self.id} — {self.patient} avec {self.medecin} le {self.date_heure} [{self.statut}]"


class Consultation(models.Model):
    rendez_vous = models.OneToOneField(RendezVous, on_delete=models.CASCADE, related_name="consultation")
    date_consultation = models.DateTimeField(auto_now_add=True)
    compte_rendu = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Consultation #{self.id} — {self.rendez_vous}"


class Medicament(models.Model):
    nom = models.CharField(max_length=150)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.nom


class Prescription(models.Model):
    consultation = models.ForeignKey(Consultation, on_delete=models.CASCADE, related_name="prescriptions")
    date_prescription = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Prescription #{self.id} — {self.consultation}"


class LignePrescription(models.Model):
    prescription = models.ForeignKey(Prescription, on_delete=models.CASCADE, related_name="lignes")
    medicament = models.ForeignKey(Medicament, on_delete=models.PROTECT)
    posologie = models.CharField(max_length=255)
    duree_traitement = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"{self.medicament} — {self.posologie}"
