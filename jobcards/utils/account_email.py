# jobcards/utils/account_email.py
from typing import Iterable, Tuple, List, Dict
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from ..email_providers import send_via_graph

def send_profile_change_password_email(user):
    """
    Envia e-mail de troca de senha para 1 usuário.
    Mantido igual ao seu, apenas retornando bool.
    """
    ctx = {
        "user": user,
        "base_url": getattr(settings, "BASE_URL", ""),
        "login_hint": getattr(settings, "TASKFY_LOGIN_HINT", ""),
    }
    html = render_to_string("mail/change_password.html", ctx)
    text = strip_tags(html)

    ok, msg = send_via_graph(
        subject="TASKFY — Password Reset",
        text_body=text,
        html_body=html,
        to_list=[user.email],      # <- individual
        bcc_list=[],
        cc_list=[],
        reply_to=None,
        sender=getattr(settings, "EMAIL_SENDER", None),
        attachments=None,
        save_to_sent=True,
    )
    if not ok and settings.DEBUG:
        # deixe levantar para ver a causa em dev
        raise RuntimeError(msg)
    return ok

def send_profile_change_password_email_bulk(users: Iterable) -> Tuple[int, List[Dict]]:
    """
    Itera sobre os usuários selecionados no Admin e dispara 1 e-mail por usuário.
    Retorna (qtd_enviados, lista_de_erros).
    """
    enviados = 0
    erros: List[Dict] = []
    for u in users:
        if not getattr(u, "email", None):
            erros.append({"username": getattr(u, "username", str(u)), "email": None, "error": "Usuário sem e-mail"})
            continue
        try:
            ok = send_profile_change_password_email(u)
            if ok:
                enviados += 1
            else:
                erros.append({"username": u.username, "email": u.email, "error": "send_via_graph retornou False"})
        except Exception as e:
            erros.append({"username": getattr(u, "username", str(u)), "email": u.email, "error": str(e)})
    return enviados, erros
