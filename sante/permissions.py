"""
Contrôle d'accès RBAC (ENF-02) — équivalent Django du role_requis() de la version FastAPI.
"""
from rest_framework.permissions import BasePermission


def role_requis(*roles_autorises):
    """Fabrique une classe de permission DRF qui n'autorise que les rôles donnés."""

    class RoleRequis(BasePermission):
        message = "Accès refusé : rôle insuffisant pour cette action."

        def has_permission(self, request, view):
            utilisateur = request.user
            return bool(
                utilisateur
                and utilisateur.is_authenticated
                and utilisateur.role in roles_autorises
            )

    return RoleRequis
