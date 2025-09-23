# jobcards/pdf_tasks.py
from django_rq import job
from django.core.cache import cache
from django_redis import get_redis_connection
from django.db import close_old_connections
from django.utils import timezone
from django.template.loader import render_to_string
from django.conf import settings
from django.core.files.storage import default_storage
from collections import defaultdict

import os
import tempfile
import hashlib
import json
import logging
import shutil

import pdfkit
import barcode
from barcode.writer import ImageWriter
from decimal import Decimal, InvalidOperation

from .models import (
    JobCard, Area,
    AllocatedManpower, AllocatedMaterial, AllocatedTool, AllocatedTask, AllocatedEngineering
)

logger = logging.getLogger("pdf")

# ================= infra: locks / fairness =================

LOCK_TTL = 15 * 60           # segundos
USER_SEMAPHORE_TTL = 60      # segundos
USER_MAX_INFLIGHT = 2        # jobs concorrentes por usuário

def _r():
    return get_redis_connection("default")

def _acquire_jobcard_lock(jobnum: str) -> bool:
    return _r().set(f"lock:pdf:{jobnum}", 1, ex=LOCK_TTL, nx=True)

def _release_jobcard_lock(jobnum: str):
    _r().delete(f"lock:pdf:{jobnum}")

def _acquire_user_slot(user_id: int) -> bool:
    pipe = _r().pipeline()
    key = f"quota:pdf:user:{user_id}"
    pipe.incr(key)
    pipe.expire(key, USER_SEMAPHORE_TTL)
    current, _ = pipe.execute()
    return int(current) <= USER_MAX_INFLIGHT

def _release_user_slot(user_id: int):
    _r().decr(f"quota:pdf:user:{user_id}")


def _to_float(x):
    """Converte com segurança para float (aceita str com vírgula)."""
    if x is None:
        return 0.0
    if isinstance(x, (int, float)):
        return float(x)
    if isinstance(x, Decimal):
        return float(x)
    if isinstance(x, str):
        s = x.strip()
        # trata "1.234,56" e "1234,56"
        if ',' in s:
            s = s.replace('.', '').replace(',', '.')
        try:
            return float(s)
        except Exception:
            return 0.0
    try:
        return float(x)
    except Exception:
        return 0.0

# ================= log simples no Redis (para o modal) =================

def _log(run_id: str, message: str):
    if not run_id:
        return
    r = get_redis_connection("default")
    key = f"pdf:{run_id}:log"
    try:
        r.rpush(key, message)
        r.ltrim(key, -500, -1)      # mantém últimas 500 linhas
        r.expire(key, 60*60*24)      # 24h
    except Exception:
        pass

# ================= fingerprint (dedupe) =================

