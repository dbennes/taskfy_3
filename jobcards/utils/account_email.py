# jobcards/utils/account_email.py
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.urls import reverse
from ..email_providers import send_via_graph

def send_profile_change_password_email(user):
    # Renderiza teus templates (ajuste os nomes/paths se forem outros)
    ctx = {
        "user": user,
        "base_url": getattr(settings, "BASE_URL", ""),
        "login_hint": getattr(settings, "TASKFY_LOGIN_HINT", ""),
    }
    html = render_to_string("mail/change_password.html", ctx)
    text = strip_tags(html)  # texto de fallback

    subject = "Taskfy — acesso/alteração de senha"
    to = [user.email]

    ok, msg = send_via_graph(
        subject=subject,
        text_body=text,
        html_body=html,
        to_list=to,
        bcc_list=[],
        cc_list=[],
        reply_to=None,
        sender=getattr(settings, "EMAIL_SENDER", None),
        attachments=None,  # se precisar, passe lista de tuplas
        save_to_sent=True,
    )
    if not ok and settings.DEBUG:
        raise RuntimeError(msg)
    return ok
