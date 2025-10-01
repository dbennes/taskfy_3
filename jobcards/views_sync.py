# jobcards/views_sync.py
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Dict, Set, List, Tuple
from django.db import transaction
from django.http import JsonResponse, HttpRequest
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import get_object_or_404

import unicodedata, re

from .models import (
    JobCard,
    ToolsBase, MaterialBase, EngineeringBase, TaskBase,
    AllocatedManpower, AllocatedTool, AllocatedMaterial, AllocatedEngineering, AllocatedTask,
)

# =========================================================
# Helpers (numéricos / strings)
# =========================================================

def _dec2(x) -> Decimal:
    """Converte para Decimal(2) com fallback 0.00 (previne NULL/InvalidOperation)."""
    try:
        if x is None or x == "":
            return Decimal("0.00")
        return Decimal(str(x)).quantize(Decimal("0.00"))
    except (InvalidOperation, ValueError, TypeError):
        return Decimal("0.00")

def _sx(s: str | None, maxlen: int) -> str:
    """Trunca string ao max_length do model (evita DataError)."""
    s = "" if s is None else str(s)
    return s[:maxlen]

# --- Limpeza/normalização de nomes de ferramentas ---
# Mantém aspas " (polegadas), dígitos, letras e pontuações comuns de catálogos.
# Remove zero-width/control, normaliza aspas/tipografia, compacta espaços.
_ALLOWED = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 /"\'()-_.:%&+[]')

_ZW_CONTROL_RE = re.compile(r"[\u200B-\u200F\u202A-\u202E]")  # zeros-width / bidi controls
_WS_RE = re.compile(r"\s+")

def _clean_tool_name(s: str | None) -> str:
    if not s:
        return ""
    # Normaliza forma Unicode (ex.: ″ → ")
    s = unicodedata.normalize("NFKC", str(s))
    # Equaliza aspas e traços tipográficos
    s = (s
         .replace("“", '"').replace("”", '"').replace("‟", '"').replace("″", '"')
         .replace("’", "'").replace("‘", "'")
         .replace("–", "-").replace("—", "-"))
    # Remove controles/zero-width
    s = _ZW_CONTROL_RE.sub("", s)
    # Filtra caracteres não permitidos (mantém aspas de polegadas)
    s = "".join(ch for ch in s if ch.isprintable() and ch in _ALLOWED)
    # Compacta espaços
    s = _WS_RE.sub(" ", s).strip()
    return s

# =========================================================
# Critério de elegibilidade por status
# =========================================================

_EXCLUDE_STATUSES: Set[str] = {"NO CHECKED", "NOT CHECKED"}

def _is_eligible_status(status: str | None) -> bool:
    s = (status or "").strip().upper()
    return bool(s) and s not in _EXCLUDE_STATUSES

# =========================================================
# Sync: somente descrição das tasks (não cria/apaga)
# =========================================================

def _sync_task_descriptions_for_job(job: JobCard) -> Dict[str, int]:
    """Atualiza SOMENTE AllocatedTask.description a partir de TaskBase.typical_task (match por order)."""
    jc   = (job.job_card_number or "").strip()
    disc = (job.discipline or "").strip()
    wkc  = (job.working_code or "").strip()

    base_tasks = (
        TaskBase.objects
        .filter(discipline=disc, working_code=wkc)
        .only("order", "typical_task")
        .order_by("order")
    )
    base_by_order = {b.order: (b.typical_task or "").strip() for b in base_tasks}
    if not base_by_order:
        return {"updated": 0, "created": 0, "deleted": 0, "unchanged": 0}

    alloc_qs = (
        AllocatedTask.objects
        .filter(jobcard_number=jc)
        .only("id", "task_order", "description")
    )
    by_order = {a.task_order: a for a in alloc_qs}

    changed: List[AllocatedTask] = []
    updated = 0
    unchanged = 0

    for order, base_desc in base_by_order.items():
        a = by_order.get(order)
        if not a:
            continue
        current = (a.description or "").strip()
        if current != base_desc:
            a.description = base_desc
            changed.append(a)
        else:
            unchanged += 1

    if changed:
        AllocatedTask.objects.bulk_update(changed, ["description"], batch_size=1000)
        updated = len(changed)

    return {"updated": updated, "created": 0, "deleted": 0, "unchanged": unchanged}

# =========================================================
# Mirror: Materials / Tools / Engineering (não toca Manpower)
# - Tools: 1 linha por (working_code, direct_labor, special_tooling LIMPO)
# - Tools.qty = qty da base (sem somar/multiplicar)
# - Materials.pmto_code = project_code
# - Após M/T/E: sincroniza descrição das tasks
# =========================================================

