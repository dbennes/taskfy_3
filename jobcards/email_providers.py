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
    Converte anexos para o formato do Microsoft Graph.
    Aceita:
      - dict com chaves: name, contentBytes|content_bytes (opcional: contentType|content_type, isInline|is_inline, contentId|content_id)
      - tupla/lista:
          (name, bytes|str, [content_type])                      # comum
          (name, bytes|str, content_type, is_inline, content_id) # inline
    """
    out = []
    for att in (attachments or []):
        # ---- Dict (recomendado p/ inline) ----
        if isinstance(att, dict):
            name = att.get("name")
            cbytes = att.get("contentBytes") or att.get("content_bytes")
            ctype  = att.get("contentType") or att.get("content_type") or (mimetypes.guess_type(name or "")[0] or "application/octet-stream")
            is_inline = att.get("isInline") or att.get("is_inline") or False
            cid = att.get("contentId") or att.get("content_id")

            # contentBytes pode vir já em base64 ou bytes/str
            if cbytes and not isinstance(cbytes, str):
                if isinstance(cbytes, bytes):
                    cbytes = base64.b64encode(cbytes).decode("ascii")
                else:
                    # str "normal" -> bytes -> base64
                    cbytes = base64.b64encode(str(cbytes).encode("utf-8")).decode("ascii")

            node = {
                "@odata.type": "#microsoft.graph.fileAttachment",
                "name": name or "attachment",
                "contentType": ctype,
                "contentBytes": cbytes or "",
            }
            if is_inline:
                node["isInline"] = True
            if cid:
                node["contentId"] = cid
            out.append(node)
            continue

        # ---- Tupla/lista ----
        if isinstance(att, (list, tuple)):
            # formatos suportados:
            # (name, content) | (name, content, content_type) | (name, content, content_type, is_inline, content_id)
            name = att[0]
            content = att[1]
            ctype = None
            is_inline = False
            cid = None

            if len(att) >= 3 and att[2]:
                ctype = att[2]
            if len(att) >= 4:
                is_inline = bool(att[3])
            if len(att) >= 5:
                cid = att[4]

            if not ctype:
                ctype = mimetypes.guess_type(name)[0] or "application/octet-stream"

            if isinstance(content, str):
                content = content.encode("utf-8")

            node = {
                "@odata.type": "#microsoft.graph.fileAttachment",
                "name": name,
                "contentType": ctype,
                "contentBytes": base64.b64encode(content).decode("ascii"),
            }
            if is_inline:
                node["isInline"] = True
            if cid:
                node["contentId"] = cid

            out.append(node)
            continue

        # outros tipos: ignora
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
