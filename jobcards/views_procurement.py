# jobcards/views_procurement.py  (ou no seu arquivo de views)
import os
import mimetypes
from django.conf import settings
from django.http import FileResponse, Http404
from django.contrib.auth.decorators import login_required, permission_required

REFERENCE_DIR = os.path.join(settings.MEDIA_ROOT, "documents_jobcards")
REFERENCE_BASENAME = "procurement_reference"  # prefixo padrão (ex.: procurement_reference.pdf)

def _find_reference_path(request) -> str | None:
    # 0) Se vier um nome via GET (?name=xxx.ext), prioriza esse
    name = (request.GET.get("name") or "").strip()
    if name:
        # evita path traversal
        safe_name = os.path.basename(name)
        candidate = os.path.join(REFERENCE_DIR, safe_name)
        if os.path.isfile(candidate):
            return candidate

    # 1) Busca por um arquivo que comece com 'procurement_reference'
    if os.path.isdir(REFERENCE_DIR):
        for fname in os.listdir(REFERENCE_DIR):
            lower = fname.lower()
            if lower.startswith(REFERENCE_BASENAME) and not lower.endswith(".tmp"):
                path = os.path.join(REFERENCE_DIR, fname)
                if os.path.isfile(path):
                    return path

        # 2) Fallback: pega o arquivo mais recente da pasta
        files = [
            os.path.join(REFERENCE_DIR, f)
            for f in os.listdir(REFERENCE_DIR)
            if os.path.isfile(os.path.join(REFERENCE_DIR, f))
        ]
        if files:
            return max(files, key=os.path.getmtime)

    return None

@login_required(login_url="login")
@permission_required("jobcards.view_procurementbase", raise_exception=True)
def download_procurement_reference(request):
    ref_path = _find_reference_path(request)
    if not ref_path or not os.path.exists(ref_path):
        raise Http404("Reference document not found in MEDIA/documents_jobcards/.")

    mime, _ = mimetypes.guess_type(ref_path)
    filename = os.path.basename(ref_path)

    f = open(ref_path, "rb")
    resp = FileResponse(
        f,
        as_attachment=True,
        filename=filename,  # mantém o nome original
    )
    if mime:
        resp["Content-Type"] = mime
    return resp
