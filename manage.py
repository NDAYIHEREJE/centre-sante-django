#!/usr/bin/env python
"""Utilitaire en ligne de commande de Django (manage.py migrate / runserver / seed / ...)."""
import os
import sys


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "centre_sante.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Impossible d'importer Django. Avez-vous activé votre environnement "
            "conda et exécuté 'pip install -r requirements.txt' ?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
