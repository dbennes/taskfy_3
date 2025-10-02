# jobcards/views_dashboardWorkpack.py
from collections import defaultdict
from datetime import date
from pathlib import Path
from decimal import Decimal

from dateutil.relativedelta import relativedelta

from django.conf import settings
from django.shortcuts import render
from django.http import FileResponse, Http404
from django.views.decorators.http import require_GET
from django.core.exceptions import FieldError

from .models import (
    JobCard,
    AllocatedMaterial, AllocatedTool, AllocatedEngineering,
    AllocatedManpower, AllocatedTask,
)

# Ordem pedida nos cards
STATUS_ORDER = [
    "Cancelled",
    "No checked",
    "Preliminary Jobcard Checked",
    "Planning Jobcard Checked",
    "Offshore Field Jobcard Checked",
    "Completed",
]

def _norm(s: str) -> str:
    return (s or "").strip().lower()

def _status_bucket(s: str) -> str:
    s = _norm(s)
    if "cancel" in s: return "Cancelled"
    if "no" in s and "check" in s: return "No checked"
    if "prelim" in s: return "Preliminary Jobcard Checked"
    if "planning" in s: return "Planning Jobcard Checked"
    if "offshore" in s: return "Offshore Field Jobcard Checked"
    if "complete" in s: return "Completed"
    return "No checked"

def _month_ticks(n_months=12):
    """1º dia de cada mês (YYYY-MM-DD) - últimos n_months, incluindo o atual."""
    today = date.today().replace(day=1)
    months = [(today - relativedelta(months=i)) for i in range(n_months - 1, -1, -1)]
    return [m.isoformat() for m in months]

def _D(x) -> Decimal:
    if x is None: return Decimal("0")
    try: return Decimal(str(x).replace(",", "."))
    except Exception: return Decimal("0")

def _wc_label_map(used_codes):
    """
    Resolve a DESCRIÇÃO do Working Code:
      1) tenta model WorkingCode(code, description) se existir;
      2) tenta campos possíveis no AllocatedManpower;
      3) fallback: o próprio código.
    """
    labels = {}
    used_codes = {c for c in used_codes if c and c != "-"}
    if not used_codes:
        return labels

    # 1) WorkingCode (se existir)
    try:
        from .models import WorkingCode  # type: ignore
        for w in WorkingCode.objects.filter(code__in=used_codes).values("code", "description"):
            desc = (w.get("description") or "").strip()
            labels[w["code"]] = desc or w["code"]
    except Exception:
        pass

    # 2) Buscar em AllocatedManpower
    if not labels:
        for fname in ("working_code_description", "working_code_desc", "wc_description", "description"):
            try:
                qs = (AllocatedManpower.objects
                      .filter(working_code__in=used_codes)
                      .values("working_code", fname).distinct())
                tmp = {}
                for r in qs:
                    if r.get(fname):
                        tmp[r["working_code"]] = str(r[fname]).strip()
                if tmp:
                    labels.update(tmp)
                    break
            except FieldError:
                continue
            except Exception:
                continue
    return labels

