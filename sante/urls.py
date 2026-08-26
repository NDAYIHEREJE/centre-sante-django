from django.urls import path
from . import views
from . import admin_api

urlpatterns = [
    path("", views.accueil),  # sert le frontend (index.html) à la racine du site

    path("auth/inscription-patient", views.inscription_patient),
    path("auth/connexion", views.connexion),
    path("auth/moi", views.mon_profil),

    path("medecins", views.lister_medecins),
    path("medicaments", views.lister_medicaments),
    path("medecins/moi/disponibilites", views.mes_disponibilites),
    path("medecins/<int:medecin_id>/disponibilites", views.disponibilites_medecin),

    path("rendezvous", views.rendez_vous_collection),  # GET (liste, filtrable ?statut=) et POST (demande)
    path("rendezvous/<int:rdv_id>", views.changer_statut_rendez_vous),

    path("consultations/<int:rdv_id>", views.enregistrer_consultation),
    path("prescriptions", views.rediger_prescription),
    path("patients/moi/prescriptions", views.mes_prescriptions),

    # ---------- Espace Administrateur ----------
    # Préfixe "gestion-admin/" (et non "admin/") : Django réserve déjà "admin/" en entier
    # pour son propre panneau d'administration (voir centre_sante/urls.py). Utiliser "admin/"
    # ici ferait passer ces routes DANS l'admin Django, qui ne les connaît pas — d'où l'erreur
    # "Unexpected token '<'" côté frontend (page d'erreur HTML de Django reçue au lieu de JSON).
    path("gestion-admin/utilisateurs", admin_api.utilisateurs_collection),
    path("gestion-admin/utilisateurs/<int:utilisateur_id>", admin_api.utilisateur_detail),
    path("gestion-admin/utilisateurs/<int:utilisateur_id>/mot-de-passe", admin_api.reinitialiser_mot_de_passe),
    path("gestion-admin/tableau-de-bord", admin_api.tableau_de_bord),
    path("gestion-admin/patients", admin_api.rechercher_patients),
    path("gestion-admin/patients/<int:patient_id>/dossier", admin_api.dossier_patient),
    path("gestion-admin/medicaments", admin_api.creer_medicament),
    path("gestion-admin/medicaments/<int:medicament_id>", admin_api.supprimer_medicament),
]
