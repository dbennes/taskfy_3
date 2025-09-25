# jobcards/views_sync.py
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Dict, Set
from django.db import transaction
from django.http import JsonResponse, HttpRequest
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import get_object_or_404

from .models import (
    JobCard,
    ToolsBase, MaterialBase, EngineeringBase,
    AllocatedManpower, AllocatedTool, AllocatedMaterial, AllocatedEngineering,
)

# =========================================================
# Helpers (conversão numérica e truncamento)
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

# =========================================================
# Critério de elegibilidade por status
# Agora: processar TUDO que for diferente de "NO CHECKED" / "NOT CHECKED"
# =========================================================

_EXCLUDE_STATUSES: Set[str] = {"NO CHECKED", "NOT CHECKED"}

def _is_eligible_status(status: str | None) -> bool:
    """Elegível se status não for vazio e NÃO estiver na lista de exclusão (case-insensitive)."""
    s = (status or "").strip().upper()
    return bool(s) and s not in _EXCLUDE_STATUSES

# =========================================================
# Núcleo: espelho (mirror) de Materials / Tools / Engineering
# - NÃO toca em AllocatedManpower nem AllocatedTask
# - Apaga e recria M/T/E por JobCard
# - Tools: inclui somente se existir DL alocado correspondente
# - Tools.qty = qty da base (sem multiplicação)
# - Materials.pmto_code = project_code
# =========================================================

@transaction.atomic
def _mirror_allocated_mte_for_job(job: JobCard) -> Dict[str, Dict[str, int]]:
    """
    Espelha Bases → Allocated (apenas M/T/E) para UMA JobCard:
    - Apaga TUDO de AllocatedMaterial/AllocatedTool/AllocatedEngineering da JC e recria.
    - NÃO toca em AllocatedManpower nem AllocatedTask.
    - Tools: só inclui itens cujo direct_labor exista em AllocatedManpower da JC.
      (qty = qty da base)
    - Materials: pmto_code = project_code (apenas isso).
    """
    jc   = _sx(job.job_card_number, 100)
    disc = (job.discipline or "").strip()
    wkc  = (job.working_code or "").strip()

    report = {
        "materials":  {"deleted": 0, "created": 0},
        "tools":      {"deleted": 0, "created": 0},
        "engineering":{"deleted": 0, "created": 0},
    }

    # -------- Apaga tudo do Allocated (M/T/E) para esta JobCard --------
    m_qs = AllocatedMaterial.objects.filter(jobcard_number=jc)
    t_qs = AllocatedTool.objects.filter(jobcard_number=jc)
    e_qs = AllocatedEngineering.objects.filter(jobcard_number=jc)

    report["materials"]["deleted"]   = m_qs.count()
    report["tools"]["deleted"]       = t_qs.count()
    report["engineering"]["deleted"] = e_qs.count()

    m_qs.delete()
    t_qs.delete()
    e_qs.delete()

    # -------- DL presente (para filtrar Tools por DL) --------
    dl_present = {
        (dl or "").strip().upper()
        for dl, in AllocatedManpower.objects
                    .filter(jobcard_number=jc)
                    .values_list("direct_labor", flat=False)
    }

    # ======================= RECRIAR: MATERIALS =======================
    # (streaming: carrega somente colunas necessárias)
    base_mats = (
        MaterialBase.objects
        .filter(job_card_number=jc)
        .only("job_card_number", "discipline", "working_code",
              "project_code", "description", "qty", "jobcard_required_qty",
              "comments", "nps1")
        .iterator(chunk_size=1000)   # <-- leitura em streaming p/ bancos grandes
    )

    new_mats: list[AllocatedMaterial] = []
    for b in base_mats:
        pmto = _sx((b.project_code or "").strip(), 100)  # pmto_code = project_code

        new_mats.append(AllocatedMaterial(
            jobcard_number = jc,
            discipline     = _sx((getattr(b, "discipline", None) or disc), 50),
            working_code   = _sx((getattr(b, "working_code", None) or wkc), 50),
            pmto_code      = pmto,
            description    = (b.description or "").strip(),
            # qty da base; se vazio, cai para jobcard_required_qty
            qty            = _dec2(getattr(b, "qty", None) or getattr(b, "jobcard_required_qty", None)),
            comments       = (getattr(b, "comments", "") or ""),
            nps1           = _sx((getattr(b, "nps1", "") or ""), 50),
        ))

        # Flush por lote: evita crescer demais em RAM
        if len(new_mats) >= 1000:
            AllocatedMaterial.objects.bulk_create(new_mats, batch_size=1000)
            report["materials"]["created"] += len(new_mats)
            new_mats.clear()

    if new_mats:
        AllocatedMaterial.objects.bulk_create(new_mats, batch_size=1000)
        report["materials"]["created"] += len(new_mats)

    # ======================= RECRIAR: TOOLS =======================
    base_tools = (
        ToolsBase.objects
        .filter(discipline=disc, working_code=wkc)
        .only("discipline", "working_code", "direct_labor", "qty_direct_labor", "special_tooling", "qty")
        .iterator(chunk_size=1000)
    )

    new_tools: list[AllocatedTool] = []
    for b in base_tools:
        name = (b.special_tooling or "").strip()
        if not name:
            continue

        dl_key = (b.direct_labor or "").strip().upper()
        if not dl_key or dl_key not in dl_present:
            continue  # respeita regra: só cria tool se existir DL alocado

        qty_base = _dec2(getattr(b, "qty", None))  # SEMPRE qty da base

        new_tools.append(AllocatedTool(
            jobcard_number   = jc,
            discipline       = _sx(disc, 100),
            working_code     = _sx(wkc, 50),
            direct_labor     = _sx((b.direct_labor or ""), 100),
            qty_direct_labor = _dec2(getattr(b, "qty_direct_labor", None)),  # armazenado como metadado
            special_tooling  = _sx(name, 255),
            qty              = qty_base,
        ))

        if len(new_tools) >= 1000:
            AllocatedTool.objects.bulk_create(new_tools, batch_size=1000)
            report["tools"]["created"] += len(new_tools)
            new_tools.clear()

    if new_tools:
        AllocatedTool.objects.bulk_create(new_tools, batch_size=1000)
        report["tools"]["created"] += len(new_tools)

    # ======================= RECRIAR: ENGINEERING =======================
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

    return report

