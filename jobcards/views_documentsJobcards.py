# jobcards/views_documentsJobcards.py
import os, mimetypes, json, re
from datetime import datetime
from io import BytesIO
from zipfile import ZipFile, ZIP_DEFLATED

from django.conf import settings
from django.http import JsonResponse, FileResponse, Http404, HttpResponse
from django.contrib.auth.decorators import login_required, permission_required
from urllib.parse import quote as urlquote

DOCS_SUBDIR = "documents_jobcards"
DOCS_DIR = os.path.join(settings.MEDIA_ROOT, DOCS_SUBDIR)
DOCS_URL = settings.MEDIA_URL + DOCS_SUBDIR + "/"

def _safe_basename(name: str) -> str:
    return os.path.basename(name or "")

def _guess_meta_from_name(name: str):
    """Extrai meta simples do nome (opcional): sys-XXX, wp-YYY, jc-ZZZ."""
    base = os.path.splitext(_safe_basename(name))[0]
    meta = {"system": "", "workpack": "", "jobcard": ""}
    patterns = {
        "system":   [r"\bsys-([A-Za-z0-9_-]+)", r"\bsystem-([A-Za-z0-9_-]+)"],
        "workpack": [r"\bwp-([A-Za-z0-9_-]+)", r"\bworkpack(?:ing)?-([A-Za-z0-9_-]+)"],
        "jobcard":  [r"\bjc-([A-Za-z0-9_-]+)", r"\bjobcard-([A-Za-z0-9_-]+)"],
    }
    for key, pats in patterns.items():
        for p in pats:
            m = re.search(p, base, flags=re.IGNORECASE)
            if m:
                meta[key] = m.group(1)
                break
    return meta

@login_required(login_url="login")
@permission_required("jobcards.view_jobcard", raise_exception=True)
def list_documents(request):
    """
    Retorna JSON com os arquivos em MEDIA/documents_jobcards.
    Filtros: ?q=&system=&workpack=&jobcard=
    """
    q        = (request.GET.get("q") or "").strip().lower()
    system   = (request.GET.get("system") or "").strip().lower()
    workpack = (request.GET.get("workpack") or "").strip().lower()
    jobcard  = (request.GET.get("jobcard") or "").strip().lower()

    items = []
    if not os.path.isdir(DOCS_DIR):
        return JsonResponse({"items": [], "total": 0})

    for fname in sorted(os.listdir(DOCS_DIR), key=lambda s: s.lower()):
        path = os.path.join(DOCS_DIR, fname)
        if not os.path.isfile(path):
            continue
        size  = os.path.getsize(path)
        mtime = int(os.path.getmtime(path))
        ext   = os.path.splitext(fname)[1].lower().lstrip(".")
        meta  = _guess_meta_from_name(fname)

        # filtros
        if q and q not in fname.lower():
            continue
        if system and system not in meta["system"].lower():
            continue
        if workpack and workpack not in meta["workpack"].lower():
            continue
        if jobcard and jobcard not in meta["jobcard"].lower():
            continue

        items.append({
            "name": fname,
            "url": DOCS_URL + urlquote(fname),
            "size": size,
            "mtime": mtime,
            "ext": ext,
            "system": meta["system"],
            "workpack": meta["workpack"],
            "jobcard": meta["jobcard"],
        })

    return JsonResponse({"items": items, "total": len(items)})

@login_required(login_url="login")
@permission_required("jobcards.view_jobcard", raise_exception=True)
def download_document(request):
    """Baixa um único documento: /documents/download/?name=arquivo.ext"""
    name = request.GET.get("name") or ""
    safe = _safe_basename(name)
    if not safe:
        raise Http404("File name required.")
    path = os.path.join(DOCS_DIR, safe)
    if not os.path.isfile(path):
        raise Http404("File not found.")

    mime, _ = mimetypes.guess_type(path)
    f = open(path, "rb")
    resp = FileResponse(f, as_attachment=True, filename=safe)
    if mime:
        resp["Content-Type"] = mime
    return resp

@login_required(login_url="login")
@permission_required("jobcards.view_jobcard", raise_exception=True)
def download_many_documents(request):
    """Baixa vários arquivos em um .zip (POST JSON: {"names": ["a.pdf", "b.docx"]})"""
    if request.method != "POST":
        return JsonResponse({"error": "POST only"}, status=405)

    try:
        data = json.loads(request.body.decode("utf-8"))
        names = data.get("names", [])
    except Exception:
        names = request.POST.getlist("names")

    if not names:
        return JsonResponse({"error": "No files selected"}, status=400)

    buf = BytesIO()
    with ZipFile(buf, "w", ZIP_DEFLATED) as zf:
        for n in names:
            safe = _safe_basename(n)
            p = os.path.join(DOCS_DIR, safe)
            if os.path.isfile(p):
                zf.write(p, arcname=safe)

    buf.seek(0)
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    resp = HttpResponse(buf.read(), content_type="application/zip")
    resp["Content-Disposition"] = f'attachment; filename="documents_{ts}.zip"'
    return resp
