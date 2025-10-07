import base64
import mimetypes
from typing import Optional, Dict
from django.contrib.staticfiles import finders

def build_inline_attachment(static_path: str, cid: str, name: Optional[str] = None) -> Optional[Dict]:
    """
    Gera um dict de anexo inline compatível com Microsoft Graph:
    {
      "@odata.type": "#microsoft.graph.fileAttachment",
      "name": "logo.png",
      "contentType": "image/png",
      "isInline": True,
      "contentId": "logo-taskfy",
      "contentBytes": "<BASE64>"
    }
    """
    file_path = finders.find(static_path)
    if not file_path:
        return None

    with open(file_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")

    ctype, _ = mimetypes.guess_type(static_path)
    return {
        "@odata.type": "#microsoft.graph.fileAttachment",
        "name": name or static_path.split("/")[-1],
        "contentType": ctype or "image/png",
        "isInline": True,
        "contentId": cid,
        "contentBytes": b64,
    }
