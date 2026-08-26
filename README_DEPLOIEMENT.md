# Guide de déploiement — Render (cloud gratuit)

Ce guide vous donne un **lien public accessible en ligne**, avec une architecture qui respecte fidèlement le diagramme de déploiement du dossier (§3.6) :

| Élément du diagramme (§3.6) | Équivalent chez Render |
|---|---|
| Serveur Web (reverse proxy + fichiers statiques) | Géré automatiquement par Render (HTTPS, load balancer) + Whitenoise pour les fichiers statiques |
| Serveur applicatif (Gunicorn + Django) | Le "Web Service" Render, qui exécute exactement `gunicorn centre_sante.wsgi:application` |
| Serveur de base de données (PostgreSQL) | Une base "PostgreSQL" Render, **physiquement séparée** du serveur applicatif — comme documenté dans votre justification ENF-01 |

Trois serveurs distincts, comme sur le diagramme — sauf que c'est Render qui les héberge, plutôt que vous.

---

## Étape 0 — Créer un dépôt GitHub (obligatoire pour Render)

Render déploie à partir d'un dépôt Git. Si vous n'en avez pas encore :

1. Créez un compte sur [github.com](https://github.com) si nécessaire.
2. Créez un nouveau dépôt (ex. `centre-sante-django`), vide, sans README.
3. Sur votre machine, dans le dossier du projet :
   ```
   cd "D:\MASTER 1\GENIE LOGICIEL EXAMEN\centre_sante_django"
   git init
   git add .
   git commit -m "Version initiale du projet"
   git branch -M main
   git remote add origin https://github.com/VOTRE-NOM/centre-sante-django.git
   git push -u origin main
   ```

> Si `git` n'est pas installé : téléchargez-le depuis [git-scm.com](https://git-scm.com/download/win), installation par défaut, puis relancez Anaconda Prompt.

**Important** : ajoutez un fichier `.gitignore` pour ne pas publier votre base locale ni vos fichiers temporaires (fourni ci-dessous, à placer à la racine du projet).

---

## Étape 1 — Créer un compte Render

Allez sur [render.com](https://render.com), créez un compte gratuit (possibilité de se connecter directement avec GitHub, ce qui simplifie la suite).

---

## Étape 2 — Déploiement automatique via `render.yaml` (le plus simple)

Le fichier `render.yaml` fourni décrit toute l'architecture (service web + base de données) en une seule fois.

1. Sur le tableau de bord Render, cliquez **"New +"** → **"Blueprint"**.
2. Reliez votre dépôt GitHub (`centre-sante-django`).
3. Render détecte automatiquement `render.yaml` et propose de créer :
   - un **Web Service** (votre application Django)
   - une **base PostgreSQL** (`centre-sante-db`)
4. Cliquez **"Apply"**. Render construit et déploie automatiquement (comptez 3 à 5 minutes pour la première fois).

## Étape 2 bis — Si vous préférez le faire manuellement (sans `render.yaml`)

1. **New +** → **PostgreSQL** → nommez-la `centre-sante-db`, plan gratuit → **Create Database**.
2. **New +** → **Web Service** → reliez votre dépôt GitHub.
3. Renseignez :
   - **Build Command** : `pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate`
   - **Start Command** : `gunicorn centre_sante.wsgi:application`
4. Dans l'onglet **Environment**, ajoutez ces variables :
   | Clé | Valeur |
   |---|---|
   | `DJANGO_DEBUG` | `False` |
   | `DJANGO_SECRET_KEY` | (cliquez "Generate" pour une valeur aléatoire) |
   | `DJANGO_ALLOWED_HOSTS` | `.onrender.com` |
   | `DATABASE_URL` | copiez la "Internal Connection String" depuis la page de votre base `centre-sante-db` |
5. **Create Web Service**.

---

## Étape 3 — Créer les données de démonstration en production

Une fois le déploiement terminé (statut "Live"), ouvrez l'onglet **Shell** de votre Web Service sur Render (accessible directement depuis le tableau de bord, pas besoin de terminal local) :

```
python manage.py seed
python manage.py createsuperuser
```

---

## Étape 4 — Accéder à votre application en ligne

Render vous donne une adresse du type :
```
https://centre-sante-django.onrender.com
```

C'est votre application complète, accessible depuis n'importe quel navigateur, n'importe où — à montrer directement à l'oral.

`/admin` reste accessible à `https://centre-sante-django.onrender.com/admin`.

---

## Limites du plan gratuit Render (à connaître avant la soutenance)

- Le service **s'endort après 15 minutes d'inactivité** et met ~30-50 secondes à se "réveiller" au premier accès suivant. **Ouvrez le lien 2-3 minutes avant votre passage** pour qu'il soit déjà réveillé.
- La base de données gratuite est automatiquement supprimée après 90 jours d'inactivité — largement suffisant pour une soutenance, mais à garder en tête si vous comptez la garder en ligne plus longtemps.
- 750h/mois gratuites, largement suffisant pour un usage de démonstration.

---

## Mettre à jour l'application après un changement de code

À chaque fois que vous modifiez le projet localement :
```
git add .
git commit -m "Description du changement"
git push
```
Render redéploie automatiquement à chaque `push` sur la branche `main`.
