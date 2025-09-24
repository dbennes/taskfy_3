# -*- coding: utf-8 -*-
# jobcards/pdf_tasks.py
from django_rq import job
from django.core.cache import cache
from django_redis import get_redis_connection
from django.db import close_old_connections, transaction
from django.db.models import Sum
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
from decimal import Decimal, InvalidOperation  # global import (boa pratica)

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


def _to_float(x) -> float:
    """
    Safe float conversion.
    Accepts: None, int, float, Decimal, str (pt-BR like '1.234,56').
    Returns 0.0 on failure.
    """
    # Import local garante Decimal mesmo se algo bugar no import global
    try:
        from decimal import Decimal as _Dec, InvalidOperation as _Inv
    except Exception:  # fallback extremo
        class _Dec(float): ...
        class _Inv(Exception): ...
    if x is None:
        return 0.0
    if isinstance(x, float):
        return x
    if isinstance(x, int):
        return float(x)
    # checa Decimal sem depender do global
    if isinstance(x, _Dec):
        return float(x)
    if isinstance(x, str):
        s = x.strip()
        if not s:
            return 0.0
        # 1) tenta direto
        try:
            return float(s)
        except ValueError:
            pass
        # 2) tenta Decimal direto
        try:
            return float(_Dec(s))
        except (ValueError, _Inv):
            pass
        # 3) heuristica BR: "1.234,56" -> "1234.56"
        try:
            s2 = s.replace(" ", "")
            s2 = s2.replace(".", "").replace(",", ".")
            return float(_Dec(s2))
        except (ValueError, _Inv):
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

def compute_jobcard_fingerprint(job_ref) -> str:
    """
    Robust fingerprint: includes all fields printed on PDF and
    all allocated resources, with deterministic ordering.

    Accepts:
      - job_ref = str (job_card_number)
      - job_ref = JobCard (instance)
    """
    if isinstance(job_ref, JobCard):
        j = job_ref
    else:
        j = JobCard.objects.get(job_card_number=str(job_ref))

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
        # images
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
    # 1) settings.WKHTMLTOPDF_BIN
    bin_path = getattr(settings, "WKHTMLTOPDF_BIN", None)
    if bin_path and os.path.exists(bin_path):
        return bin_path

    # 2) projeto (Windows)
    candidate = os.path.join(str(getattr(settings, "BASE_DIR", "")), "wkhtmltopdf", "bin", "wkhtmltopdf.exe")
    if os.path.exists(candidate):
        return candidate

    # 3) Program Files (Windows) / Linux
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


# ================= SYNC (ÚNICA FUNÇÃO NOVA) =================