def dashboard_workpack(request, wp_number=None):
    # -------------------------- Workpacks e seleção
    workpacks = list(
        JobCard.objects.exclude(workpack_number__isnull=True)
        .exclude(workpack_number__exact="")
        .values_list("workpack_number", flat=True)
        .distinct().order_by("workpack_number")
    )
    selected_wp = request.GET.get("wp") or wp_number or (workpacks[0] if workpacks else "")

    jcs_qs = JobCard.objects.filter(workpack_number=selected_wp).order_by("job_card_number")
    jobcard_numbers = list(jcs_qs.values_list("job_card_number", flat=True))

    # -------------------------- Contagens por status
    status_counts = defaultdict(int)
    for jc in jcs_qs:
        status_counts[_status_bucket(jc.jobcard_status)] += 1

    total_jobcards = len(jobcard_numbers)
    status_counts["No checked"] = 0  # regra

    # Cards superiores
    top_cards = []
    for label in STATUS_ORDER:
        cnt = status_counts.get(label, 0)
        pct = round((cnt / total_jobcards * 100), 1) if total_jobcards else 0
        top_cards.append({"label": label, "count": cnt, "pct": pct})

    # --- NOVO: dados do gráfico de barras por status (na mesma ordem dos cards)
    status_labels = STATUS_ORDER[:]  # mantém a ordem definida
    status_counts_list = [status_counts.get(lbl, 0) for lbl in status_labels]

    # -------------------------- Allocations
    # Materials
    materials_qs = (
        AllocatedMaterial.objects
        .filter(jobcard_number__in=jobcard_numbers)
        .order_by("jobcard_number", "pmto_code")
    )
    materials_map = defaultdict(list)
    materials_flat = []
    for m in materials_qs:
        rec = {
            "jobcard": m.jobcard_number,
            "pmto": m.pmto_code,
            "desc": m.description,
            "dim": getattr(m, "nps1", "") or "",
            "qty": m.qty,
            "notes": m.comments or "",
        }
        materials_map[m.jobcard_number].append(m)
        materials_flat.append(rec)

    # Tools
    tools_qs = (
        AllocatedTool.objects
        .filter(jobcard_number__in=jobcard_numbers)
        .order_by("jobcard_number", "working_code")
    )
    tools_map = defaultdict(list)
    for t in tools_qs:
        tools_map[t.jobcard_number].append(t)

    # Engineering (docs)
    docs_qs = (
        AllocatedEngineering.objects
        .filter(jobcard_number__in=jobcard_numbers)
        .order_by("jobcard_number", "document")
    )
    docs_map = defaultdict(list)
    for d in docs_qs:
        docs_map[d.jobcard_number].append(d)

    # -------------------------- Tasks & Manpower
    tasks_qs = AllocatedTask.objects.filter(jobcard_number__in=jobcard_numbers)

    task_desc_map = defaultdict(dict)
    for t in tasks_qs:
        task_desc_map[t.jobcard_number][t.task_order] = t.description or ""

    mp_qs = (
        AllocatedManpower.objects
        .filter(jobcard_number__in=jobcard_numbers)
        .order_by("jobcard_number", "task_order", "direct_labor")
    )

    # índice (jc, ordem) -> MPs
    mp_by_task = defaultdict(list)
    for p in mp_qs:
        mp_by_task[(p.jobcard_number, p.task_order)].append(p)

    # -------------------------- KPI HH (base: AllocatedManpower.hours)
    total_hh_dec = sum((_D(p.hours) for p in mp_qs), Decimal("0"))
    kpis = {
        "total_jobcards": total_jobcards,
        "with_materials": (
            AllocatedMaterial.objects
            .filter(jobcard_number__in=jobcard_numbers)
            .values("jobcard_number").distinct().count()
        ),
        "activity_ids_valid": (
            jcs_qs.exclude(activity_id__iregex=r"to\s*be\s*verified")
            .exclude(activity_id__isnull=True)
            .exclude(activity_id__exact="")
            .values("activity_id").distinct().count()
        ),
        "total_hh": float(total_hh_dec),
    }

    # -------------------------- Map p/ tabela por JC (expansiva)
    manpower_map = defaultdict(list)
    for p in mp_qs:
        desc = task_desc_map.get(p.jobcard_number, {}).get(p.task_order, "")
        manpower_map[p.jobcard_number].append({
            "working_code": p.working_code,
            "direct_labor": p.direct_labor,
            "qty": p.qty,
            "hours": p.hours,
            "task_order": p.task_order,
            "description": desc,
        })

    # -------------------------- Grid principal por JC (HH = soma MPs)
    jobcards_rows = []
    for idx, jc in enumerate(jcs_qs, start=1):
        jc_id = jc.job_card_number
        hh_total_dec = sum((_D(mp.get("hours")) for mp in manpower_map.get(jc_id, [])), Decimal("0"))

        materials_count = len(materials_map.get(jc_id, []))
        tools_count = len(tools_map.get(jc_id, []))
        manpower_count = len(manpower_map.get(jc_id, []))
        docs_count = len(docs_map.get(jc_id, []))
        has_alloc = any([materials_count, tools_count, manpower_count, docs_count])

        jobcards_rows.append({
            "idx": idx,
            "number": jc_id,
            "discipline": jc.discipline,
            "status": _status_bucket(jc.jobcard_status),
            "start": jc.start,
            "finish": jc.finish,
            "hh_total": float(hh_total_dec),
            "materials_count": materials_count,
            "tools_count": tools_count,
            "manpower_count": manpower_count,
            "docs_count": docs_count,
            "has_alloc": has_alloc,
        })

    # -------------------------- Manpower agregado (barra % cinza + horas)
    agg_map = defaultdict(lambda: {"hours_total": Decimal("0")})
    for p in mp_qs:
        key = p.direct_labor or "-"
        agg_map[key]["hours_total"] += _D(p.hours)

    tot_hours = sum(v["hours_total"] for v in agg_map.values()) or Decimal("0")

    manpower_agg = []
    for labor, v in sorted(agg_map.items(), key=lambda x: x[0].lower()):
        h = v["hours_total"]
        pct = (h / tot_hours * Decimal("100")) if tot_hours > 0 else Decimal("0")
        manpower_agg.append({
            "direct_labor": labor,
            "hours_total": float(h),
            "pct": float(pct),
            "pct_css": f"{float(pct):.1f}%",  # evita vírgula no CSS
        })
    manpower_totals = {"hours": float(tot_hours)}

    # -------------------------- Tasks by working code (WC descr. + task + Total MH)
    tasks_rows = []
    for t in tasks_qs.order_by("jobcard_number", "task_order"):
        jc_id = t.jobcard_number
        tord = t.task_order
        wcs = sorted({mp.working_code for mp in mp_by_task.get((jc_id, tord), []) if mp.working_code})
        working_code = wcs[0] if wcs else "-"
        alloc_h_dec = sum((_D(mp.hours) for mp in mp_by_task.get((jc_id, tord), [])), Decimal("0"))
        tasks_rows.append({
            "working_code": working_code,
            "task": t.description or "",
            "allocated_hours": float(alloc_h_dec),
        })

    agg_task_map = defaultdict(lambda: {"allocated_hours": Decimal("0")})
    for r in tasks_rows:
        key = (r["working_code"] or "-", (r["task"] or "-").strip())
        agg_task_map[key]["allocated_hours"] += _D(r["allocated_hours"])

    used_wc = {wc for (wc, _task) in agg_task_map.keys()}
    wc_label_map = _wc_label_map(used_wc)

    tasks_wc_agg = []
    total_alloc = Decimal("0")
    for (wc, task_name), vals in sorted(agg_task_map.items(), key=lambda x: (x[0][0], x[0][1])):
        label = wc_label_map.get(wc, wc) or "-"
        ah = vals["allocated_hours"]
        tasks_wc_agg.append({
            "working_code": label,  # mostra descrição (mantém título "Working code")
            "task": task_name,
            "allocated_hours": float(ah),
        })
        total_alloc += ah
    tasks_wc_totals = {"allocated_hours": float(total_alloc)}

    # -------------------------- Contexto
    context = {
        "workpacks": workpacks,
        "selected_wp": selected_wp,
        "total_workpacks": len(workpacks),

        "kpis": kpis,
        "top_cards": top_cards,

        # NOVO: gráfico de barras por status
        "status_labels": status_labels,
        "status_counts": status_counts_list,

        # tabelas
        "manpower_agg": manpower_agg,
        "manpower_totals": manpower_totals,
        "materials_flat": materials_flat,
        "tasks_wc": tasks_wc_agg,
        "tasks_wc_totals": tasks_wc_totals,

        # detalhe por JC
        "jobcards": jobcards_rows,
        "materials_map": dict(materials_map),
        "tools_map": dict(tools_map),
        "manpower_map": dict(manpower_map),
        "docs_map": dict(docs_map),
    }
    return render(request, "sistema/dashboard_workpack/dashboard_workpack.html", context)

@require_GET
def jobcard_pdf_view(request, jobcard_number: str):
    """Abre o PDF inline."""
    filename = f"{jobcard_number}.pdf"
    roots = [
        Path(getattr(settings, "JOBCARD_PDF_DIR", "")),
        Path(settings.MEDIA_ROOT) / "jobcards_pdfs",
        Path(settings.MEDIA_ROOT) / "jobcards" / "pdfs",
        Path(settings.MEDIA_ROOT) / "jobcards",
        Path(settings.MEDIA_ROOT),
    ]
    file_path = None
    for base in roots:
        if not base: continue
        p = base / filename
        if p.exists(): file_path = p; break
    if not file_path:
        for base in roots:
            if not base or not base.exists(): continue
            matches = list(base.glob(f"{jobcard_number}*.pdf"))
            if matches: file_path = matches[0]; break
    if not file_path or not file_path.exists():
        raise Http404("PDF não encontrado para esta JobCard. Gere o PDF primeiro.")
    resp = FileResponse(open(file_path, "rb"), content_type="application/pdf")
    resp["Content-Disposition"] = f'inline; filename="{file_path.name}"'
    return resp
