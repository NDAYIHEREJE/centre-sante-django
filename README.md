# Application de gestion d'un centre de santé — Version Django (frontend + backend fusionnés)

## Pourquoi cette version existe

Cette version réimplémente les mêmes fonctionnalités que la version FastAPI livrée précédemment (mêmes routes d'API, même contrat de données), avec **Django + Django REST Framework**, pour utiliser les commandes standards `python manage.py migrate` et `python manage.py runserver`.

**Le frontend et le backend sont désormais fusionnés dans un seul serveur** : `index.html`, `style.css` et `app.js` sont servis directement par Django (via son système de templates/fichiers statiques), à la même adresse que l'API. **Un seul terminal et une seule commande suffisent** — plus besoin du second serveur `python -m http.server 5500`, ni de se soucier du CORS entre deux ports différents.

## Architecture

```
centre_sante_django/
├── manage.py                    point d'entrée des commandes Django
├── centre_sante/                configuration du projet (settings, urls, wsgi)
├── sante/                       application métier
│   ├── models.py                 modèles ORM (= diagramme de classes)
│   ├── serializers.py            validation entrées/sorties (DRF)
│   ├── views.py                  routes de l'API + vue d'accueil (accueil() sert index.html)
│   ├── permissions.py            contrôle d'accès RBAC
│   ├── services.py               logique métier (créneaux, transitions d'état)
│   ├── admin.py                  interface d'administration (/admin)
│   ├── templates/index.html      page du frontend (servie à la racine "/")
│   ├── static/app.js             logique frontend (chemins d'API relatifs)
│   ├── static/style.css          styles du frontend
│   └── management/commands/      commandes personnalisées (seed, gestion_comptes)
└── requirements.txt
```

## 1. Installation

```bash
conda activate centre_sante
cd chemin\vers\centre_sante_django
pip install -r requirements.txt
```

## 2. Créer la base de données (équivalent de `migrate`)

```bash
python manage.py makemigrations sante
python manage.py migrate
```

## 3. Générer les données de démonstration

```bash
python manage.py seed
```

Crée le compte médecin (`medecin@clinique.test` / `motdepasse123`), le compte réceptionniste (`reception@clinique.test` / `motdepasse123`), leurs disponibilités et quelques médicaments.

## 4. (Recommandé) Créer un compte administrateur Django

```bash
python manage.py createsuperuser
```

Donne accès à `http://localhost:8000/admin` pour visualiser/modifier directement les données.

## 5. Lancer le serveur — UN SEUL terminal, UNE SEULE commande

```bash
python manage.py runserver
```

Puis ouvrez simplement :

```
http://localhost:8000
```

➡️ C'est l'écran de connexion de l'application, servi directement par Django. **Plus besoin d'un second terminal ni du port 5500.**

L'API reste accessible aux mêmes adresses qu'avant (`http://localhost:8000/auth/connexion`, `http://localhost:8000/rendezvous`, etc.) — seule la manière de servir le frontend a changé.

L'administration reste sur `http://localhost:8000/admin`.

## 6. Scénario de démonstration

Identique aux versions précédentes, mais tout se passe maintenant sur `localhost:8000` uniquement :
1. Créer un compte patient, se connecter, prendre un RDV avec le Dr Nkurunziza
2. Se connecter en réceptionniste (`reception@clinique.test`), confirmer la demande
3. Vérifier dans `/admin` que le rendez-vous apparaît avec le statut `CONFIRME`
4. Tester la contrainte anti-double-réservation en demandant deux fois le même créneau (le second doit échouer avec une erreur 409)

## Aide-mémoire des commandes

```bash
# Installation (une seule fois)
conda activate centre_sante
pip install -r requirements.txt
python manage.py makemigrations sante
python manage.py migrate
python manage.py seed

# À chaque session de travail — UN SEUL terminal désormais
conda activate centre_sante
cd chemin\vers\centre_sante_django
python manage.py runserver
```

Puis ouvrez `http://localhost:8000` dans le navigateur.

