"""Papéis e permissões do sistema MGT (RC26).

Papéis (UserProfile.role):
  - admin: acesso total, aprova usuários na tela Equipe.
  - comercial: opera o funil; pode exportar/importar e rodar o Diário.
  - tecnico: opera projetos/tarefas/RAT; sem excluir/exportar/importar.

Superusuário conta sempre como admin. Ações protegidas:
  - excluir registros: admin
  - exportar/importar: admin + comercial
  - Diário Oficial (execução automática): admin + comercial
  - tela Equipe: admin
"""

from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


def user_role(user):
    """Papel efetivo do usuário ('admin', 'comercial' ou 'tecnico')."""
    if not getattr(user, "is_authenticated", False):
        return ""
    if user.is_superuser:
        return "admin"
    profile = getattr(user, "profile", None)
    return profile.role if profile else "tecnico"


def role_required(*roles):
    """Exige login e um dos papéis informados (403 caso contrário)."""
    def decorator(view):
        @wraps(view)
        @login_required
        def wrapper(request, *args, **kwargs):
            if user_role(request.user) not in roles:
                raise PermissionDenied
            return view(request, *args, **kwargs)
        return wrapper
    return decorator


def role_context(request):
    """Context processor: expõe `user_role` em todos os templates."""
    return {"user_role": user_role(request.user)}
