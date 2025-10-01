# jobcards/utils/account_email.py
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

def _abs_profile_change_url() -> str:
    """
    Monta a URL absoluta do seu Profile com o sinalizador para abrir o modal.
    Ex.: http://SEU-HOST:8080/account/profile/?open=change-password
    """
    base = (getattr(settings, "BASE_URL", "") or "").rstrip("/")
    return f"{base}/account/profile/?open=change-password"

def send_profile_change_password_email(user) -> tuple[bool, str]:
    """
    Envia o e-mail com o link para o Profile (abrindo o modal de troca de senha).
    Retorna (ok, detalhe).
    """
    email = (user.email or "").strip()
    if not email:
        return (False, "Usuário sem e-mail")

    ctx = {
        "user": user,
        "profile_change_url": _abs_profile_change_url(),
        "base_url": getattr(settings, "BASE_URL", ""),
    }

    subject = "Taskfy — Atualize sua senha"
    text_body = render_to_string("mail/change_password.txt", ctx)
    html_body = render_to_string("mail/change_password.html", ctx)

    msg = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[email],
    )
    msg.attach_alternative(html_body, "text/html")

    try:
        msg.send()
        return (True, "sent")
    except Exception as e:
        return (False, f"SMTP: {e!r}")
