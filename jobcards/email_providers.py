# jobcards/email_providers.py
from django.conf import settings
import requests, msal, base64, mimetypes, time

GRAPH_SCOPE = ["https://graph.microsoft.com/.default"]
GRAPH_BASE = "https://graph.microsoft.com/v1.0"

def _get_graph_token():
    cfg = getattr(settings, "MS_GRAPH", {})
    app = msal.ConfidentialClientApplication(
        client_id=cfg["CLIENT_ID"],
        authority=f"https://login.microsoftonline.com/{cfg['TENANT_ID']}",
        client_credential=cfg["CLIENT_SECRET"],
    )
    result = app.acquire_token_silent(GRAPH_SCOPE, account=None) or app.acquire_token_for_client(scopes=GRAPH_SCOPE)
    if "access_token" not in result:
        raise RuntimeError(f"Graph auth falhou: {result.get('error_description') or result}")
    return result["access_token"]

def _addr(a): 
    return {"emailAddress": {"address": a}} if a else None

def _mk_attachments(attachments):
    """
    attachments: lista de tuplas (nome, conteudo_bytes|str, mimetype_opcional)
    """
    out = []
    for att in (attachments or []):
        if not isinstance(att, (list, tuple)) or len(att) not in (2,3): 
            continue
        name, content = att[0], att[1]
        ctype = att[2] if len(att)==3 and att[2] else (mimetypes.guess_type(name)[0] or "application/octet-stream")
        if isinstance(content, str):
            content = content.encode("utf-8")
        out.append({
            "@odata.type": "#microsoft.graph.fileAttachment",
            "name": name,
            "contentType": ctype,
            "contentBytes": base64.b64encode(content).decode("ascii"),
        })
    return out

def send_via_graph(
    subject,
    text_body,
    html_body,
    to_list,
    bcc_list=None,
    cc_list=None,
    reply_to=None,
    sender=None,
    attachments=None,
    save_to_sent=True,
):
    """
    Envia via Microsoft Graph (sendMail) usando app-only.
    Mantém tua assinatura, só acrescentei cc/reply_to/anexos.
    """
    sender = sender or getattr(settings, "EMAIL_SENDER", None)
    if not sender:
        return (False, "EMAIL_SENDER não definido no settings.")

    token = _get_graph_token()
    url = f"{GRAPH_BASE}/users/{sender}/sendMail"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    to_rcpts  = [_addr(a) for a in (to_list  or []) if a]
    cc_rcpts  = [_addr(a) for a in (cc_list  or []) if a]
    bcc_rcpts = [_addr(a) for a in (bcc_list or []) if a]
    reply_to_list = [_addr(reply_to)] if reply_to else []

    body = {"contentType": "HTML", "content": html_body} if html_body else {"contentType": "Text", "content": text_body or ""}

    payload = {
        "message": {
            "subject": subject or "",
            "body": body,
            "toRecipients": to_rcpts,
            "ccRecipients": cc_rcpts,
            "bccRecipients": bcc_rcpts,
            "replyTo": reply_to_list,
            "attachments": _mk_attachments(attachments),
        },
        "saveToSentItems": bool(save_to_sent),
    }

    # Retry simples pra 429/5xx
    for attempt in range(4):
        r = requests.post(url, json=payload, headers=headers, timeout=30)
        if r.status_code in (202, 200):
            return (True, "ok")
        if r.status_code in (429, 500, 502, 503, 504) and attempt < 3:
            wait = int(r.headers.get("Retry-After", 2 ** attempt))
            time.sleep(min(wait, 8))
            continue
        return (False, f"Graph sendMail {r.status_code}: {r.text}")

    return (False, "Falha desconhecida ao enviar via Graph")