# =========================================================
# Endpoints
# =========================================================

@require_POST
@login_required
@permission_required('jobcards.change_jobcard', raise_exception=True)
def jobcard_sync_allocations(request: HttpRequest, job_card_number: str):
    """
    Mirror M/T/E para UMA JobCard específica.
    Critério: status elegível = diferente de "NO CHECKED"/"NOT CHECKED".
    """
    job = get_object_or_404(
        JobCard.objects.only("job_card_number", "jobcard_status", "discipline", "working_code", "tag"),
        job_card_number=job_card_number
    )
    if not _is_eligible_status(job.jobcard_status):
        return JsonResponse({'ok': False, 'error': 'JobCard status not eligible (must be different from NO CHECKED/NOT CHECKED).'}, status=400)

    rep = _mirror_allocated_mte_for_job(job)

    def pad(sec: str) -> Dict[str, int]:
        d = rep.get(sec, {})
        return {"created": int(d.get("created", 0)), "deleted": int(d.get("deleted", 0)), "updated": 0, "unchanged": 0}

    return JsonResponse({
        'ok': True,
        'job_card_number': job_card_number,
        'report': {
            'materials':   pad('materials'),
            'tools':       pad('tools'),
            'engineering': pad('engineering'),
            'manpower':    {"created":0,"deleted":0,"updated":0,"unchanged":0},
            'tasks':       {"created":0,"deleted":0,"updated":0,"unchanged":0},
        }
    })

@require_POST
@login_required
@permission_required('jobcards.change_jobcard', raise_exception=True)
def api_sync_allocations_all(request: HttpRequest):
    """
    Mirror M/T/E para TODAS as JobCards com status elegível (≠ NO/NOT CHECKED).
    Escalável para bancos grandes:
      - Só carrega colunas necessárias via .only(...)
      - Itera com .iterator(chunk_size=...)
      - Transação por JobCard (rápida)
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
        if chunk <= 0: chunk = 1000
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
        'materials':   {'deleted':0,'created':0},
        'tools':       {'deleted':0,'created':0},
        'engineering': {'deleted':0,'created':0},
        'manpower':    {'deleted':0,'created':0},
        'tasks':       {'deleted':0,'created':0},
    }

    for job in qs:
        if limit is not None and processed >= limit:
            break
        rep = _mirror_allocated_mte_for_job(job)
        processed += 1
        for sec in ('materials','tools','engineering'):
            totals[sec]['deleted'] += int(rep.get(sec, {}).get('deleted', 0))
            totals[sec]['created'] += int(rep.get(sec, {}).get('created', 0))

    return JsonResponse({'ok': True, 'processed': processed, 'totals': totals, 'note': 'Processed all eligible JobCards.'})
