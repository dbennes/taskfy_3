# jobcards/pdf_tasks.py
from django_rq import job
from django.core.cache import cache
from django_redis import get_redis_connection
from django.db import close_old_connections
from django.utils import timezone
from django.template.loader import render_to_string
from django.conf import settings
from django.core.files.storage import default_storage

import os
import tempfile
import hashlib
import json
import logging
import shutil

import pdfkit
import barcode
from barcode.writer import ImageWriter

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
    j = JobCard.objects.get(job_card_number=job_card_number)
    payload = {
        "jc": j.job_card_number,
        "rev": j.rev,
        "lm":  j.last_modified_at.isoformat() if j.last_modified_at else "",
        "stat": j.jobcard_status,
        "tools": list(AllocatedTool.objects.filter(jobcard_number=j.job_card_number)
                      .values("direct_labor", "qty", "qty_direct_labor", "special_tooling")),
        "mats":  list(AllocatedMaterial.objects.filter(jobcard_number=j.job_card_number)
                      .values("pmto_code","description","qty","nps1")),
        "tasks": list(AllocatedTask.objects.filter(jobcard_number=j.job_card_number)
                      .values("task_order","max_hours","total_hours","percent","not_applicable")),
        "eng":   list(AllocatedEngineering.objects.filter(jobcard_number=j.job_card_number)
                      .values("document","tag","rev","status")),
    }
    return hashlib.sha1(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()[:16]

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

def _render_jobcard_pdf_to_disk(job_card_number: str):
    job = JobCard.objects.get(job_card_number=job_card_number)
    area_info = Area.objects.filter(area_code=job.location).first() if job.location else None

    # Barcode (gera 1x por jobcard)
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

    # Atualiza status preliminar (mesma lógica da view)
    if job.jobcard_status != 'PRELIMINARY JOBCARD CHECKED':
        job.jobcard_status = 'PRELIMINARY JOBCARD CHECKED'
        if not job.checked_preliminary_by and not job.checked_preliminary_at:
            job.checked_preliminary_by = "worker"
            job.checked_preliminary_at = timezone.now()
            job.save(update_fields=['jobcard_status','checked_preliminary_by','checked_preliminary_at'])
        else:
            job.save(update_fields=['jobcard_status'])

    allocated_manpowers = AllocatedManpower.objects.filter(jobcard_number=job_card_number).order_by('task_order')
    allocated_materials = AllocatedMaterial.objects.filter(jobcard_number=job.job_card_number)
    allocated_tools = list(AllocatedTool.objects.filter(jobcard_number=job_card_number))
    allocated_tasks = AllocatedTask.objects.filter(jobcard_number=job_card_number).order_by('task_order')
    allocated_engineerings = AllocatedEngineering.objects.filter(jobcard_number=job.job_card_number)

    image_path = os.path.join(settings.BASE_DIR, 'static', 'assets', 'img', '3.jpg')
    image_url = f'file:///{image_path.replace("\\", "/")}'

    # Imagens anexas (até 4)
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

    # configura wkhtmltopdf
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

@job('pdf', timeout=60*60, result_ttl=24*60*60, failure_ttl=24*60*60)
def render_jobcard_pdf_job(run_id: str, job_card_number: str, owner_id: int, expected_fp: str):
    close_old_connections()

    # cancelado?
    if cache.get(f'pdf:{run_id}:stop'):
        cache.incr(f'pdf:{run_id}:done', 1)
        _log(run_id, f"STOP {job_card_number}")
        return "stopped"

    # fairness por usuário
    if not _acquire_user_slot(owner_id):
        _release_user_slot(owner_id)
        _log(run_id, f"THROTTLE {job_card_number}")
        raise Exception("USER_THROTTLE")

    # lock por jobcard
    if not _acquire_jobcard_lock(job_card_number):
        cache.incr(f'pdf:{run_id}:done', 1)
        _release_user_slot(owner_id)
        _log(run_id, f"SKIP-LOCK {job_card_number}")
        return "skipped-locked"

    try:
        # fingerprint atual (se mudou, atualiza o esperado só para persistir depois)
        current = compute_jobcard_fingerprint(job_card_number)
        if current != expected_fp:
            expected_fp = current

        ok, err = _render_jobcard_pdf_to_disk(job_card_number)

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
