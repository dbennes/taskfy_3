# sistema/views_downloads_jobcards.py
from __future__ import annotations

import csv
import io
import os
import re
import zipfile
import datetime
from typing import List, Optional, Set

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse

from .models import JobCard  # só precisamos do número/revisão

# ============ CONFIG ============

# Resolve a pasta de backups de forma resiliente
# Preferência: settings.JOB_BACKUP_DIR; fallback: <BASE_DIR>/jobcard_backups
# (Manter string por compatibilidade com APIs de path existentes)
_base_dir = getattr(settings, "BASE_DIR", os.getcwd())
_default_backup = os.path.join(str(_base_dir), "jobcard_backups")
JOBCARD_PDF_DIR: str = str(getattr(settings, "JOB_BACKUP_DIR", _default_backup))

# Regex para normalizar números de JobCard (ex.: remover espaços)
_JOBCARD_RE = re.compile(r"\s+")


def _norm_jobcard_number(s: str) -> str:
    # Normaliza número de JobCard para comparação/lookup
    if not s:
        return ""
    return _JOBCARD_RE.sub("", s).strip()


# ============ Helpers para ZIP ============

def _zip_files_to_response(filepaths: List[str], zip_name: str) -> FileResponse:
    """
    Empacota os arquivos em um ZIP e retorna como download.
    - Usa BytesIO para conjuntos pequenos.
    - Para conjuntos grandes (> ~250MB), usa NamedTemporaryFile para evitar alto uso de RAM.
    """
    # soma aproximada do tamanho total
    total_size = 0
    existing_files: List[str] = []
    for fp in filepaths:
        if os.path.isfile(fp):
            existing_files.append(fp)
            try:
                total_size += os.path.getsize(fp)
            except OSError:
                pass

    # ===== Estratégia 1: ZIP em memória (rápido para poucos/pequenos arquivos) =====
    if total_size <= 250 * 1024 * 1024:  # ~250MB
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for fp in existing_files:
                arcname = os.path.basename(fp)  # evita traversal; nome simples
                zf.write(fp, arcname=arcname)
        buffer.seek(0)
        return FileResponse(buffer, as_attachment=True, filename=zip_name)

    # ===== Estratégia 2: ZIP em arquivo temporário (melhor para conjuntos grandes) =====
    import tempfile
    tmp = tempfile.NamedTemporaryFile(prefix="jobcards_", suffix=".zip", delete=False)
    tmp_path = tmp.name
    tmp.close()

    try:
        with zipfile.ZipFile(tmp_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for fp in existing_files:
                arcname = os.path.basename(fp)
                zf.write(fp, arcname=arcname)
        # FileResponse faz streaming do arquivo; o GC do SO limpará depois do envio se você quiser remover manualmente em outro processo.
        f = open(tmp_path, "rb")
        resp = FileResponse(f, as_attachment=True, filename=zip_name)
        # Dica: se quiser remoção automática do temporário após a resposta,
        # rode um cron/cleanup periódicos na pasta de temporários do sistema.
        return resp
    except Exception:
        # Se der erro, tenta remover o arquivo temporário
        try:
            os.remove(tmp_path)
        except Exception:
            pass
        raise


# ============ Localização de PDFs (sem regenerar) ============

def _pdf_filename(jobcard_number: str, rev: Optional[str]) -> str:
    """Nome de arquivo padrão mais comum no seu fluxo."""
    rev_tag = (rev or "R00").replace("/", "_").replace("\\", "_")
    return f"JobCard_{jobcard_number}_Rev_{rev_tag}.pdf"


def _ensure_backup_dir() -> None:
    """Garante a existência da pasta de backup (idempotente)."""
    try:
        os.makedirs(JOBCARD_PDF_DIR, exist_ok=True)
    except Exception:
        # Não impede fluxo; apenas falha silenciosa
        pass


def _find_existing_pdf_path(jobcard_number: str, rev: Optional[str]) -> Optional[str]:
    """
    Procura PDF existente em JOBCARD_PDF_DIR.
    1) Tenta nome exato "JobCard_<num>_Rev_<rev>.pdf"
    2) Fallback: qualquer "JobCard_<num>_Rev_*.pdf"
    3) Fallback 2: qualquer arquivo .pdf que contenha o número (último recurso)
    """
    if not JOBCARD_PDF_DIR:
        return None

    _ensure_backup_dir()

    # (1) exato
    exact = os.path.join(JOBCARD_PDF_DIR, _pdf_filename(jobcard_number, rev))
    if os.path.isfile(exact):
        return exact

    # (2) prefix match
    prefix = f"JobCard_{jobcard_number}_Rev_"
    try:
        for name in os.listdir(JOBCARD_PDF_DIR):
            if name.startswith(prefix) and name.lower().endswith(".pdf"):
                return os.path.join(JOBCARD_PDF_DIR, name)
    except FileNotFoundError:
        return None

    # (3) contains (permissivo)
    try:
        for name in os.listdir(JOBCARD_PDF_DIR):
            if jobcard_number in name and name.lower().endswith(".pdf"):
                return os.path.join(JOBCARD_PDF_DIR, name)
    except FileNotFoundError:
        return None

    return None


# ============ Parsers de arquivos (CSV/XLSX) ============

def _read_jobcards_from_csv(file) -> List[str]:
    # Lê CSV com cabeçalho 'jobcard_number'
    file.seek(0)
    decoded = io.TextIOWrapper(file, encoding="utf-8", errors="ignore")
    reader = csv.DictReader(decoded)
    jc: Set[str] = set()
    for row in reader:
        num = _norm_jobcard_number(row.get("jobcard_number", ""))
        if num:
            jc.add(num)
    return sorted(jc)


def _read_jobcards_from_xlsx(file) -> List[str]:
    # Lê XLSX com cabeçalho 'jobcard_number'
    try:
        import openpyxl  # leve, padrão de mercado
    except Exception as e:
        raise RuntimeError("To read .xlsx, install 'openpyxl' (pip install openpyxl).") from e

    file.seek(0)
    wb = openpyxl.load_workbook(file, data_only=True, read_only=True)
    ws = wb.active
    headers = []
    jc_col = None
    result: Set[str] = set()
    for i, row in enumerate(ws.iter_rows(values_only=True), start=1):
        if i == 1:
            headers = [str(c or "").strip().lower() for c in row]
            if "jobcard_number" in headers:
                jc_col = headers.index("jobcard_number")
            else:
                break
        else:
            if jc_col is None:
                break
            val = row[jc_col] if jc_col < len(row) else None
            num = _norm_jobcard_number(str(val or ""))
            if num:
                result.add(num)
    return sorted(result)


# ============ Views ============

@login_required
def page(request: HttpRequest) -> HttpResponse:
    """Página de downloads de JobCards (por lista ou todas)."""
    return render(request, "sistema/downloads_jobcards/downloads_jobcards.html")


@login_required
def download_template(request: HttpRequest) -> FileResponse:
    """CSV Template com cabeçalho 'jobcard_number'."""
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["jobcard_number"])
    data = io.BytesIO(buffer.getvalue().encode("utf-8"))
    return FileResponse(data, as_attachment=True, filename="jobcards_download.csv")