@transaction.atomic
def _mirror_allocated_mte_for_job(job: JobCard) -> Dict[str, Dict[str, int]]:
    jc   = _sx(job.job_card_number, 100)
    disc = (job.discipline or "").strip()
    wkc  = (job.working_code or "").strip()

    report = {
        "materials":   {"deleted": 0, "created": 0, "updated": 0, "unchanged": 0},
        "tools":       {"deleted": 0, "created": 0, "updated": 0, "unchanged": 0},
        "engineering": {"deleted": 0, "created": 0, "updated": 0, "unchanged": 0},
        "tasks":       {"deleted": 0, "created": 0, "updated": 0, "unchanged": 0},
    }

    # -------- limpa tudo do Allocated (M/T/E) desta JC --------
    m_qs = AllocatedMaterial.objects.filter(jobcard_number=jc)
    t_qs = AllocatedTool.objects.filter(jobcard_number=jc)
    e_qs = AllocatedEngineering.objects.filter(jobcard_number=jc)

    report["materials"]["deleted"]   = m_qs.count()
    report["tools"]["deleted"]       = t_qs.count()
    report["engineering"]["deleted"] = e_qs.count()

    m_qs.delete(); t_qs.delete(); e_qs.delete()

    # -------- DL presente (para filtrar Tools por DL) --------
    dl_present = {
        (dl or "").strip().upper()
        for dl, in AllocatedManpower.objects
                    .filter(jobcard_number=jc)
                    .values_list("direct_labor", flat=False)
    }

    # ======================= MATERIALS =======================
    base_mats = (
        MaterialBase.objects
        .filter(job_card_number=jc)
        .only("job_card_number", "discipline", "working_code",
              "project_code", "description", "qty", "jobcard_required_qty",
              "comments", "nps1")
        .iterator(chunk_size=1000)
    )

    new_mats: list[AllocatedMaterial] = []
    for b in base_mats:
        pmto = _sx((b.project_code or "").strip(), 100)

        new_mats.append(AllocatedMaterial(
            jobcard_number = jc,
            discipline     = _sx((getattr(b, "discipline", None) or disc), 50),
            working_code   = _sx((getattr(b, "working_code", None) or wkc), 50),
            pmto_code      = pmto,
            description    = (b.description or "").strip(),
            qty            = _dec2(getattr(b, "qty", None) or getattr(b, "jobcard_required_qty", None)),
            comments       = (getattr(b, "comments", "") or ""),
            nps1           = _sx((getattr(b, "nps1", "") or ""), 50),
        ))

        if len(new_mats) >= 1000:
            AllocatedMaterial.objects.bulk_create(new_mats, batch_size=1000)
            report["materials"]["created"] += len(new_mats)
            new_mats.clear()

    if new_mats:
        AllocatedMaterial.objects.bulk_create(new_mats, batch_size=1000)
        report["materials"]["created"] += len(new_mats)

    # ======================= TOOLS =======================
    # Regra: 1 linha por (WKC, DL, TOOL_CLEAN) com qty EXATA da base.
    base_tools_iter = (
        ToolsBase.objects
        .filter(discipline=disc, working_code=wkc)
        .only("id", "discipline", "working_code",
              "direct_labor", "qty_direct_labor", "special_tooling", "qty")
        .iterator(chunk_size=1000)
    )

    # Deduplicador por tripla usando NOME LIMPO para evitar variações por caracteres especiais
    seen: dict[Tuple[str, str, str], ToolsBase] = {}

    for b in base_tools_iter:
        raw_name = (b.special_tooling or "")
        name = _clean_tool_name(raw_name)
        if not name:
            # ignora itens sem nome válido após limpeza
            continue

        dl_key  = (b.direct_labor or "").strip().upper()
        if not dl_key or dl_key not in dl_present:
            # Só inclui se o DL existir na JC
            continue

        wkc_key = ((b.working_code or wkc).strip().upper())
        key = (wkc_key, dl_key, name.upper())

        if key not in seen:
            seen[key] = b
        else:
            # Opcional: preferir a linha mais recente da base
            # if b.id > seen[key].id:
            #     seen[key] = b
            pass

    new_tools: list[AllocatedTool] = []
    for b in seen.values():
        name = _clean_tool_name(b.special_tooling)
        qty_base = _dec2(getattr(b, "qty", None))  # EXATAMENTE a qty da base

        new_tools.append(AllocatedTool(
            jobcard_number   = jc,
            discipline       = _sx(disc, 100),
            working_code     = _sx((b.working_code or wkc), 50),
            direct_labor     = _sx((b.direct_labor or ""), 100),
            qty_direct_labor = _dec2(getattr(b, "qty_direct_labor", None)),  # metadado
            special_tooling  = _sx(name, 255),  # nome já normalizado (preserva 24")
            qty              = qty_base,
        ))

        if len(new_tools) >= 1000:
            AllocatedTool.objects.bulk_create(new_tools, batch_size=1000)
            report["tools"]["created"] += len(new_tools)
            new_tools.clear()

    if new_tools:
        AllocatedTool.objects.bulk_create(new_tools, batch_size=1000)
        report["tools"]["created"] += len(new_tools)

    # ======================= ENGINEERING =======================
    base_engs = (
        EngineeringBase.objects
        .filter(jobcard_number=jc)
        .only("jobcard_number", "discipline", "document", "rev", "status")
        .iterator(chunk_size=1000)
    )

    new_engs: list[AllocatedEngineering] = []
    for b in base_engs:
        doc = (b.document or "").strip()
        if not doc:
            continue
        new_engs.append(AllocatedEngineering(
            jobcard_number = jc,
            discipline     = _sx((getattr(b, "discipline", None) or disc), 50),
            document       = _sx(doc, 200),
            tag            = _sx((job.tag or ""), 50),
            rev            = _sx((getattr(b, "rev", "") or ""), 10),
            status         = _sx((getattr(b, "status", "") or ""), 50),
        ))

        if len(new_engs) >= 1000:
            AllocatedEngineering.objects.bulk_create(new_engs, batch_size=1000)
            report["engineering"]["created"] += len(new_engs)
            new_engs.clear()

    if new_engs:
        AllocatedEngineering.objects.bulk_create(new_engs, batch_size=1000)
        report["engineering"]["created"] += len(new_engs)

    # ======================= TASK DESCRIPTIONS =======================
    tasks_rep = _sync_task_descriptions_for_job(job)
    report["tasks"].update(tasks_rep)

    return report

