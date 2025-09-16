# views.py
from __future__ import annotations

import re
from typing import Dict, Optional

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render

from .models import DocumentoControle, EngineeringBase


# =========================
# Helpers
# =========================

_CODE_RE = re.compile(r"[^A-Z0-9_\-\/\.]")  # mantém letras, números, _, -, / e .

def normalize_code(s: str) -> str:
    """
    Normaliza o código para casar EngineeringBase.document com DocumentoControle.codigo.
    - Uppercase; remove espaços
    - Remove extensão comum (PDF/DWG/DOC/DOCX/XLS/XLSX)
    - Remove caracteres estranhos
    """
    if not s:
        return ""
    s = s.strip().upper().replace(" ", "")
    s = re.sub(r"\.(PDF|DWG|DOCX?|XLSX?)$", "", s, flags=re.IGNORECASE)
    s = _CODE_RE.sub("", s)
    return s


def rev_letter_color(rev: str) -> str:
    """
    Cor do ponto pela letra da revisão (puramente visual).
    """
    if not rev:
        return "#9aa3b2"  # cinza
    r = rev.strip().upper()
    if r.startswith("C"):
        return "#1f9d55"  # verde (AFC)
    if r.startswith("A"):
        return "#b58900"  # âmbar (IN APPROVAL)
    if r.startswith("R"):
        return "#6b5bd9"  # roxo (IN REVIEW)
    return "#23272e"


def map_rev_to_status(rev: str) -> str:
    """
    Mapeia a letra da revisão para o status em inglês:
      - Rxx -> IN REVIEW
      - Axx -> IN APPROVAL
      - Cxx -> AFC
      - caso contrário -> string vazia (não sobrepõe)
    """
    if not rev:
        return ""
    r = rev.strip().upper()
    if r.startswith("R"):
        return "IN REVIEW"
    if r.startswith("A"):
        return "IN APPROVAL"
    if r.startswith("C"):
        return "AFC"
    return ""


def find_doc_ctrl_for_document(eng_document: str) -> Optional[DocumentoControle]:
    """
    Localiza o DocumentoControle correspondente ao EngineeringBase.document.
    1) Igualdade direta (case-insensitive).
    2) Fallback por normalização do código.
    """
    if not eng_document:
        return None

    dc = (
        DocumentoControle.objects
        .filter(codigo__iexact=eng_document)
        .order_by("-atualizado_em")
        .first()
    )
    if dc:
        return dc

    key = normalize_code(eng_document)
    for cand in DocumentoControle.objects.only("id", "codigo", "revisao", "atualizado_em").order_by("-atualizado_em"):
        if normalize_code(cand.codigo) == key:
            return cand
    return None


# =========================
# Views
# =========================

@login_required(login_url="login")
def docs_revision_review(request):
    """
    Lista somente documentos em que EngineeringBase.rev difere de DocumentoControle.revisao.
    Filtros:
      - search: busca em jobcard_number, document, discipline
      - project: filtra DocumentoControle.nome_projeto
      - items_per_page: 5,10,20,50,100,100000
    """
    search = (request.GET.get("search") or "").strip()
    project = (request.GET.get("project") or "").strip()

    PAGE_SIZE_OPTIONS = [5, 10, 20, 50, 100, 100000]
    try:
        per_page = int(request.GET.get("items_per_page") or 10)
    except Exception:
        per_page = 10
    if per_page not in PAGE_SIZE_OPTIONS:
        per_page = 10

    # Base de engenharia
    eng_qs = EngineeringBase.objects.all().only(
        "id", "jobcard_number", "discipline", "document", "rev", "status"
    )
    if search:
        eng_qs = eng_qs.filter(
            Q(document__icontains=search) |
            Q(jobcard_number__icontains=search) |
            Q(discipline__icontains=search)
        )

    # DocumentoControle (opcionalmente filtrado por projeto)
    ctrl_qs = DocumentoControle.objects.all().only(
        "id", "codigo", "revisao", "status_documento", "nome_projeto"
    )
    if project:
        ctrl_qs = ctrl_qs.filter(nome_projeto__icontains=project)

    # Index por código normalizado para casamento O(1)
    ctrl_map: Dict[str, DocumentoControle] = {
        normalize_code(dc.codigo): dc for dc in ctrl_qs
    }

    # Monta linhas com mismatch de revisão
    rows = []
    for eng in eng_qs:
        key = normalize_code(eng.document)
        dc = ctrl_map.get(key)
        if not dc:
            continue  # não encontrou no controle
        eng_rev = (eng.rev or "").strip().upper()
        dc_rev = (dc.revisao or "").strip().upper()
        if not dc_rev:
            continue  # sem revisão no controle
        if eng_rev != dc_rev:  # inclui apenas quando difere
            rows.append({
                "eng": eng,
                "jobcard_number": eng.jobcard_number,
                "document": eng.document,
                "eng_rev": eng_rev or "—",
                "dc_rev": dc_rev,
                "dc_status": (dc.status_documento or ""),
                "dc_color": rev_letter_color(dc_rev),
                "eng_color": rev_letter_color(eng_rev),
                "dc_id": dc.id,
                # opcional: status alvo caso aceite
                "target_status": map_rev_to_status(dc_rev),
            })

    # Paginação
    paginator = Paginator(rows, per_page)
    page_obj = paginator.get_page(request.GET.get("page"))

    context = {
        "rows": page_obj,                   # objeto de página para o template
        "total_mismatch": len(rows),
        "search": search,
        "project": project,
        "items_per_page": per_page,         # int (para selected)
        "page_size_options": PAGE_SIZE_OPTIONS,
    }
    return render(request, "sistema/doc_revision/docs_revision_review.html", context)


