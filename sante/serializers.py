from rest_framework import serializers
from .models import (
    Utilisateur, Patient, Medecin, DisponibiliteMedecin,
    RendezVous, Consultation, Prescription, LignePrescription, Medicament,
)


class UtilisateurSerializer(serializers.ModelSerializer):
    class Meta:
        model = Utilisateur
        fields = ["id", "email", "nom", "prenom", "role"]


class InscriptionPatientSerializer(serializers.Serializer):
    email = serializers.EmailField()
    mot_de_passe = serializers.CharField(min_length=6, write_only=True)
    nom = serializers.CharField(max_length=100)
    prenom = serializers.CharField(max_length=100)
    telephone = serializers.CharField(max_length=30, required=False, allow_blank=True)
    date_naissance = serializers.DateField(required=False, allow_null=True)
    adresse = serializers.CharField(max_length=255, required=False, allow_blank=True)


class DisponibiliteMedecinSerializer(serializers.ModelSerializer):
    class Meta:
        model = DisponibiliteMedecin
        fields = ["id", "jour_semaine", "heure_debut", "heure_fin", "duree_creneau_minutes"]


class RendezVousSerializer(serializers.ModelSerializer):
    # patient_id et medecin_id sont générés automatiquement par Django pour les ForeignKey
    class Meta:
        model = RendezVous
        fields = ["id", "patient_id", "medecin_id", "date_heure", "statut", "motif"]


class DemandeRDVSerializer(serializers.Serializer):
    medecin_id = serializers.IntegerField()
    date_heure = serializers.DateTimeField()
    motif = serializers.CharField(required=False, allow_blank=True)


class LignePrescriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = LignePrescription
        fields = ["medicament_id", "posologie", "duree_traitement"]


class PrescriptionInSerializer(serializers.Serializer):
    consultation_id = serializers.IntegerField()
    lignes = LignePrescriptionSerializer(many=True)


class PrescriptionOutSerializer(serializers.ModelSerializer):
    lignes = LignePrescriptionSerializer(many=True, read_only=True)

    class Meta:
        model = Prescription
        fields = ["id", "date_prescription", "lignes"]
