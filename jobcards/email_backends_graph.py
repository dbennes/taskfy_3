# jobcards/email_backends_graph.py
from typing import List
from django.core.mail.backends.base import BaseEmailBackend
from django.conf import settings
from .email_providers import send_via_graph

def _extract_html(msg):
    # Se for EmailMultiAlternatives, usa o HTML
    for alt, ctype in getattr(msg, "alternatives", []):
        if ctype and ctype.lower() in ("text/html", "html"):
            return alt
    # Se content_subtype for html
    if getattr(msg, "content_subtype", "").lower() == "html":
        return msg.body or ""
    return None  # sem HTML

class GraphOnlyEmailBackend(BaseEmailBackend):
    """
    Converte EmailMessage/EmailMultiAlternatives do Django para teu provider send_via_graph.
    Abole SMTP completamente.
    """
    def send_messages(self, email_messages: List) -> int:
        if not email_messages:
            return 0
        sent = 0
        for m in email_messages:
            html = _extract_html(m)
            text = "" if html else (m.body or "")
            # Converte anexos do Django -> tuplas (nome, bytes, mimetype)
            atts = []
            for a in getattr(m, "attachments", []):
                if isinstance(a, (list, tuple)) and len(a) in (2,3):
                    atts.append(a)  # já está no formato esperado
                else:
                    # Se for MIMEBase/objeto, ignore ou trate conforme seu uso atual
                    pass

            ok, msg = send_via_graph(
                subject=m.subject or "",
                text_body=text,
                html_body=html,
                to_list=list(m.to or []),
                bcc_list=list(getattr(m, "bcc", []) or []),
                cc_list=list(getattr(m, "cc", []) or []),
                reply_to=(m.reply_to[0] if getattr(m, "reply_to", None) else None),
                sender=getattr(settings, "EMAIL_SENDER", None),
                attachments=atts,
                save_to_sent=True,
            )
            if not ok and settings.DEBUG:
                raise RuntimeError(msg)
            if ok:
                sent += 1
        return sent