@login_required
def download_jobcards_by_list(request: HttpRequest) -> HttpResponse:
    if request.method != "POST":
        messages.warning(request, "Upload a CSV or XLSX file containing the 'jobcard_number' column.")
        return redirect(reverse("download_jobcards_page"))

    f = request.FILES.get("file")
    if not f:
        messages.error(request, "File not provided.")
        return redirect(reverse("download_jobcards_page"))

    # lê arquivo
    try:
        name = (f.name or "").lower()
        if name.endswith(".csv"):
            numbers = _read_jobcards_from_csv(f)
        elif name.endswith(".xlsx"):
            numbers = _read_jobcards_from_xlsx(f)
        else:
            messages.error(request, "Invalid format. Please upload a .csv or .xlsx file.")
            return redirect(reverse("download_jobcards_page"))
    except Exception as e:
        messages.error(request, f"Failed to read file: {e}")
        return redirect(reverse("download_jobcards_page"))

    if not numbers:
        messages.warning(request, "No valid JobCard numbers found in the file.")
        return redirect(reverse("download_jobcards_page"))

    # resolve PDFs (somente existentes)
    ok_paths: List[str] = []
    missing: List[str] = []

    # Busca revisão no banco só para tentar casar o nome exato primeiro
    rev_map = {
        jc.job_card_number: jc.rev
        for jc in JobCard.objects.filter(job_card_number__in=numbers).only("job_card_number", "rev")
    }

    for num in numbers:
        pdf_path = _find_existing_pdf_path(num, rev_map.get(num))
        if pdf_path:
            ok_paths.append(pdf_path)
        else:
            missing.append(num)

    if not ok_paths:
        messages.error(request, "No PDF found to package.")
        if missing:
            messages.info(
                request,
                f"Missing PDFs: {', '.join(missing[:12])}{' ...' if len(missing) > 12 else ''}"
            )
        return redirect(reverse("download_jobcards_page"))

    if missing:
        messages.warning(request, f"{len(missing)} JobCard(s) do not have a PDF in the backup folder.")

    # monta zip
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_name = f"jobcards_selected_{len(ok_paths)}_{ts}.zip"
    return _zip_files_to_response(ok_paths, zip_name)


@login_required
def download_all_jobcards(request: HttpRequest) -> HttpResponse:
    if request.method != "POST":
        return redirect(reverse("download_jobcards_page"))

    qs = JobCard.objects.all().only("job_card_number", "rev")
    if not qs.exists():
        messages.info(request, "There are no JobCards registered.")
        return redirect(reverse("download_jobcards_page"))

    ok_paths: List[str] = []
    missing: List[str] = []

    for job in qs:
        num = _norm_jobcard_number(job.job_card_number)
        if not num:
            continue
        pdf_path = _find_existing_pdf_path(num, job.rev)
        if pdf_path:
            ok_paths.append(pdf_path)
        else:
            missing.append(num)

    if not ok_paths:
        messages.error(request, "No PDF found to package.")
        if missing:
            messages.info(
                request,
                f"Missing PDFs: {', '.join(missing[:12])}{' ...' if len(missing) > 12 else ''}"
            )
        return redirect(reverse("download_jobcards_page"))

    if missing:
        messages.warning(request, f"{len(missing)} JobCard(s) do not have a PDF in the backup folder.")

    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_name = f"jobcards_all_{len(ok_paths)}_{ts}.zip"
    return _zip_files_to_response(ok_paths, zip_name)