def _sync_allocations_from_bases(job, *, delete_missing: bool = True) -> None:
    """
    Atualiza/cria/limpa os Allocated* de um JobCard com base nos bancos Base.
    - Persiste as mudanças ANTES de gerar o PDF.
    - Preserva progresso do usuário em AllocatedTask (completed/percent/not_applicable).
    - Recalcula qty de ferramentas quando houver qty_direct_labor (multiplica pelo total de DL alocado).
    - Se delete_missing=True, remove dos Allocated o que saiu dos Bases.
    """
    # imports locais para não alterar os imports globais
    from .models import ManpowerBase, ToolsBase, TaskBase, MaterialBase, AllocatedManpower, AllocatedTool, AllocatedTask, AllocatedMaterial

    def _norm(s):
        return (s or "").strip().upper()

    def _dec(v):
        try:
            return Decimal(str(v))
        except Exception:
            return Decimal("0")

    jc = job.job_card_number

    @transaction.atomic
    def _run():
        # ===== MANPOWER =====
        mp_bases = list(ManpowerBase.objects.filter(
            discipline=job.discipline,
            working_code=job.working_code
        ))

        # task_order padrão = primeiro do TaskBase ou 1
        first_task = TaskBase.objects.filter(
            discipline=job.discipline, working_code=job.working_code
        ).order_by("order").first()
        default_task_order = first_task.order if first_task else 1

        base_mp_keys = set()
        for b in mp_bases:
            base_mp_keys.add(b.direct_labor)
            obj, _ = AllocatedManpower.objects.get_or_create(
                jobcard_number=jc,
                direct_labor=b.direct_labor,
                defaults={"task_order": default_task_order},
            )
            obj.discipline = b.discipline
            obj.working_code = b.working_code
            obj.qty = _dec(b.qty)
            obj.hours = _dec(b.qty)        # ajuste a fórmula se necessário
            if not obj.task_order:
                obj.task_order = default_task_order
            obj.save()

        if delete_missing:
            AllocatedManpower.objects.filter(jobcard_number=jc).exclude(
                direct_labor__in=list(base_mp_keys)
            ).delete()

        # Mapa DL -> soma qty alocada
        mp_qty_by_dl_qs = (
            AllocatedManpower.objects
            .filter(jobcard_number=jc)
            .values("direct_labor")
            .annotate(total=Sum("qty"))
        )
        mp_qty_by_dl = { _norm(r["direct_labor"]): (r["total"] or Decimal("0")) for r in mp_qty_by_dl_qs }

        # ===== TOOLS =====
        tool_bases = list(ToolsBase.objects.filter(
            discipline=job.discipline,
            working_code=job.working_code
        ))

        base_tool_keys = set()
        for t in tool_bases:
            base_tool_keys.add(t.special_tooling)
            obj, _ = AllocatedTool.objects.get_or_create(
                jobcard_number=jc,
                special_tooling=t.special_tooling,
            )
            obj.discipline = t.discipline
            obj.working_code = t.working_code
            obj.direct_labor = t.direct_labor
            obj.qty_direct_labor = _dec(t.qty_direct_labor)

            # Se houver qty_direct_labor -> multiplica pelo total de DL alocado
            # Senão usa qty fixo do Base (se existir)
            dl_total = mp_qty_by_dl.get(_norm(t.direct_labor), Decimal("0"))
            if t.qty_direct_labor is not None:
                obj.qty = _dec(t.qty_direct_labor) * dl_total
            else:
                obj.qty = _dec(getattr(t, "qty", 0))
            obj.save()

        if delete_missing:
            AllocatedTool.objects.filter(jobcard_number=jc).exclude(
                special_tooling__in=list(base_tool_keys)
            ).delete()

        # ===== TASKS =====
        task_bases = list(TaskBase.objects.filter(
            discipline=job.discipline,
            working_code=job.working_code
        ).order_by("order"))

        base_task_orders = set()
        for tb in task_bases:
            base_task_orders.add(tb.order)
            obj, _ = AllocatedTask.objects.get_or_create(
                jobcard_number=jc,
                task_order=tb.order,
            )
            # atualiza apenas o que vem do Base; preserva progresso do usuário
            if obj.description != tb.typical_task:
                obj.description = tb.typical_task
                obj.save(update_fields=["description"])

        if delete_missing:
            AllocatedTask.objects.filter(jobcard_number=jc).exclude(
                task_order__in=list(base_task_orders)
            ).delete()

        # ===== MATERIALS =====
        mats_base = list(MaterialBase.objects.filter(job_card_number=jc))

        def _mat_key(m):
            # Chave estável para o allocated: prioriza item, senão descrição
            if getattr(m, "item", None) is not None:
                return f"ITEM:{m.item}"
            desc = (m.description or "").strip()
            return f"DESC:{desc[:64]}" if desc else f"ROW:{getattr(m, 'pk', id(m))}"

        base_mat_codes = set()
        for m in mats_base:
            code = _mat_key(m)
            base_mat_codes.add(code)
            obj, _ = AllocatedMaterial.objects.get_or_create(
                jobcard_number=jc,
                pmto_code=code,
            )
            obj.discipline = m.discipline
            obj.working_code = m.working_code
            obj.description = m.description
            obj.qty = _dec(getattr(m, "qty", 0))
            obj.nps1 = getattr(m, "nps1", None)
            obj.comments = getattr(m, "comments", None)
            obj.save()

        if delete_missing:
            AllocatedMaterial.objects.filter(jobcard_number=jc).exclude(
                pmto_code__in=list(base_mat_codes)
            ).delete()

    _run()


# ================= renderizador (usa seus templates) =================

def _render_jobcard_pdf_to_disk(
    job_card_number: str,
    *,
    status_override: str | None = None,
):
    job = JobCard.objects.get(job_card_number=job_card_number)
    area_info = Area.objects.filter(area_code=job.location).first() if job.location else None

    # 🔥 SINCRONIZA os Allocated* com os Bancos Base ANTES de gerar o PDF
    _sync_allocations_from_bases(job, delete_missing=True)

    # === POLITICA DE STATUS ===
    if status_override is not None and job.jobcard_status != status_override:
        job.jobcard_status = status_override
        job.save(update_fields=['jobcard_status'])

    # ---------- Barcode ----------
    base_dir = str(getattr(settings, "BASE_DIR", ""))
    barcode_folder = os.path.join(base_dir, 'static', 'barcodes')
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

    # Recalcular ferramentas conforme DL alocado (para exibição no PDF)
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

    image_path = os.path.join(base_dir, 'static', 'assets', 'img', '3.jpg')
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
                'enable-local-file-access': '',
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

    backups_dir = str(getattr(settings, 'JOB_BACKUP_DIR',
                              os.path.join(base_dir, 'jobcard_backups')))
    os.makedirs(backups_dir, exist_ok=True)
    rev_tag = (job.rev or "R00").replace("/", "_").replace("\\", "_")
    backup_filename = f'JobCard_{job_card_number}_Rev_{rev_tag}.pdf'
    with open(os.path.join(backups_dir, backup_filename), 'wb') as f:
        f.write(pdf_bytes)

    return True, None


# ================= RQ Job (executa no worker) =================

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

        ok, err = _render_jobcard_pdf_to_disk(
            job_card_number,
            status_override=None  # nunca altera status em lote
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