def compute_jobcard_fingerprint(job_card_number: str) -> str:
    """
    Fingerprint robusto: inclui todos os campos exibidos no PDF e
    todos os recursos alocados, sempre com ordenação determinística.
    """
    j = JobCard.objects.get(job_card_number=job_card_number)

    job_payload = {
        "jc": j.job_card_number,
        "rev": j.rev,
        "jobcard_status": j.jobcard_status,
        "prepared_by": j.prepared_by,
        "date_prepared": (j.date_prepared.isoformat() if j.date_prepared else ""),
        "approved_br": j.approved_br,
        "date_approved": (j.date_approved.isoformat() if j.date_approved else ""),
        "subsystem": j.subsystem,
        "discipline": j.discipline,
        "working_code": j.working_code,
        "working_code_description": j.working_code_description,
        "system": j.system,
        "location": j.location,
        "level": getattr(j, "level", "") or "",
        "workpack_number": getattr(j, "workpack_number", "") or "",
        "seq_number": getattr(j, "seq_number", "") or "",
        "tag": j.tag,
        "unit": getattr(j, "unit", "") or "",
        "total_man_hours": _to_float(getattr(j, "total_man_hours", 0)),
        "job_card_description": getattr(j, "job_card_description", "") or "",
        "comments": j.comments,
        "activity_id": j.activity_id,
        "hot_work_required": j.hot_work_required,
        "total_weight": _to_float(getattr(j, "total_weight", 0)),
        "total_duration_hs": _to_float(getattr(j, "total_duration_hs", 0)),
        "company_comments": getattr(j, "company_comments", ""),
        "last_modified_at": j.last_modified_at.isoformat() if getattr(j, "last_modified_at", None) else "",
        # imagens (se existirem no seu model)
        "image_1": getattr(getattr(j, "image_1", None), "name", ""),
        "image_2": getattr(getattr(j, "image_2", None), "name", ""),
        "image_3": getattr(getattr(j, "image_3", None), "name", ""),
        "image_4": getattr(getattr(j, "image_4", None), "name", ""),
    }

    payload = {
        "job": job_payload,

        # MANPOWER
        "manp": list(
            AllocatedManpower.objects
            .filter(jobcard_number=j.job_card_number)
            .order_by("task_order", "direct_labor", "id")
            .values("task_order", "direct_labor", "hours", "qty")
        ),

        # TOOLS
        "tools": list(
            AllocatedTool.objects
            .filter(jobcard_number=j.job_card_number)
            .order_by("direct_labor", "special_tooling", "id")
            .values("direct_labor", "qty", "qty_direct_labor", "special_tooling")
        ),

        # MATERIALS
        "mats": list(
            AllocatedMaterial.objects
            .filter(jobcard_number=j.job_card_number)
            .order_by("pmto_code", "id")
            .values("pmto_code", "description", "qty", "nps1", "comments")
        ),

        # TASKS
        "tasks": list(
            AllocatedTask.objects
            .filter(jobcard_number=j.job_card_number)
            .order_by("task_order", "id")
            .values("task_order", "description", "max_hours", "total_hours",
                    "percent", "not_applicable", "completed")
        ),

        # ENGINEERING
        "eng": list(
            AllocatedEngineering.objects
            .filter(jobcard_number=j.job_card_number)
            .order_by("discipline", "document", "tag", "id")
            .values("discipline", "document", "tag", "rev", "status")
        ),
    }

    return hashlib.sha1(
        json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()[:16]

# ================= wkhtmltopdf helper =================

def _find_wkhtmltopdf() -> str | None:
    # 1) settings.WKHTMLTOPDF_BIN (se setado)
    bin_path = getattr(settings, "WKHTMLTOPDF_BIN", None)
    if bin_path and os.path.exists(bin_path):
        return bin_path

    # 2) pasta padrão do projeto (Windows)
    candidate = os.path.join(settings.BASE_DIR, "wkhtmltopdf", "bin", "wkhtmltopdf.exe")
    if os.path.exists(candidate):
        return candidate

    # 3) Program Files (Windows)
    candidates = [
        r"C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe",
        r"C:\Program Files (x86)\wkhtmltopdf\bin\wkhtmltopdf.exe",
        "/usr/bin/wkhtmltopdf",
        "/usr/local/bin/wkhtmltopdf",
    ]
    for c in candidates:
        if os.path.exists(c):
            return c

    # 4) PATH
    which = shutil.which("wkhtmltopdf")
    return which

# ================= renderizador (usa seus templates) =================

# jobcards/pdf_tasks.py
def _render_jobcard_pdf_to_disk(
    job_card_number: str,
    *,
    status_override: str | None = None,
):
    job = JobCard.objects.get(job_card_number=job_card_number)
    area_info = Area.objects.filter(area_code=job.location).first() if job.location else None

    # === POLÍTICA DE STATUS ===
    # NUNCA alterar status no render, a menos que receba override explícito.
    if status_override is not None and job.jobcard_status != status_override:
        job.jobcard_status = status_override
        job.save(update_fields=['jobcard_status'])

    # ---------- Barcode ----------
    barcode_folder = os.path.join(settings.BASE_DIR, 'static', 'barcodes')
    os.makedirs(barcode_folder, exist_ok=True)
    barcode_filename = f'{job.job_card_number}.png'
    barcode_path = os.path.join(barcode_folder, barcode_filename)
    if not os.path.exists(barcode_path):
        CODE128 = barcode.get_barcode_class('code128')
        code128 = CODE128(job.job_card_number, writer=ImageWriter())
        with open(barcode_path, 'wb') as fh:
            code128.write(fh, options={'write_text': False})
    barcode_url = f'file:///{barcode_path.replace("\\", "/")}'

    # === DADOS ===
    allocated_manpowers = list(
        AllocatedManpower.objects.filter(jobcard_number=job_card_number).order_by('task_order')
    )
    allocated_materials = AllocatedMaterial.objects.filter(jobcard_number=job.job_card_number)
    allocated_tasks     = AllocatedTask.objects.filter(jobcard_number=job_card_number).order_by('task_order')
    allocated_engineerings = AllocatedEngineering.objects.filter(jobcard_number=job.job_card_number)

    # Recalcular ferramentas em função do DL alocado
    dl_qty = defaultdict(float)
    for mp in allocated_manpowers:
        if mp.direct_labor:
            dl_key = (mp.direct_labor or "").strip().upper()
            dl_qty[dl_key] += float(mp.qty or 0)

    _all_tools = list(AllocatedTool.objects.filter(jobcard_number=job_card_number))
    effective_tools = []
    for t in _all_tools:
        dl_key = (t.direct_labor or "").strip().upper()

        if not dl_key:
            base_qty = float(t.qty or 0)
            if base_qty > 0:
                t.qty = base_qty
                effective_tools.append(t)
            continue

        if dl_key in dl_qty:
            if t.qty_direct_labor is not None:
                computed = float(t.qty_direct_labor or 0) * dl_qty[dl_key]
            else:
                computed = float(t.qty or 0)
            if computed > 0:
                t.qty = computed
                effective_tools.append(t)

    allocated_tools = effective_tools

    image_path = os.path.join(settings.BASE_DIR, 'static', 'assets', 'img', '3.jpg')
    image_url = f'file:///{image_path.replace("\\", "/")}'

    image_files = {}
    for i in range(1, 5):
        field = f'image_{i}'
        f = getattr(job, field, None)
        if f:
            try:
                if hasattr(f, 'path') and os.path.exists(f.path):
                    image_files[field] = 'file:///' + f.path.replace('\\', '/')
                elif hasattr(f, 'name') and default_storage.exists(f.name):
                    storage_path = default_storage.path(f.name)
                    image_files[field] = 'file:///' + storage_path.replace('\\', '/')
                elif hasattr(f, 'url'):
                    image_files[field] = f.url
                else:
                    image_files[field] = None
            except Exception:
                image_files[field] = getattr(f, 'url', None)
        else:
            image_files[field] = None

    half = len(allocated_tools) // 2 if allocated_tools else 0

    context = {
        'job': job,
        'allocated_manpowers': allocated_manpowers,
        'allocated_materials': allocated_materials,
        'allocated_tools': allocated_tools,
        'allocated_tools_left': allocated_tools[:half],
        'allocated_tools_right': allocated_tools[half:],
        'allocated_tasks': allocated_tasks,
        'allocated_engineerings': allocated_engineerings,
        'image_path': image_url,
        'barcode_image': barcode_url,
        'area_info': area_info,
        'image_files': image_files,
    }

    html = render_to_string('sistema/jobcard_pdf.html', context)
    header_html = render_to_string('sistema/header.html', context)
    footer_html = render_to_string('sistema/footer.html', context)

    header_temp = tempfile.NamedTemporaryFile(delete=False, suffix='.html')
    header_temp.write(header_html.encode('utf-8')); header_temp.close()
    footer_temp = tempfile.NamedTemporaryFile(delete=False, suffix='.html')
    footer_temp.write(footer_html.encode('utf-8')); footer_temp.close()

    wkhtml = _find_wkhtmltopdf()
    local_config = pdfkit.configuration(wkhtmltopdf=wkhtml) if wkhtml else None

    try:
        pdf_bytes = pdfkit.from_string(
            html, False, configuration=local_config,
            options={
                'enable-local-file-access': None,
                'margin-top': '35mm',
                'margin-bottom': '30mm',
                'header-html': f'file:///{header_temp.name.replace("\\", "/")}',
                'footer-html': f'file:///{footer_temp.name.replace("\\", "/")}',
                'header-spacing': '5',
                'footer-spacing': '5',
                'quiet': ''
            }
        )
    finally:
        try: os.unlink(header_temp.name)
        except: pass
        try: os.unlink(footer_temp.name)
        except: pass

    backups_dir = getattr(settings, 'JOB_BACKUP_DIR', os.path.join(settings.BASE_DIR, 'jobcard_backups'))
    os.makedirs(backups_dir, exist_ok=True)
    backup_filename = f'JobCard_{job_card_number}_Rev_{job.rev}.pdf'
    with open(os.path.join(backups_dir, backup_filename), 'wb') as f:
        f.write(pdf_bytes)

    return True, None


# ================= RQ Job (executa no worker) =================

# jobcards/pdf_tasks.py
@job('pdf', timeout=60*60, result_ttl=24*60*60, failure_ttl=24*60*60)
def render_jobcard_pdf_job(run_id: str, job_card_number: str, owner_id: int, expected_fp: str):
    close_old_connections()

    if cache.get(f'pdf:{run_id}:stop'):
        cache.incr(f'pdf:{run_id}:done', 1)
        _log(run_id, f"STOP {job_card_number}")
        return "stopped"

    if not _acquire_user_slot(owner_id):
        _release_user_slot(owner_id)
        _log(run_id, f"THROTTLE {job_card_number}")
        raise Exception("USER_THROTTLE")

    if not _acquire_jobcard_lock(job_card_number):
        cache.incr(f'pdf:{run_id}:done', 1)
        _release_user_slot(owner_id)
        _log(run_id, f"SKIP-LOCK {job_card_number}")
        return "skipped-locked"

    try:
        current = compute_jobcard_fingerprint(job_card_number)
        if current != expected_fp:
            expected_fp = current

        # Lote NUNCA altera status
        ok, err = _render_jobcard_pdf_to_disk(
            job_card_number,
            status_override=None
        )

        cache.incr(f'pdf:{run_id}:done', 1)
        if ok:
            cache.incr(f'pdf:{run_id}:ok', 1)
            cache.set(f'pdf:lastfp:{job_card_number}', expected_fp, 60*60*24*30)
            _log(run_id, f"OK {job_card_number}")
            return "ok"
        else:
            cache.incr(f'pdf:{run_id}:err', 1)
            _log(run_id, f"ERR {job_card_number}: {err or 'unknown'}")
            return f"err: {err}"

    except Exception as e:
        cache.incr(f'pdf:{run_id}:done', 1)
        cache.incr(f'pdf:{run_id}:err', 1)
        _log(run_id, f"ERR {job_card_number}: {e}")
        raise
    finally:
        _release_jobcard_lock(job_card_number)
        _release_user_slot(owner_id)
