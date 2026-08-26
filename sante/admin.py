"""
Enregistrement des modèles dans l'admin Django.
Avantage majeur par rapport à la version FastAPI : /admin fournit une interface
de visualisation et d'édition des données prête à l'emploi, sans code supplémentaire —
utile pour inspecter rapidement la base pendant le développement ou la soutenance.
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import (
    Utilisateur, Patient, Medecin, DisponibiliteMedecin,
    RendezVous, Consultation, Prescription, LignePrescription, Medicament,
)


@admin.register(Utilisateur)
class UtilisateurAdmin(UserAdmin):
    model = Utilisateur
    list_display = ("email", "nom", "prenom", "role", "is_active", "date_creation")
    list_filter = ("role", "is_active")
    ordering = ("email",)
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Informations personnelles", {"fields": ("nom", "prenom", "telephone", "role")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser")}),
    )
    add_fieldsets = (
        (None, {"classes": ("wide",), "fields": ("email", "nom", "prenom", "role", "password1", "password2")}),
    )
    search_fields = ("email", "nom", "prenom")


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ("utilisateur", "date_naissance")


@admin.register(Medecin)
class MedecinAdmin(admin.ModelAdmin):
    list_display = ("utilisateur", "specialite", "numero_ordre")


@admin.register(DisponibiliteMedecin)
class DisponibiliteMedecinAdmin(admin.ModelAdmin):
    list_display = ("medecin", "jour_semaine", "heure_debut", "heure_fin", "duree_creneau_minutes")


@admin.register(RendezVous)
class RendezVousAdmin(admin.ModelAdmin):
    list_display = ("id", "patient", "medecin", "date_heure", "statut")
    list_filter = ("statut",)


@admin.register(Consultation)
class ConsultationAdmin(admin.ModelAdmin):
    list_display = ("id", "rendez_vous", "date_consultation")


@admin.register(Medicament)
class MedicamentAdmin(admin.ModelAdmin):
    list_display = ("id", "nom")


@admin.register(Prescription)
class PrescriptionAdmin(admin.ModelAdmin):
    list_display = ("id", "consultation", "date_prescription")


@admin.register(LignePrescription)
class LignePrescriptionAdmin(admin.ModelAdmin):
    list_display = ("id", "prescription", "medicament", "posologie")