# =========================================================
# Endpoints
# =========================================================

@require_POST
@login_required
@permission_required('jobcards.change_jobcard', raise_exception=True)
def jobcard_sync_allocations(request: HttpRequest, job_card_number: str):
    """Mirror M/T/E para UMA JobCard (≠ NO/NOT CHECKED) + sync da descrição das tasks."""
    job = get_object_or_404(
        JobCard.objects.only("job_card_number", "jobcard_status", "discipline", "working_code", "tag"),
        job_card_number=job_card_number
    )
    if not _is_eligible_status(job.jobcard_status):
        return JsonResponse(
            {'ok': False, 'error': 'JobCard status not eligible (must be different from NO CHECKED/NOT CHECKED).'},
            status=400
        )

    rep = _mirror_allocated_mte_for_job(job)

    def pad(sec: str) -> Dict[str, int]:
        d = rep.get(sec, {})
        return {
            "created":   int(d.get("created", 0)),
            "deleted":   int(d.get("deleted", 0)),
            "updated":   int(d.get("updated", 0)),
            "unchanged": int(d.get("unchanged", 0)),
        }

    return JsonResponse({
        'ok': True,
        'job_card_number': job_card_number,
        'report': {
            'materials':   pad('materials'),
            'tools':       pad('tools'),
            'engineering': pad('engineering'),
            'manpower':    {"created":0,"deleted":0,"updated":0,"unchanged":0},
            'tasks':       pad('tasks'),
        }
    })

@require_POST
@login_required
@permission_required('jobcards.change_jobcard', raise_exception=True)
def api_sync_allocations_all(request: HttpRequest):
    """
    Mirror M/T/E para TODAS as JobCards elegíveis.
    - .only(...) e .iterator(...) para escala.
    - Depois sincroniza a descrição das tasks.
    Query params opcionais:
      - limit: int  (limita quantas JobCards processar)
      - chunk: int  (tamanho do iterator chunk; default 1000)
    """
    try:
        limit = int(request.GET.get("limit", "0")) or None
    except ValueError:
        limit = None
    try:
        chunk = int(request.GET.get("chunk", "1000"))
        if chunk <= 0:
            chunk = 1000
    except ValueError:
        chunk = 1000

    qs = (
        JobCard.objects
        .exclude(jobcard_status__iexact="NO CHECKED")
        .exclude(jobcard_status__iexact="NOT CHECKED")
        .only("job_card_number", "jobcard_status", "discipline", "working_code", "tag")
        .order_by("id")
        .iterator(chunk_size=chunk)
    )

    processed = 0
    totals = {
        'materials':   {'deleted':0,'created':0,'updated':0},
        'tools':       {'deleted':0,'created':0,'updated':0},
        'engineering': {'deleted':0,'created':0,'updated':0},
        'manpower':    {'deleted':0,'created':0,'updated':0},
        'tasks':       {'deleted':0,'created':0,'updated':0},
    }

    for job in qs:
        if limit is not None and processed >= limit:
            break
        rep = _mirror_allocated_mte_for_job(job)
        processed += 1
        for sec in ('materials','tools','engineering','tasks'):
            totals[sec]['deleted'] += int(rep.get(sec, {}).get('deleted', 0))
            totals[sec]['created'] += int(rep.get(sec, {}).get('created', 0))
            totals[sec]['updated'] += int(rep.get(sec, {}).get('updated', 0))

    return JsonResponse({
        'ok': True,
        'processed': processed,
        'totals': totals,
        'note': 'Processed all eligible JobCards (including task description sync).'
    })
