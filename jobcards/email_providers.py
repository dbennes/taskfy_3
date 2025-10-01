# jobcards/email_providers.py
from django.conf import settings
import requests, msal

GRAPH_SCOPE = ["https://graph.microsoft.com/.default"]
GRAPH_BASE = "https://graph.microsoft.com/v1.0"

def _get_graph_token():
    cfg = getattr(settings, "MS_GRAPH", {})
    app = msal.ConfidentialClientApplication(
        client_id=cfg["CLIENT_ID"],
        authority=f"https://login.microsoftonline.com/{cfg['TENANT_ID']}",
        client_credential=cfg["CLIENT_SECRET"],
    )
    result = app.acquire_token_silent(GRAPH_SCOPE, account=None)
    if not result:
        result = app.acquire_token_for_client(scopes=GRAPH_SCOPE)
    if "access_token" not in result:
        raise RuntimeError(f"Graph auth falhou: {result.get('error_description')}")
    return result["access_token"]

def send_via_graph(subject, text_body, html_body, to_list, bcc_list=None, sender=None):
    sender = sender or getattr(settings, "EMAIL_SENDER", None)
    if not sender:
        return (False, "EMAIL_SENDER não definido no settings.")
    token = _get_graph_token()
    url = f"{GRAPH_BASE}/users/{sender}/sendMail"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    def _addr(a): return {"emailAddress": {"address": a}}
    to_rcpts = [_addr(a) for a in to_list]
    bcc_rcpts = [_addr(a) for a in (bcc_list or [])]

    # usa HTML se disponível, senão texto
    if html_body:
        body = {"contentType": "HTML", "content": html_body}
    else:
        body = {"contentType": "Text", "content": text_body or ""}

    payload = {
        "message": {
            "subject": subject,
            "body": body,
            "toRecipients": to_rcpts,
            "bccRecipients": bcc_rcpts,
        },
        "saveToSentItems": True,
    }
    r = requests.post(url, json=payload, headers=headers, timeout=30)
    if r.status_code in (202, 200):
        return (True, "ok")
    return (False, f"Graph sendMail {r.status_code}: {r.text}")
