# jobcards/middleware.py
from django.shortcuts import redirect
from django.urls import reverse
from django.db import connection
from django.db.utils import ProgrammingError, OperationalError
from django.apps import apps

class ForcePasswordChangeMiddleware:
    """
    Força troca de senha quando must_change_password=True.
    Resiliente: se a tabela/flag ainda não existir, ignora.
    Faz cache do check da tabela para evitar testar em toda request.
    """
    _checked = False
    _flag_table_ok = False

    def __init__(self, get_response):
        self.get_response = get_response

    @classmethod
    def _ensure_flag_table(cls):
        if cls._checked:
            return
        try:
            # checa se o model está registrado
            apps.get_model("jobcards", "UserSecurityFlag")
            # tenta selecionar 1 linha; se a tabela não existir, explode e caímos no except
            with connection.cursor() as cur:
                cur.execute("SELECT 1 FROM jobcards_usersecurityflag LIMIT 1")
            cls._flag_table_ok = True
        except Exception:
            cls._flag_table_ok = False
        finally:
            cls._checked = True

    def __call__(self, request):
        user = getattr(request, "user", None)
        if not (user and user.is_authenticated):
            return self.get_response(request)

        # garante que só tentaremos ler o flag se a tabela existir
        self._ensure_flag_table()
        if not self._flag_table_ok:
            return self.get_response(request)

        try:
            flag = getattr(user, "securityflag", None)
        except (ProgrammingError, OperationalError):
            # algum problema de migração/consulta: segue o fluxo normal
            return self.get_response(request)

        if flag and getattr(flag, "must_change_password", False):
            allowed = {
                reverse("password_change"),
                reverse("password_change_done"),
                reverse("logout"),
            }
            if request.path not in allowed:
                return redirect("password_change")

        return self.get_response(request)