@login_required(login_url="login")
@transaction.atomic
def accept_doc_revision(request, eng_id: int):
    """
    Aceita a revisão do DocumentoControle para um EngineeringBase específico.
    - Atualiza eng.rev = dc.revisao
    - Atualiza eng.status = IN REVIEW / IN APPROVAL / AFC conforme a letra da revisão
    """
    if request.method != "POST":
        return redirect("docs_revision_review")

    eng = get_object_or_404(EngineeringBase, id=eng_id)
    dc = find_doc_ctrl_for_document(eng.document)

    if not dc or not (dc.revisao or "").strip():
        messages.error(request, f"Document control not found or without valid revision for '{eng.document}'.")
        return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))

    new_rev = dc.revisao.strip().upper()
    current_rev = (eng.rev or "").strip().upper()

    # Define status com base na letra da revisão
    new_status = map_rev_to_status(new_rev)

    if current_rev == new_rev and (eng.status or "") == new_status:
        messages.info(request, f"'{eng.document}' is already on revision {new_rev}.")
        return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))

    eng.rev = new_rev
    update_fields = ["rev"]

    # Aplica o novo status somente se mapeado
    if new_status:
        eng.status = new_status
        update_fields.append("status")

    eng.save(update_fields=update_fields)
    messages.success(request, f"'{eng.document}' updated to revision {new_rev} ({new_status or 'status unchanged'}).")
    return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))


@login_required(login_url="login")
@transaction.atomic
def accept_doc_revision_bulk(request):
    """
    Aceita em lote (checkbox) as revisões novas do DocumentoControle para vários EngineeringBase.
    - Atualiza rev e status usando o mesmo mapeamento por letra de revisão.
    """
    if request.method != "POST":
        return redirect("docs_revision_review")

    ids = request.POST.getlist("eng_ids")
    if not ids:
        messages.warning(request, "Select at least one document.")
        return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))

    eng_list = list(EngineeringBase.objects.filter(id__in=ids))

    # Mapa de controle por código normalizado (1 passada)
    ctrl_map: Dict[str, DocumentoControle] = {
        normalize_code(dc.codigo): dc
        for dc in DocumentoControle.objects.only("codigo", "revisao", "atualizado_em")
    }

    updated = 0
    for eng in eng_list:
        key = normalize_code(eng.document)
        dc = ctrl_map.get(key)
        if not dc or not (dc.revisao or "").strip():
            continue

        new_rev = dc.revisao.strip().upper()
        current_rev = (eng.rev or "").strip().upper()
        if new_rev == current_rev:
            # mesmo número de revisão; ainda assim podemos ajustar status se desejar:
            new_status_same = map_rev_to_status(new_rev)
            if new_status_same and (eng.status or "") != new_status_same:
                eng.status = new_status_same
                eng.save(update_fields=["status"])
                updated += 1
            continue

        # Status baseado na letra
        new_status = map_rev_to_status(new_rev)

        eng.rev = new_rev
        update_fields = ["rev"]
        if new_status:
            eng.status = new_status
            update_fields.append("status")

        eng.save(update_fields=update_fields)
        updated += 1

    messages.success(request, f"{updated} document(s) updated successfully.")
    return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))
