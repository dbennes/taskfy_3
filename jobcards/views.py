from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login as auth_login
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Count
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.utils import timezone
from django.db import transaction
from collections import defaultdict
from datetime import datetime
from decimal import Decimal
import os
import re
import pdfkit
import barcode
from barcode.writer import ImageWriter
from io import BytesIO
from django.views.generic import ListView, CreateView
from django.urls import reverse_lazy
from .models import Discipline, Area, WorkingCode, System
from .forms import DisciplineForm, AreaForm, WorkingCodeForm, SystemForm, ImpedimentsForm
import datetime
from django.conf import settings
from .models import (
    JobCard, TaskBase, ManpowerBase, MaterialBase, ToolsBase, EngineeringBase,
    AllocatedEngineering, AllocatedManpower, AllocatedMaterial, AllocatedTool, AllocatedTask,
    Discipline, Area, WorkingCode, System, Impediments, PMTOBase, MRBase, ProcurementBase
)
import tempfile
from django.db.models import Sum
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from .models import MaterialBase, JobCard
import pandas as pd
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST
from datetime import datetime
from datetime import date
import io
from jobcards.models import DocumentoRevisaoAlterada, DocumentoControle

from django.shortcuts import render, get_object_or_404, redirect
from django.db import transaction
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
import re
from collections import defaultdict
from .models import (
    JobCard, TaskBase, ManpowerBase, AllocatedManpower, AllocatedTask,
    MaterialBase, AllocatedMaterial, ToolsBase, AllocatedTool,
    EngineeringBase, AllocatedEngineering
)

from django.shortcuts import render, get_object_or_404, redirect
from django.db import transaction
from django.db.models import Sum
from django.contrib.auth.decorators import login_required
from collections import defaultdict
import re
from .models import JobCard, TaskBase, ManpowerBase, AllocatedManpower, AllocatedTask, MaterialBase, AllocatedMaterial, ToolsBase, AllocatedTool, EngineeringBase, AllocatedEngineering





# Caminho absoluto do executável dentro do projeto
path_wkhtmltopdf = os.path.join(settings.BASE_DIR, 'wkhtmltopdf', 'bin', 'wkhtmltopdf.exe')
config = pdfkit.configuration(wkhtmltopdf=path_wkhtmltopdf)

# - PARTE DA INDEX DO SISTEMA
def index(request):
    return render(request, 'index.html')

# - PARTE DO LOGIN DO SISTEMA
def login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)

        if user is not None:
            auth_login(request, user)
            return redirect('dashboard')  # redireciona para a index
        else:
            return render(request, 'login.html', {'erro': 'Login Inválido'})

    # Se não for POST, retorna a página de login normalmente
    return render(request, 'login.html')

# - PARTE DO DASHBOARD


def dashboard(request):
    # Summary cards
    total_jobcards = JobCard.objects.count()
    checked_count = JobCard.objects.exclude(jobcard_status='NO CHECKED').count()
    not_checked_count = total_jobcards - checked_count

    # JobCards with Material (jobcards únicos presentes na base de material)
    jobcards_with_material = (
        MaterialBase.objects
        .exclude(job_card_number__isnull=True)
        .exclude(job_card_number__exact='')
        .values('job_card_number')
        .distinct()
        .count()
    )

    # Gráfico: JobCards por Disciplina (usando discipline_code)
    # Pega todos os códigos de disciplina distintos e ordena
    codigos = list(JobCard.objects.values_list('discipline_code', flat=True).distinct().order_by('discipline_code'))
    labels_total = codigos
    data_total = [
        JobCard.objects.filter(discipline_code=cod).count()
        for cod in codigos
    ]

    # Charts para não checkeds
    not_checked_qs = (
        JobCard.objects
        .filter(jobcard_status='NO CHECKED')
        .values('discipline')
        .annotate(count=Count('id'))
        .order_by('discipline')
    )
    labels_not_checked = [entry['discipline'] for entry in not_checked_qs]
    data_not_checked   = [entry['count']      for entry in not_checked_qs]

    # AWP Monitor: System > WorkPack > JobCards
    awp_data = defaultdict(lambda: defaultdict(list))
    for jc in JobCard.objects.all().order_by('system', 'workpack_number', 'job_card_number'):
        if jc.system and jc.workpack_number:
            awp_data[jc.system][jc.workpack_number].append(jc)

    # ALERTA: JobCards com campos obrigatórios vazios/nulos
    jobcards_incompletos = JobCard.objects.filter(
        Q(job_card_number__isnull=True) | Q(job_card_number__exact='') |
        Q(prepared_by__isnull=True) | Q(prepared_by__exact='') |
        Q(discipline__isnull=True) | Q(discipline__exact='') |
        Q(job_card_description__isnull=True) | Q(job_card_description__exact='') |
        Q(date_prepared__isnull=True)
    )
    alerta_count = jobcards_incompletos.count()
    
    # Gráfico JobCards por Área (location)
    area_qs = (
        JobCard.objects
        .values('location')
        .annotate(count=Count('id'))
        .order_by('location')
    )
    labels_areas = [entry['location'] or '—' for entry in area_qs]
    data_areas   = [entry['count'] for entry in area_qs]

    level_xx_count = JobCard.objects.exclude(level__iexact='XX').count()
    activity_to_be_verified_count = JobCard.objects.exclude(activity_id__iexact='to be verified').count()
    start_1900_count = JobCard.objects.exclude(start=date(1900, 1, 1)).count()
    finish_1900_count = JobCard.objects.exclude(finish=date(1900, 1, 1)).count()
    system_to_be_verified_count = JobCard.objects.exclude(system__iexact='to be verified').count()
    subsystem_to_be_verified_count = JobCard.objects.exclude(subsystem__iexact='to be verified').count()
    preliminary_checked_count = JobCard.objects.filter(jobcard_status='PRELIMINARY JOBCARD CHECKED').count()
    planning_checked_count = JobCard.objects.filter(jobcard_status='PLANNING JOBCARD CHECKED').count()
    offshore_checked_count = JobCard.objects.filter(jobcard_status='OFFSHORE FIELD JOBCARD CHECKED').count()
    approved_to_execute_count = JobCard.objects.filter(jobcard_status='APPROVED TO EXECUTE').count()
    finalized_count = JobCard.objects.filter(jobcard_status='JOBCARD FINALIZED').count()
    
    # Pega todos os pares únicos (code, name)
    discipline_legend = (
        JobCard.objects
        .values_list('discipline_code', 'discipline')
        .distinct()
        .order_by('discipline_code')
    )
    
    # Encontra todos os documentos da EngineeringBase que também estão no DocumentoControle
    engineering_synced_docs = EngineeringBase.objects.filter(
        document__in=DocumentoControle.objects.values_list('codigo', flat=True)
    )

    context = {
        'total_jobcards': total_jobcards,
        'not_checked_count': not_checked_count,
        'checked_count': checked_count,
        'jobcards_with_material': jobcards_with_material,
        'labels_not_checked': labels_not_checked,
        'data_not_checked': data_not_checked,
        'labels_total': labels_total,    # códigos das disciplinas
        'data_total': data_total,        # valores por código
        'awp_data': awp_data,
        'jobcards_incompletos': jobcards_incompletos,
        'alerta_count': alerta_count,
        'labels_areas': labels_areas,
        'data_areas': data_areas,
        'level_xx_count': level_xx_count,
        'activity_to_be_verified_count': activity_to_be_verified_count,
        'start_1900_count': start_1900_count,
        'finish_1900_count': finish_1900_count,
        'system_to_be_verified_count': system_to_be_verified_count,
        'subsystem_to_be_verified_count': subsystem_to_be_verified_count,
        'preliminary_checked_count': preliminary_checked_count,
        'planning_checked_count': planning_checked_count,
        'offshore_checked_count': offshore_checked_count,
        'approved_to_execute_count': approved_to_execute_count,
        'finalized_count': finalized_count,
        'discipline_legend': discipline_legend,
        'engineering_synced_docs': engineering_synced_docs,
        'preliminary_percent': f"{(preliminary_checked_count/total_jobcards*100):.2f}" if total_jobcards else "0.00",
    'planning_percent': f"{(planning_checked_count/total_jobcards*100):.2f}" if total_jobcards else "0.00",
    'offshore_percent': f"{(offshore_checked_count/total_jobcards*100):.2f}" if total_jobcards else "0.00",
    'approved_percent': f"{(approved_to_execute_count/total_jobcards*100):.2f}" if total_jobcards else "0.00",
        
    }
    return render(request, 'sistema/dashboard.html', context)


@login_required(login_url='login')
def jobcards_list(request):  
    qs = JobCard.objects.all()

    search = request.GET.get('search', '')
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    items_per_page = request.GET.get('items_per_page', '10')

    if search:
        qs = qs.filter(
            Q(discipline__icontains=search) |
            Q(job_card_number__icontains=search) |
            Q(prepared_by__icontains=search)
        )

    if start_date:
        start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
        qs = qs.filter(start__gte=start_date_obj)

    if end_date:
        end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
        qs = qs.filter(start__lte=end_date_obj)

    # Verifica items_per_page, define padrão 10 se inválido
    try:
        items_per_page = int(items_per_page)
    except (ValueError, TypeError):
        items_per_page = 10

    paginator = Paginator(qs, items_per_page)

    page = request.GET.get('page')
    try:
        jobcards_page = paginator.page(page)
    except PageNotAnInteger:
        jobcards_page = paginator.page(1)
    except EmptyPage:
        jobcards_page = paginator.page(paginator.num_pages)
        
    backups_dir = os.path.join(settings.BASE_DIR, 'jobcard_backups')
    available_pdfs = {f for f in os.listdir(backups_dir) if f.endswith('.pdf')}

    context = {
        'jobcards': jobcards_page,
        'search': search,
        'start_date': start_date,
        'end_date': end_date,
        'items_per_page': items_per_page,
        'paginator': paginator,
        'available_pdfs': available_pdfs,
    }
    return render(request, 'sistema/jobcards.html', context)

# - PARTE DO DASHBOARD
@login_required(login_url='login') # EXIGE O USUARIO A ESTAR LOGADO
def create_jobcard(request, jobcard_id=None):
    return render(request, 'sistema/create_jobcard.html')


@login_required(login_url='login')
def edit_jobcard(request, jobcard_id=None):
    job = get_object_or_404(JobCard, job_card_number=jobcard_id) if jobcard_id else None

    if request.method == 'POST' and job:
        job.jobcard_status = request.POST.get('JOBCARD_STATUS', job.jobcard_status)
        job.discipline = request.POST.get('DISCIPLINE', job.discipline)
        job.discipline_code = request.POST.get('DISCIPLINE_CODE', job.discipline_code)
        job.location = request.POST.get('LOCATION', job.location)
        job.level = request.POST.get('LEVEL', job.level)
        job.activity_id = request.POST.get('ACTIVITY_ID', job.activity_id)
        job.system = request.POST.get('SYSTEM', job.system)
        job.subsystem = request.POST.get('SUBSYSTEM', job.subsystem)
        job.workpack_number = request.POST.get('WORKPACK_NUMBER', job.workpack_number)
        job.start = request.POST.get('START') or None
        job.finish = request.POST.get('FINISH') or None
        job.working_code_description = request.POST.get('WORKING_CODE_DESCRIPTION', job.working_code_description)
        job.tag = request.POST.get('TAG', job.tag)
        job.job_card_description = request.POST.get('JOB_CARD_DESCRIPTION', job.job_card_description)
        job.comments = request.POST.get('COMMENTS', job.comments)
        job.total_weight = request.POST.get('TOTAL_WEIGHT', job.total_weight)
        job.unit = request.POST.get('UNIT', job.unit)
        job.indice_kpi = request.POST.get('INDICE_KPI', job.indice_kpi)
        job.prepared_by = request.POST.get('PREPARED_BY', job.prepared_by)
        job.date_prepared = request.POST.get('DATE_PREPARED') or None
        job.approved_br = request.POST.get('APPROVED_BR', job.approved_br)
        job.date_approved = request.POST.get('DATE_APPROVED') or None
        job.hot_work_required = request.POST.get('HOT_WORK_REQUIRED', job.hot_work_required)

        job.rev = '1'

        job.last_modified_by = request.user.username
        job.save()

        def safe_float(s):
            return float(s.replace('%', '').replace(',', '.')) if s and s.strip() else 0.0

        mp_pattern = re.compile(r'^mp-(\d+)-(\d+)-qty$')  # task_order, manpower_id

        with transaction.atomic():
            AllocatedManpower.objects.filter(jobcard_number=job.job_card_number).delete()
            AllocatedTask.objects.filter(jobcard_number=job.job_card_number).delete()
            AllocatedMaterial.objects.filter(jobcard_number=job.job_card_number).delete()
            AllocatedTool.objects.filter(jobcard_number=job.job_card_number).delete()
            AllocatedEngineering.objects.filter(jobcard_number=job.job_card_number).delete()

            task_list = TaskBase.objects.filter(working_code=job.working_code).order_by('order')
            task_orders = [str(task.order) for task in task_list]  # Lista com todos os task.order (string)

            not_applicable_tasks = set()
            for key in request.POST.keys():
                if key.startswith('task-not-applicable-'):
                    task_order = key.replace('task-not-applicable-', '')
                    not_applicable_tasks.add(task_order)

            # Salva manpowers
            for key, val in request.POST.items():
                match = mp_pattern.match(key)
                if not match:
                    continue

                task_order, mp_id = match.group(1), int(match.group(2))
                if task_order in not_applicable_tasks:
                    continue

                qty = safe_float(val)
                hh_key = f"mp-{task_order}-{mp_id}-hh"
                hours = safe_float(request.POST.get(hh_key, ''))

                if qty == 0.0 and hours == 0.0:
                    continue

                mp = ManpowerBase.objects.filter(pk=mp_id).first()
                if not mp:
                    continue  # ignora os ids que foram apagados
                
                AllocatedManpower.objects.create(
                    jobcard_number=job.job_card_number,
                    discipline=mp.discipline,
                    working_code=mp.working_code,
                    direct_labor=mp.direct_labor,
                    qty=qty,
                    hours=hours,
                    task_order=int(task_order),  # task_order é o próprio order da task
                )

            # Salva tarefas alocadas
            for task in task_list:
                max_hh = request.POST.get(f"hh-max-{task.order}", '0')
                total_hh = request.POST.get(f"hh-total-{task.order}", '0')
                percent = request.POST.get(f"hh-percent-{task.order}", '0')

                not_applicable = request.POST.get(f"task-not-applicable-{task.order}") == 'on'

                AllocatedTask.objects.create(
                    jobcard_number=job.job_card_number,
                    task_order=task.order,
                    description=task.typical_task,
                    max_hours=safe_float(max_hh),
                    total_hours=safe_float(total_hh),
                    percent=safe_float(percent),
                    not_applicable=not_applicable,
                )

            # Salva materiais alocados
            project_codes = request.POST.getlist('project_code[]')
            descriptions = request.POST.getlist('description[]')
            jobcard_required_qtys = request.POST.getlist('jobcard_required_qty[]')
            comments = request.POST.getlist('comments[]')
            nps1_list = request.POST.getlist('nps1[]')

            for code, desc, qty, comment, nps1 in zip(project_codes, descriptions, jobcard_required_qtys, comments, nps1_list):
                AllocatedMaterial.objects.create(
                    jobcard_number=job.job_card_number,
                    discipline=job.discipline,
                    working_code=job.working_code,
                    pmto_code=code,
                    description=desc,
                    qty=float(qty.replace(',', '.')) if qty else 0.0,
                    comments=comment,
                    nps1=nps1
                )

            # Salva ferramentas alocadas
            tool_items = request.POST.getlist('tool_item[]')
            tool_disciplines = request.POST.getlist('tool_discipline[]')
            tool_working_codes = request.POST.getlist('tool_working_code[]')
            tool_direct_labors = request.POST.getlist('tool_direct_labor[]')
            tool_qty_direct_labors = request.POST.getlist('tool_qty_direct_labor[]')
            tool_special_toolings = request.POST.getlist('tool_special_tooling[]')
            tool_qtys = request.POST.getlist('tool_qty[]')

            for item, discipline, working_code, direct_labor, qty_dl, special_tooling, qty in zip(
                tool_items, tool_disciplines, tool_working_codes, tool_direct_labors,
                tool_qty_direct_labors, tool_special_toolings, tool_qtys
            ):
                AllocatedTool.objects.create(
                    jobcard_number=job.job_card_number,
                    discipline=discipline,
                    working_code=working_code,
                    direct_labor=direct_labor,
                    qty_direct_labor=float(qty_dl.replace(',', '.')) if qty_dl else 0.0,
                    special_tooling=special_tooling,
                    qty=float(qty.replace(',', '.')) if qty else 0.0
                )

            # Salva documentos de engenharia
            eng_disciplines = request.POST.getlist('eng_discipline[]')
            eng_documents = request.POST.getlist('eng_document[]')
            eng_tags = request.POST.getlist('eng_tag[]')
            eng_revs = request.POST.getlist('eng_rev[]')
            eng_statuses = request.POST.getlist('eng_status[]')

            for discipline, document, tag, rev, status in zip(eng_disciplines, eng_documents, eng_tags, eng_revs, eng_statuses):
                AllocatedEngineering.objects.create(
                    jobcard_number=job.job_card_number,
                    discipline=discipline,
                    document=document,
                    tag=tag,
                    rev=rev,
                    status=status,
                )

        total_duration_hs = AllocatedTask.objects.filter(jobcard_number=job.job_card_number).aggregate(total=Sum('max_hours'))['total'] or 0
        total_man_hours = AllocatedTask.objects.filter(jobcard_number=job.job_card_number).aggregate(total=Sum('total_hours'))['total'] or 0

        job.total_duration_hs = f'{total_duration_hs:.2f}'
        job.total_man_hours = f'{total_man_hours:.2f}'
        job.rev = '1'
        job.save(update_fields=['total_duration_hs', 'total_man_hours', 'rev'])

        return redirect('generate_pdf', jobcard_id=job.job_card_number)

    # --- GET ---
    disciplinas = JobCard.objects.values_list('discipline', flat=True).distinct().order_by('discipline')
    discipline_codes = JobCard.objects.values_list('discipline_code', flat=True).distinct().order_by('discipline_code')
    locations = JobCard.objects.values_list('location', flat=True).distinct().order_by('location')
    levels = JobCard.objects.values_list('level', flat=True).distinct().order_by('level')
    activity_ids = JobCard.objects.values_list('activity_id', flat=True).distinct().order_by('activity_id')
    systems = JobCard.objects.values_list('system', flat=True).distinct().order_by('system')
    subsystems = JobCard.objects.values_list('subsystem', flat=True).distinct().order_by('subsystem')
    workpacks = JobCard.objects.values_list('workpack_number', flat=True).distinct().order_by('workpack_number')

    task_list = TaskBase.objects.filter(working_code=job.working_code).order_by('order') if job else []
    manpowers = ManpowerBase.objects.filter(working_code__in=[t.working_code for t in task_list])
    manpowers_dict = defaultdict(list)
    for mp in manpowers:
        manpowers_dict[mp.working_code].append(mp)

    materials_list = MaterialBase.objects.filter(job_card_number=job.job_card_number) if job else []
    tools_list = ToolsBase.objects.filter(working_code=job.working_code) if job else []
    engineering_list = EngineeringBase.objects.filter(jobcard_number=job.job_card_number) if job else []

    all_manpowers = ManpowerBase.objects.all().order_by('direct_labor', 'id')
    unique_manpowers = {}
    for mp in all_manpowers:
        if mp.direct_labor not in unique_manpowers:
            unique_manpowers[mp.direct_labor] = mp

    allocated_tasks_qs = AllocatedTask.objects.filter(jobcard_number=job.job_card_number)
    allocated_tasks_dict = {t.task_order: t for t in allocated_tasks_qs}

    allocated_manpowers_qs = AllocatedManpower.objects.filter(jobcard_number=job.job_card_number)
    allocated_manpowers_dict = defaultdict(list)
    for mp in allocated_manpowers_qs:
        allocated_manpowers_dict[mp.task_order].append(mp)

    def manpower_list_for_task(task):
        return allocated_manpowers_dict.get(task.order) or manpowers_dict.get(task.working_code, [])

    context = {
        'job': job,
        'disciplinas': disciplinas,
        'discipline_codes': discipline_codes,
        'locations': locations,
        'levels': levels,
        'activity_ids': activity_ids,
        'systems': systems,
        'subsystems': subsystems,
        'workpacks': workpacks,
        'task_list': task_list,
        'manpowers_dict': manpowers_dict,
        'all_manpowers': ManpowerBase.objects.all(),
        'materials_list': materials_list,
        'tools_list': tools_list,
        'engineering_list': engineering_list,
        'unique_manpowers': unique_manpowers.values(),
        'allocated_tasks_dict': allocated_tasks_dict,
        'allocated_manpowers_dict': allocated_manpowers_dict,
        'manpower_list_for_task': manpower_list_for_task,
    }

    return render(request, 'sistema/create_jobcard.html', context)

def allocate_resources(request, jobcard_id):
    job = get_object_or_404(JobCard, job_card_number=jobcard_id)

    # Alocar Manpower
    for mp in ManpowerBase.objects.filter(working_code=job.working_code):
        AllocatedManpower.objects.update_or_create(
            jobcard_number=job.job_card_number,
            manpower_name=mp.manpower_name,
            defaults={
                'working_code': mp.working_code,
                'qty': mp.qty,
                'description': mp.description,
            }
        )

    # Alocar Materials
    for mat in MaterialBase.objects.filter(job_card_number=job.job_card_number):
        AllocatedMaterial.objects.update_or_create(
            jobcard_number=job.job_card_number,
            item=mat.item,
            defaults={
                'working_code': mat.working_code,
                'discipline': mat.discipline,
                'description': mat.description,
                'qty': mat.qty,
                'unit': mat.unit,
            }
        )

    # Alocar Tools
    for tool in ToolsBase.objects.filter(working_code=job.working_code):
        AllocatedTool.objects.update_or_create(
            jobcard_number=job.job_card_number,
            item=tool.item,
            defaults={
                'working_code': tool.working_code,
                'special_tooling': tool.special_tooling,
                'qty': tool.qty,
            }
        )

    return redirect('generate_pdf', jobcard_id=job.job_card_number)

@login_required(login_url='login')
def generate_pdf(request, jobcard_id):
    job = get_object_or_404(JobCard, job_card_number=jobcard_id)

    # Gerar código de barras
    barcode_folder = os.path.join(settings.BASE_DIR, 'static', 'barcodes')
    os.makedirs(barcode_folder, exist_ok=True)

    barcode_filename = f'{job.job_card_number}.png'
    barcode_path = os.path.join(barcode_folder, barcode_filename)

    if not os.path.exists(barcode_path):
        CODE128 = barcode.get_barcode_class('code128')
        code128 = CODE128(job.job_card_number, writer=ImageWriter())
        code128.write(open(barcode_path, 'wb'), options={'write_text': False})

    barcode_url = f'file:///{barcode_path.replace("\\", "/")}'

    if job.jobcard_status != 'PRELIMINARY JOBCARD CHECKED':
        job.jobcard_status = 'PRELIMINARY JOBCARD CHECKED'
        job.save(update_fields=['jobcard_status'])

    allocated_manpowers = AllocatedManpower.objects.filter(jobcard_number=jobcard_id)
    allocated_materials = AllocatedMaterial.objects.filter(jobcard_number=job.job_card_number)
    allocated_tools = AllocatedTool.objects.filter(jobcard_number=jobcard_id)
    allocated_tasks = AllocatedTask.objects.filter(jobcard_number=jobcard_id).order_by('task_order')
    allocated_engineerings = AllocatedEngineering.objects.filter(jobcard_number=job.job_card_number)

    image_path = os.path.join(settings.BASE_DIR, 'static', 'assets', 'img', '3.jpg')
    image_url = f'file:///{image_path.replace("\\", "/")}'

    half = len(allocated_tools) // 2
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
    }

    html_string = render_to_string('sistema/jobcard_pdf.html', context, request=request)

    # Renderizar header e footer com contexto
    header_html_string = render_to_string('sistema/header.html', context, request=request)
    footer_html_string = render_to_string('sistema/footer.html', context, request=request)

    # Criar arquivos temporários
    header_temp = tempfile.NamedTemporaryFile(delete=False, suffix='.html')
    footer_temp = tempfile.NamedTemporaryFile(delete=False, suffix='.html')

    header_temp.write(header_html_string.encode('utf-8'))
    footer_temp.write(footer_html_string.encode('utf-8'))

    header_temp.close()
    footer_temp.close()

    pdf_file = pdfkit.from_string(
        html_string,
        False,
        configuration=config,
        options={
            'enable-local-file-access': '',
            'margin-top': '35mm',
            'margin-bottom': '30mm',
            'header-html': f'file:///{header_temp.name.replace("\\", "/")}',
            'footer-html': f'file:///{footer_temp.name.replace("\\", "/")}',
            'header-spacing': '5',
            'footer-spacing': '5',
        }
    )

    # Backup versionado
    backup_filename = f'JobCard_{jobcard_id}_Rev_{job.rev}.pdf'
    backups_dir = os.path.join(settings.BASE_DIR, 'jobcard_backups')
    os.makedirs(backups_dir, exist_ok=True)

    backup_path = os.path.join(backups_dir, backup_filename)
    with open(backup_path, 'wb') as f:
        f.write(pdf_file)

    # Limpar arquivos temporários
    os.unlink(header_temp.name)
    os.unlink(footer_temp.name)

    # Resposta para download
    response = HttpResponse(pdf_file, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename=JobCard_{jobcard_id}_Rev_{job.rev}.pdf'
    return response


# --------- DATABASE EXIBIÇÕES --------------- #

@login_required(login_url='login')
def jobcards_overview(request):
    jobcards = JobCard.objects.all().order_by('-date_prepared')

    # Filtros simples (opcional)
    search_number = request.GET.get('search_number', '')
    search_discipline = request.GET.get('search_discipline', '')
    search_prepared_by = request.GET.get('search_prepared_by', '')

    if search_number:
        jobcards = jobcards.filter(job_card_number__icontains=search_number)

    if search_discipline:
        jobcards = jobcards.filter(discipline__icontains=search_discipline)

    if search_prepared_by:
        jobcards = jobcards.filter(prepared_by__icontains=search_prepared_by)

    context = {
        'jobcards': jobcards,
    }
    return render(request, 'sistema/databases/jobcards_overview.html', context)

@login_required(login_url='login')
def materials_list(request):
    materials = MaterialBase.objects.all()

    context = {
        'materials': materials
    }

    return render(request, 'sistema/databases/materials_list.html', context)

@login_required(login_url='login')
def manpower_list(request):
    manpowers = ManpowerBase.objects.all()
    context = {
        'manpowers': manpowers
    }
    return render(request, 'sistema/databases/manpower_list.html', context)

@login_required(login_url='login')
def tools_list(request):
    tools = ToolsBase.objects.all()
    context = {
        'tools': tools
    }
    return render(request, 'sistema/databases/tools_list.html', context)

@login_required(login_url='login')
def engineering_list(request):
    engineering = EngineeringBase.objects.all()
    context = {
        'engineering': engineering
    }
    return render(request, 'sistema/databases/engineering_list.html', context)

@login_required(login_url='login')
def task_list(request):
    tasks = TaskBase.objects.all()
    # Cria um dicionário: código → descrição
    code_to_desc = {wc.code.upper(): wc.description for wc in WorkingCode.objects.all()}
    context = {
        'tasks': tasks,
        'code_to_desc': code_to_desc
    }
    return render(request, 'sistema/databases/task_list.html', context)

# --------- DATABASE ALOCAÇÕES --------------- #

@login_required(login_url='login')
def allocated_manpower_list(request):
    allocated_manpower = AllocatedManpower.objects.all()
    context = {
        'allocated_manpower': allocated_manpower
    }
    return render(request, 'sistema/allocated/allocated_manpower_list.html', context)

@login_required(login_url='login')
def allocated_material_list(request):
    allocated_materials = AllocatedMaterial.objects.all()
    context = {
        'allocated_materials': allocated_materials
    }
    return render(request, 'sistema/allocated/allocated_material_list.html', context)

@login_required(login_url='login')
def allocated_tool_list(request):
    allocated_tools = AllocatedTool.objects.all()
    context = {
        'allocated_tools': allocated_tools
    }
    return render(request, 'sistema/allocated/allocated_tool_list.html', context)

@login_required(login_url='login')
def allocated_engineering_list(request):
    allocated_engineering = AllocatedEngineering.objects.all()
    context = {
        'allocated_engineering': allocated_engineering
    }
    return render(request, 'sistema/allocated/allocated_engineering_list.html', context)

@login_required(login_url='login')
def allocated_task_list(request):
    allocated_tasks = AllocatedTask.objects.all()
    context = {
        'allocated_tasks': allocated_tasks
    }
    return render(request, 'sistema/allocated/allocated_task_list.html', context)

# --------- IMPORTAÇÕES BANCOS --------------- #

@csrf_exempt
def import_materials(request):
    if request.method == "POST":
        overwrite = request.POST.get('overwrite') == '1'
        file = request.FILES.get('file')
        if not file:
            return JsonResponse({'status': 'error', 'message': 'No file uploaded.'})

        # Lê o arquivo (csv ou excel)
        try:
            if file.name.endswith('.csv'):
                df = pd.read_csv(file)
            else:
                df = pd.read_excel(file)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f'Could not read file: {str(e)}'})

        # Lista das colunas obrigatórias (atualizadas!)
        required_columns = [
            'job_card_number', 'working_code', 'discipline', 'tag_jobcard_base',
            'jobcard_required_qty', 'unit_req_qty', 'weight_kg', 'material_segmentation',
            'comments', 'sequenc_no_procurement', 'status_procurement', 'mr_number',
            'basic_material', 'description', 'project_code', 'nps1', 'qty', 'unit', 'po',
            'reference_documents'
        ]
        missing = [col for col in required_columns if col not in df.columns]
        if missing:
            return JsonResponse({'status': 'error', 'message': f"Missing columns: {', '.join(missing)}"})

        # Padroniza os jobcards da planilha
        df['job_card_number'] = df['job_card_number'].astype(str).str.strip().str.upper()
        jobcards_in_file = df['job_card_number'].unique()
        errors = []
        # Valida existência de todos os jobcards antes de qualquer alteração
        for jc in jobcards_in_file:
            if not JobCard.objects.filter(job_card_number__iexact=jc).exists():
                errors.append(f"Job Card '{jc}' does not exist.")

        if errors:
            return JsonResponse({'status': 'error', 'message': " | ".join(errors)})

        # NOVA VALIDAÇÃO: cada job_card_number só pode ter 1 working_code e 1 discipline
        for jc in jobcards_in_file:
            working_codes = df[df['job_card_number'].str.upper() == jc.upper()]['working_code'].astype(str).str.upper().unique()
            disciplines = df[df['job_card_number'].str.upper() == jc.upper()]['discipline'].astype(str).str.upper().unique()
            if len(working_codes) > 1:
                return JsonResponse({'status': 'error', 'message': f"Job Card '{jc}' has more than one Working Code in the file: {', '.join(working_codes)}."})
            if len(disciplines) > 1:
                return JsonResponse({'status': 'error', 'message': f"Job Card '{jc}' has more than one Discipline in the file: {', '.join(disciplines)}."})

        # Confirma duplicidade para qualquer jobcard
        materials_exist = any(
            MaterialBase.objects.filter(job_card_number__iexact=jc).exists()
            for jc in jobcards_in_file
        )
        if materials_exist and not overwrite:
            return JsonResponse({'status': 'duplicate', 'message': 'Materials already registered for one or more Job Cards in your file. Overwrite?'})

        # Se overwrite, apaga antes de importar os novos
        if overwrite:
            for jc in jobcards_in_file:
                MaterialBase.objects.filter(job_card_number__iexact=jc).delete()

        # Insere todos os materiais de todas as jobcards válidas
        for idx, row in df.iterrows():
            try:
                jc = str(row['job_card_number']).strip().upper()
                MaterialBase.objects.create(
                    job_card_number = jc,
                    working_code = str(row.get('working_code', '')).strip().upper(),
                    discipline = str(row.get('discipline', '')).strip().upper(),
                    tag_jobcard_base = str(row.get('tag_jobcard_base', '')).strip().upper(),
                    jobcard_required_qty = float(row.get('jobcard_required_qty', 0)) if row.get('jobcard_required_qty') not in [None, ''] else None,
                    unit_req_qty = str(row.get('unit_req_qty', '')).strip().upper(),
                    weight_kg = float(row.get('weight_kg', 0)) if row.get('weight_kg') not in [None, ''] else None,
                    material_segmentation = str(row.get('material_segmentation', '')).strip().upper(),
                    comments = str(row.get('comments', '')).strip(),
                    sequenc_no_procurement = str(row.get('sequenc_no_procurement', '')).strip().upper(),
                    status_procurement = str(row.get('status_procurement', '')).strip().upper(),
                    mr_number = str(row.get('mr_number', '')).strip().upper(),
                    basic_material = str(row.get('basic_material', '')).strip().upper(),
                    description = str(row.get('description', '')).strip().upper(),
                    project_code = str(row.get('project_code', '')).strip().upper(),
                    nps1 = str(row.get('nps1', '')).strip().upper(),
                    qty = float(row.get('qty', 0)) if row.get('qty') not in [None, ''] else None,
                    unit = str(row.get('unit', '')).strip().upper(),
                    po = str(row.get('po', '')).strip().upper(),
                    reference_documents = str(row.get('reference_documents', '')).strip()
                )
            except Exception as e:
                return JsonResponse({
                    'status': 'error',
                    'message': f"Error on row {idx+2}: {str(e)}"
                })

        return JsonResponse({'status': 'ok'})
    return JsonResponse({'status': 'error', 'message': 'Invalid request.'})

@login_required
def import_jobcard(request):
    if request.method == "POST":
        overwrite = request.POST.get('overwrite') == '1'
        file = request.FILES.get('file')
        if not file:
            return JsonResponse({'status': 'error', 'message': 'No file uploaded.'})

        try:
            if file.name.endswith('.csv'):
                df = pd.read_csv(file)
            else:
                df = pd.read_excel(file)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f'Could not read file: {str(e)}'})

        required_fields = [
            "item",
            "seq_number",
            "discipline",
            "discipline_code",
            "location",
            "level",
            "activity_id",
            "start",
            "finish",
            "system",
            "subsystem",
            "workpack_number",
            "working_code",
            "tag",
            "working_code_description",
            "job_card_number",
            "job_card_description",
            "total_weight",
            "unit",
            "total_duration_hs",
            "indice_kpi",
            "total_man_hours",
            "comments",
            "hot_work_required",  # <- Agora faz parte dos required_fields!
        ]

        file_fields = list(df.columns)
        missing = [f for f in required_fields if f not in file_fields]
        extra = [f for f in file_fields if f not in required_fields]
        if missing:
            return JsonResponse({'status': 'error', 'message': f"Missing columns: {', '.join(missing)}"})
        if extra:
            return JsonResponse({'status': 'error', 'message': f"Extra/unexpected columns: {', '.join(extra)}"})

        empty_fields = []
        for field in required_fields:
            if df[field].isnull().any() or (df[field] == '').any():
                empty_fields.append(field)
        if empty_fields:
            return JsonResponse({'status': 'error', 'message': f"Please fill all required fields: {', '.join(empty_fields)}"})

        for _, row in df.iterrows():
            # ----------- Validação do formato do Job Card Number -----------
            job_card_number = str(row['job_card_number']).strip()
            pattern = r"^[A-Z0-9]{3}\.[A-Z0-9]{2}-[A-Z0-9]{2}-\d{4}$"
            if not re.match(pattern, job_card_number):
                return JsonResponse({
                    'status': 'error',
                    'message': f"Job Card Number '{job_card_number}' is invalid. The expected format is: A09.PS-EL-0001"
                })

            # --- Validação do campo hot_work_required ---
            hot_work_value = str(row.get('hot_work_required', '')).strip().capitalize()
            if hot_work_value not in ['Yes', 'No']:
                return JsonResponse({
                    'status': 'error',
                    'message': f"Invalid value for Hot Work Required in JobCard '{job_card_number}'. Only 'Yes' or 'No' are allowed."
                })

            jobcard_exist = JobCard.objects.filter(job_card_number=job_card_number).exists()

            # --- Converte campos de data, se necessário ---
            for date_field in ["start", "finish"]:
                if isinstance(row[date_field], str) and row[date_field]:
                    try:
                        row[date_field] = pd.to_datetime(row[date_field]).date()
                    except Exception:
                        return JsonResponse({'status': 'error', 'message': f"Invalid date format in {date_field} for Job Card '{job_card_number}'"})

            if jobcard_exist:
                if not overwrite:
                    return JsonResponse({
                        'status': 'duplicate',
                        'message': f"JobCard {job_card_number} already exists. Do you want to update this JobCard?"
                    })
                else:
                    # Atualiza, mas não mexe em rev!
                    jobcard = JobCard.objects.get(job_card_number=job_card_number)
                    for field in required_fields:
                        if field == 'hot_work_required':
                            setattr(jobcard, field, hot_work_value)
                        else:
                            setattr(jobcard, field, row[field])
                    jobcard.last_modified_by = request.user.username
                    jobcard.last_modified_at = timezone.now()
                    jobcard.save()
            else:
                # Cria nova JobCard normalmente
                data = {field: row[field] for field in required_fields}
                data["rev"] = "0"
                data["hot_work_required"] = hot_work_value
                data["jobcard_status"] = "NO CHECKED"
                data["completed"] = "NO"
                data["prepared_by"] = request.user.username
                data["date_prepared"] = timezone.now()
                data["approved_br"] = ""
                data["date_approved"] = None
                data["status"] = "NO"
                data["last_modified_by"] = request.user.username
                data["last_modified_at"] = timezone.now()
                data["offshore_field_check"] = "NO"
                jobcard = JobCard.objects.create(**data)

        return JsonResponse({'status': 'ok'})
    return JsonResponse({'status': 'error', 'message': 'Invalid request.'})

@login_required
def import_manpower(request):
    if request.method == "POST":
        file = request.FILES.get('file')
        if not file:
            return JsonResponse({'status': 'error', 'message': 'No file uploaded.'})

        try:
            if file.name.endswith('.csv'):
                df = pd.read_csv(file)
            else:
                df = pd.read_excel(file)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f'Could not read file: {str(e)}'})

        required_fields = [
            "item",
            "discipline",
            "working_code",
            "working_description",
            "direct_labor",
            "qty"
        ]

        file_fields = list(df.columns)
        missing = [f for f in required_fields if f not in file_fields]
        extra = [f for f in file_fields if f not in required_fields]
        if missing:
            return JsonResponse({'status': 'error', 'message': f"Missing columns: {', '.join(missing)}"})
        if extra:
            return JsonResponse({'status': 'error', 'message': f"Extra/unexpected columns: {', '.join(extra)}"})

        empty_fields = []
        for field in required_fields:
            if df[field].isnull().any() or (df[field] == '').any():
                empty_fields.append(field)
        if empty_fields:
            return JsonResponse({'status': 'error', 'message': f"Please fill all required fields: {', '.join(empty_fields)}"})

        # Descobrir todos os pares discipline+working_code do arquivo, sempre em maiúsculo
        discipline_codes = set(
            (str(row["discipline"]).strip().upper(), str(row["working_code"]).strip().upper())
            for _, row in df.iterrows()
        )

        # Apagar todos os registros existentes para esses pares, usando sempre upper
        for discipline, working_code in discipline_codes:
            ManpowerBase.objects.filter(
                discipline=discipline,
                working_code=working_code
            ).delete()

        # Checar unicidade dentro do arquivo e criar registros em CAPS LOCK
        seen = set()
        for _, row in df.iterrows():
            discipline = str(row["discipline"]).strip().upper()
            working_code = str(row["working_code"]).strip().upper()
            direct_labor = str(row["direct_labor"]).strip().upper()
            working_description = str(row["working_description"]).strip().upper()
            key = (discipline, working_code, direct_labor)
            if key in seen:
                return JsonResponse({'status': 'error', 'message': f"Duplicated direct_labor '{direct_labor}' for working_code '{working_code}' and discipline '{discipline}' in the file."})
            seen.add(key)

            # working_code deve existir (sempre upper)
            if not WorkingCode.objects.filter(code=working_code).exists():
                return JsonResponse({
                    'status': 'error',
                    'message': f"Working code '{working_code}' is not registered in the WorkingCode base. Only registered codes are allowed."
                })

            ManpowerBase.objects.create(
                item=row["item"],
                discipline=discipline,
                working_code=working_code,
                working_description=working_description,
                direct_labor=direct_labor,
                qty=row["qty"]
            )

        return JsonResponse({'status': 'ok'})
    return JsonResponse({'status': 'error', 'message': 'Invalid request.'})

@login_required
def import_toolsbase(request):
    if request.method == "POST":
        file = request.FILES.get('file')
        if not file:
            return JsonResponse({'status': 'error', 'message': 'No file uploaded.'})

        try:
            if file.name.endswith('.csv'):
                df = pd.read_csv(file)
            else:
                df = pd.read_excel(file)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f'Could not read file: {str(e)}'})

        required_fields = [
            "item",
            "discipline",
            "working_code",
            "direct_labor",
            "qty_direct_labor",
            "special_tooling",
            "qty"
        ]

        file_fields = list(df.columns)
        missing = [f for f in required_fields if f not in file_fields]
        extra = [f for f in file_fields if f not in required_fields]
        if missing:
            return JsonResponse({'status': 'error', 'message': f"Missing columns: {', '.join(missing)}"})
        if extra:
            return JsonResponse({'status': 'error', 'message': f"Extra/unexpected columns: {', '.join(extra)}"})

        empty_fields = []
        for field in required_fields:
            if df[field].isnull().any() or (df[field].astype(str).str.strip() == '').any():
                empty_fields.append(field)
        if empty_fields:
            return JsonResponse({'status': 'error', 'message': f"Please fill all required fields: {', '.join(empty_fields)}"})

        # Descobrir todos os pares discipline+working_code do arquivo
        discipline_codes = set(
            (str(row["discipline"]).strip().lower(), str(row["working_code"]).strip().lower())
            for _, row in df.iterrows()
        )

        # Apagar todos os registros existentes para esses pares
        for discipline, working_code in discipline_codes:
            ToolsBase.objects.filter(
                discipline__iexact=discipline,
                working_code__iexact=working_code
            ).delete()

        # Criar os novos registros (garante unicidade no arquivo também)
        seen = set()
        for _, row in df.iterrows():
            discipline = str(row["discipline"]).strip().upper()
            working_code = str(row["working_code"]).strip().upper()
            direct_labor = str(row["direct_labor"]).strip().upper()
            special_tooling = str(row["special_tooling"]).strip().upper()

            # Checa unicidade dentro do próprio arquivo (opcional, mas recomendado)
            key = (discipline, working_code, direct_labor, special_tooling)
            if key in seen:
                return JsonResponse({'status': 'error', 'message': f"Duplicated tool for direct labor '{direct_labor}', special tooling '{special_tooling}' in file."})
            seen.add(key)

            # working_code deve existir
            if not WorkingCode.objects.filter(code__iexact=working_code).exists():
                return JsonResponse({
                    'status': 'error',
                    'message': f"Working code '{row['working_code']}' is not registered in the WorkingCode base. Only registered codes are allowed."
                })

            ToolsBase.objects.create(
                item=int(row["item"]),
                discipline=discipline,
                working_code=working_code,
                direct_labor=direct_labor,
                qty_direct_labor=float(row["qty_direct_labor"]),
                special_tooling=special_tooling,
                qty=float(row["qty"])
            )

        return JsonResponse({'status': 'ok'})
    return JsonResponse({'status': 'error', 'message': 'Invalid request.'})

@login_required
def import_engineering(request):
    if request.method == "POST":
        overwrite = request.POST.get("overwrite") == "1"
        file = request.FILES.get('file')
        if not file:
            return JsonResponse({'status': 'error', 'message': 'No file uploaded.'})

        try:
            if file.name.endswith('.csv'):
                df = pd.read_csv(file)
            else:
                df = pd.read_excel(file)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f'Could not read file: {str(e)}'})

        required_fields = ["item", "discipline", "document", "jobcard_number", "rev", "status"]
        missing = [f for f in required_fields if f not in df.columns]
        extra = [f for f in df.columns if f not in required_fields]
        if missing:
            return JsonResponse({'status': 'error', 'message': f"Missing columns: {', '.join(missing)}"})
        if extra:
            return JsonResponse({'status': 'error', 'message': f"Extra/unexpected columns: {', '.join(extra)}"})

        # Verificar duplicatas por jobcard_number
        jobcards_in_file = df['jobcard_number'].unique().tolist()
        duplicates = EngineeringBase.objects.filter(jobcard_number__in=jobcards_in_file).exists()

        if duplicates and not overwrite:
            return JsonResponse({
                'status': 'duplicate',
                'message': 'Some jobcards already exist in the system. Do you want to overwrite them?'
            })

        if overwrite:
            EngineeringBase.objects.filter(jobcard_number__in=jobcards_in_file).delete()

        for _, row in df.iterrows():
            EngineeringBase.objects.create(
                item=row["item"],
                discipline=row["discipline"].strip(),
                document=row["document"].strip(),
                jobcard_number=row["jobcard_number"].strip(),
                rev=str(row["rev"]).strip(),
                status=row["status"].strip()
            )

        return JsonResponse({'status': 'ok'})
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method.'})

@login_required
def import_taskbase(request):
    if request.method == "POST":
        file = request.FILES.get('file')
        if not file:
            return JsonResponse({'status': 'error', 'message': 'No file uploaded.'})

        try:
            if file.name.endswith('.csv'):
                df = pd.read_csv(file)
            else:
                df = pd.read_excel(file)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f'Could not read file: {str(e)}'})

        required_fields = [
            "item",
            "discipline",
            "working_code",
            "typical_task",
            "order"
        ]

        file_fields = list(df.columns)
        missing = [f for f in required_fields if f not in file_fields]
        extra = [f for f in file_fields if f not in required_fields]
        if missing:
            return JsonResponse({'status': 'error', 'message': f"Missing columns: {', '.join(missing)}"})
        if extra:
            return JsonResponse({'status': 'error', 'message': f"Extra/unexpected columns: {', '.join(extra)}"})

        empty_fields = []
        for field in required_fields:
            if df[field].isnull().any() or (df[field].astype(str).str.strip() == '').any():
                empty_fields.append(field)
        if empty_fields:
            return JsonResponse({'status': 'error', 'message': f"Please fill all required fields: {', '.join(empty_fields)}"})

        # Descobrir todos os pares discipline+working_code do arquivo
        discipline_codes = set(
            (str(row["discipline"]).strip().upper(), str(row["working_code"]).strip().upper())
            for _, row in df.iterrows()
        )

        # Apagar todos os registros existentes para esses pares
        for discipline, working_code in discipline_codes:
            TaskBase.objects.filter(
                discipline__iexact=discipline,
                working_code__iexact=working_code
            ).delete()

        # Criar os novos registros
        for _, row in df.iterrows():
            TaskBase.objects.create(
                item=int(row["item"]),
                discipline=str(row["discipline"]).strip().upper(),
                working_code=str(row["working_code"]).strip().upper(),
                typical_task=str(row["typical_task"]).strip().upper(),
                order=int(row["order"])
            )

        return JsonResponse({'status': 'ok'})
    return JsonResponse({'status': 'error', 'message': 'Invalid request.'})

#REFERENCES FUNÇÕES 

class DisciplineListView(ListView):
    model = Discipline
    template_name = 'sistema/references/discipline_list.html'
    context_object_name = 'disciplines'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = DisciplineForm()
        return context

    def post(self, request, *args, **kwargs):
        form = DisciplineForm(request.POST)
        if form.is_valid():
            form.save()
        return redirect('disciplines_list')

class AreaListView(ListView):
    model = Area
    template_name = 'sistema/references/area_list.html'
    context_object_name = 'areas'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = AreaForm()
        return context

    def post(self, request, *args, **kwargs):
        form = AreaForm(request.POST)
        if form.is_valid():
            form.save()
        return redirect('areas_list')

class WorkingCodeListView(ListView):
    model = WorkingCode
    template_name = 'sistema/references/workingcode_list.html'
    context_object_name = 'workingcodes'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = WorkingCodeForm()
        return context

    def post(self, request, *args, **kwargs):
        form = WorkingCodeForm(request.POST)
        if form.is_valid():
            form.save()
        return redirect('workingcodes_list')

class SystemListView(ListView):
    model = System
    template_name = 'sistema/references/system_list.html'
    context_object_name = 'systems'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = SystemForm()
        return context

    def post(self, request, *args, **kwargs):
        form = SystemForm(request.POST)
        if form.is_valid():
            form.save()
        return redirect('systems_list')
    
    # Discipline Delete
    
def delete_discipline(request, pk):
    discipline = get_object_or_404(Discipline, pk=pk)
    discipline.delete()
    return redirect('disciplines_list')  # Nome da URL que lista Disciplines

# --------- DELETAR DADOS -------------- #

# System Delete
def delete_system(request, pk):
    system = get_object_or_404(System, pk=pk)
    system.delete()
    return redirect('systems_list')  # Nome da URL que lista Systems

# Working Code Delete
def delete_working_code(request, pk):
    working_code = get_object_or_404(WorkingCode, pk=pk)
    working_code.delete()
    return redirect('workingcodes_list')  # Nome da URL que lista Working Codes

# Area Delete
def delete_area(request, pk):
    area = get_object_or_404(Area, pk=pk)
    area.delete()
    return redirect('areas_list')  # Nome da URL que lista Areas


# --------- BAIXAR EXPORTAÇÕES --------- #

@login_required
def export_materials_excel(request):
    # CAPTURA OS FILTROS ENVIADOS PELO FRONT
    material = request.GET.get('material', '')
    status = request.GET.get('status', '')
    project_code = request.GET.get('project_code', '')
    global_search = request.GET.get('search', '')

    # INICIA A QUERY
    qs = MaterialBase.objects.all()

    # FILTROS POR CAMPO INDIVIDUAL
    if material:
        qs = qs.filter(material_segmentation__icontains=material)
    if status:
        qs = qs.filter(status_procurement__icontains=status)
    if project_code:
        qs = qs.filter(project_code__icontains=project_code)

    # FILTRO GLOBAL (BUSCA EM VÁRIOS CAMPOS)
    if global_search:
        qs = qs.filter(
            Q(item__icontains=global_search) |
            Q(job_card_number__icontains=global_search) |
            Q(working_code__icontains=global_search) |
            Q(discipline__icontains=global_search) |
            Q(tag_jobcard_base__icontains=global_search) |
            Q(material_segmentation__icontains=global_search) |
            Q(project_code__icontains=global_search) |
            Q(description__icontains=global_search) |
            Q(unit_req_qty__icontains=global_search) |
            Q(weight_kg__icontains=global_search) |
            Q(comments__icontains=global_search) |
            Q(status_procurement__icontains=global_search)
            # Adicione outros campos que queira filtrar no global_search!
        )

    # MONTA O DATAFRAME COM OS CAMPOS QUE QUER EXPORTAR (já com MR Number e Reference Documents!)
    data = qs.values(
        'item',
        'job_card_number',
        'working_code',
        'discipline',
        'tag_jobcard_base',
        'jobcard_required_qty',
        'unit_req_qty',
        'weight_kg',
        'material_segmentation',
        'comments',
        'sequenc_no_procurement',
        'status_procurement',
        'mr_number',               # <-- NOVO CAMPO
        'basic_material',
        'description',
        'project_code',
        'nps1',
        'qty',
        'unit',
        'po',
        'reference_documents'      # <-- NOVO CAMPO
    )

    df = pd.DataFrame(list(data))

    # FORMATAÇÃO NUMÉRICA: duas casas, vírgula
    for col in ['jobcard_required_qty', 'weight_kg', 'qty']:
        if col in df.columns:
            df[col] = df[col].apply(lambda x: '{:.2f}'.format(x).replace('.', ',') if pd.notnull(x) else '')

    # GERA O EXCEL PARA DOWNLOAD
    response = HttpResponse(content_type='application/vnd.ms-excel')
    response['Content-Disposition'] = 'attachment; filename=materials.xlsx'
    df.to_excel(response, index=False)
    return response

@login_required
def export_manpower_excel (request):
    discipline = request.GET.get('discipline', '')
    working_code = request.GET.get('working_code', '')
    direct_labor = request.GET.get('direct_labor', '')
    global_search = request.GET.get('search', '')

    qs = ManpowerBase.objects.all()

    if discipline:
        qs = qs.filter(discipline__icontains=discipline)
    if working_code:
        qs = qs.filter(working_code__icontains=working_code)
    if direct_labor:
        qs = qs.filter(direct_labor__icontains=direct_labor)
    if global_search:
        qs = qs.filter(
            Q(discipline__icontains=global_search) |
            Q(working_code__icontains=global_search) |
            Q(working_description__icontains=global_search) |
            Q(direct_labor__icontains=global_search)
        )

    data = qs.values(
        'item',
        'discipline',
        'working_code',
        'working_description',
        'direct_labor',
        'qty'
    )

    df = pd.DataFrame(list(data))

    # Formatação de qty com 2 casas
    if 'qty' in df.columns:
        df['qty'] = df['qty'].apply(lambda x: '{:.2f}'.format(x) if pd.notnull(x) else '')

    response = HttpResponse(content_type='application/vnd.ms-excel')
    response['Content-Disposition'] = 'attachment; filename=manpower_base_export.xlsx'
    df.to_excel(response, index=False)
    return response

@login_required
def export_toolsbase_excel(request):
    discipline = request.GET.get('discipline', '')
    working_code = request.GET.get('working_code', '')
    direct_labor = request.GET.get('direct_labor', '')
    global_search = request.GET.get('search', '')

    qs = ToolsBase.objects.all()

    if discipline:
        qs = qs.filter(discipline__icontains=discipline)
    if working_code:
        qs = qs.filter(working_code__icontains=working_code)
    if direct_labor:
        qs = qs.filter(direct_labor__icontains=direct_labor)
    if global_search:
        qs = qs.filter(
            Q(discipline__icontains=global_search) |
            Q(working_code__icontains=global_search) |
            Q(direct_labor__icontains=global_search) |
            Q(special_tooling__icontains=global_search)
        )

    data = qs.values(
        'item',
        'discipline',
        'working_code',
        'direct_labor',
        'qty_direct_labor',
        'special_tooling',
        'qty'
    )

    df = pd.DataFrame(list(data))

    # Formatação de qty com 2 casas decimais
    for col in ['qty_direct_labor', 'qty']:
        if col in df.columns:
            df[col] = df[col].apply(lambda x: '{:.2f}'.format(x) if pd.notnull(x) else '')

    response = HttpResponse(content_type='application/vnd.ms-excel')
    response['Content-Disposition'] = 'attachment; filename=toolsbase_export.xlsx'
    df.to_excel(response, index=False)
    return response

# --------- AREA REPORTS --------------- #

@login_required(login_url='jobcards')
def jobcards_tam(request):
    qs = JobCard.objects.filter(comments__icontains='TAM')

    search = request.GET.get('search', '')
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    items_per_page = request.GET.get('items_per_page', '10')

    if search:
        qs = qs.filter(
            Q(discipline__icontains=search) |
            Q(job_card_number__icontains=search) |
            Q(prepared_by__icontains=search)
        )

    if start_date:
        start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
        qs = qs.filter(start__gte=start_date_obj)

    if end_date:
        end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
        qs = qs.filter(start__lte=end_date_obj)

    try:
        items_per_page = int(items_per_page)
    except (ValueError, TypeError):
        items_per_page = 10

    paginator = Paginator(qs, items_per_page)
    page = request.GET.get('page')
    try:
        jobcards_page = paginator.page(page)
    except PageNotAnInteger:
        jobcards_page = paginator.page(1)
    except EmptyPage:
        jobcards_page = paginator.page(paginator.num_pages)

    backups_dir = os.path.join(settings.BASE_DIR, 'jobcard_backups')
    available_pdfs = {f for f in os.listdir(backups_dir) if f.endswith('.pdf')}

    context = {
        'jobcards': jobcards_page,
        'search': search,
        'start_date': start_date,
        'end_date': end_date,
        'items_per_page': items_per_page,
        'paginator': paginator,
        'available_pdfs': available_pdfs,
        'tam_only': True,
        'request': request,  # Para usar request.GET.* no template
    }
    return render(request, 'sistema/jobcards.html', context)

# --------- AVANÇAR JOBCARDS --------------- #

def jobcard_progress(request):
    return render(request, 'sistema/avancar/jobcard_progress.html')

@require_GET
def api_jobcard_detail(request, jobcard_number):
    try:
        job = JobCard.objects.get(job_card_number=jobcard_number)
    except JobCard.DoesNotExist:
        return JsonResponse({'error': 'JobCard not found'}, status=404)

    data = {
        'job_card_number': job.job_card_number,
        'discipline': job.discipline,
        'location': job.location,
        'tag': job.tag,
        'jobcard_status': job.jobcard_status,
        'completed': job.completed,
        'prepared_by': job.prepared_by,
        'date_prepared': job.date_prepared.strftime('%Y-%m-%d') if job.date_prepared else '',
        'prepared_by': job.prepared_by,
        'working_code_description': job.working_code_description,
    }
    return JsonResponse(data)

@require_POST
def api_jobcard_advance(request, jobcard_number):
    try:
        job = JobCard.objects.get(job_card_number=jobcard_number)
    except JobCard.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'JobCard not found'}, status=404)
    job.completed = 'YES'
    job.save()
    return JsonResponse({'success': True})


# --------- AREA DE IMPEDIMENTOS --------------- #

@login_required
def create_impediment(request):
    error = None
    jobcard = None
    jobcard_number = ''

    if request.method == 'POST':
        form = ImpedimentsForm(request.POST)
        jobcard_number = request.POST.get('jobcard_number', '').strip()
        if not JobCard.objects.filter(job_card_number=jobcard_number).exists():
            error = f"JobCard '{jobcard_number}' does not exist."
        if form.is_valid() and not error:
            impediment = form.save(commit=False)
            impediment.created_by = request.user.username  # <--- SÓ O NOME
            impediment.save()
            return render(request, 'sistema/impediments/impediments.html', {'form': ImpedimentsForm(), 'success': True})

    else:
        form = ImpedimentsForm()

    return render(request, 'sistema/impediments/impediments.html', {
        'form': form,
        'jobcard_number': jobcard_number,
        'jobcard': jobcard,
        'error': error,
    })
        
@login_required(login_url='login')
def impediments_list(request):
    search = request.GET.get('search', '')
    items_per_page = int(request.GET.get('items_per_page', 10))
    page = request.GET.get('page', 1)

    qs = Impediments.objects.all().order_by('-created_at')

    if search:
        qs = qs.filter(
            Q(jobcard_number__icontains=search) |
            Q(notes__icontains=search) |
            Q(other__icontains=search)
        )

    paginator = Paginator(qs, items_per_page)
    impediments = paginator.get_page(page)
    
    items_options = [5, 10, 20, 50, 100]

    context = {
        'impediments': impediments,
        'search': search,
        'items_per_page': items_per_page,
        'paginator': paginator,
        'items_options': items_options,
    }
    return render(request, 'sistema/impediments/impediments_list.html', context)

@csrf_exempt
@login_required(login_url='login')
def impediment_update(request):
    if request.method == 'POST':
        id = request.POST.get('id')
        try:
            imped = Impediments.objects.get(id=id)
        except Impediments.DoesNotExist:
            return JsonResponse({'success': False, 'msg': 'Not found'})

        imped.jobcard_number = request.POST.get('jobcard_number', imped.jobcard_number)
        imped.scaffold      = request.POST.get('scaffold') == 'true'
        imped.material      = request.POST.get('material') == 'true'
        imped.engineering   = request.POST.get('engineering') == 'true'
        imped.other         = request.POST.get('other', '')
        imped.origin_shell  = request.POST.get('origin_shell') == 'true'
        imped.origin_utc    = request.POST.get('origin_utc') == 'true'
        imped.notes         = request.POST.get('notes', '')
        imped.mainpower = request.POST.get('mainpower') == 'true'
        imped.tools = request.POST.get('tools') == 'true'
        imped.access = request.POST.get('access') == 'true'
        imped.pwt = request.POST.get('pwt') == 'true'
        imped.save()
        return JsonResponse({'success': True})
    return JsonResponse({'success': False})

@csrf_exempt
@login_required(login_url='login')
def impediment_delete(request):
    if request.method == 'POST':
        id = request.POST.get('id')
        try:
            imped = Impediments.objects.get(id=id)
            imped.delete()
            return JsonResponse({'success': True})
        except Impediments.DoesNotExist:
            return JsonResponse({'success': False, 'msg': 'Not found'})
    return JsonResponse({'success': False})

# --------- AREA DE PMTO --------------- #

def pmto_list(request):
    pmto_items = PMTOBase.objects.all()
    return render(request, 'sistema/pmto/pmto_list.html', {'pmto_items': pmto_items})

@csrf_exempt
def import_pmto(request):
    if request.method == 'POST' and request.FILES.get('file'):
        try:
            file = request.FILES['file']
            df = pd.read_excel(file) if file.name.endswith('.xlsx') else pd.read_csv(file)
            force = request.POST.get('force_update') == 'true'

            # Coleta todos os PMTOCODE do arquivo
            pmto_codes = set(df['PMTOCODE'])
            # Checa se já existem no banco
            existing_codes = list(PMTOBase.objects.filter(pmto_code__in=pmto_codes).values_list('pmto_code', flat=True))

            # Se existe e não está forçando update, retorna para pedir confirmação
            if existing_codes and not force:
                return JsonResponse({
                    'status': 'need_confirm',
                    'duplicated_codes': list(existing_codes)
                })

            # Agora, valida DESCRIPTION+MATERIAL para cada linha
            for _, row in df.iterrows():
                other_pmto = PMTOBase.objects.filter(
                    description=row['DESCRITIVO'],
                    material=row['MATERIAL']
                ).exclude(pmto_code=row['PMTOCODE'])
                if other_pmto.exists():
                    return JsonResponse({
                        'status': 'descmat_duplicate',
                        'detail': (
                            f"<b>DESCRIPTION:</b> {row['DESCRITIVO']}<br>"
                            f"<b>MATERIAL:</b> {row['MATERIAL']}<br>"
                            f"Already registered for <b>PMTO CODE:</b> {other_pmto.first().pmto_code}"
                        )
                    })

            # Agora, faz o import normal (update_or_create)
            for _, row in df.iterrows():
                PMTOBase.objects.update_or_create(
                    pmto_code=row['PMTOCODE'],
                    defaults={
                        'description': row['DESCRITIVO'],
                        'material': row['MATERIAL'],
                        'qty': row['QTY'],
                        'weight': row['WEIGHT'],
                        'unit': row['unit']
                    }
                )

            return JsonResponse({'status': 'ok'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'invalid', 'message': 'No file uploaded'})

@login_required
def export_pmto_excel(request):
    # CAPTURA OS FILTROS ENVIADOS PELO FRONT
    pmto_code = request.GET.get('pmto_code', '')
    description = request.GET.get('description', '')
    material = request.GET.get('material', '')
    global_search = request.GET.get('search', '')

    # INICIA A QUERY
    qs = PMTOBase.objects.all()

    # FILTROS POR CAMPO INDIVIDUAL
    if pmto_code:
        qs = qs.filter(pmto_code__icontains=pmto_code)
    if description:
        qs = qs.filter(description__icontains=description)
    if material:
        qs = qs.filter(material__icontains=material)

    # FILTRO GLOBAL (BUSCA EM VÁRIOS CAMPOS)
    if global_search:
        qs = qs.filter(
            Q(pmto_code__icontains=global_search) |
            Q(description__icontains=global_search) |
            Q(material__icontains=global_search) |
            Q(unit__icontains=global_search)
        )

    # MONTA O DATAFRAME COM OS CAMPOS QUE QUER EXPORTAR
    data = qs.values(
        'pmto_code',
        'description',
        'material',
        'qty',
        'weight',
        'unit'
    )

    df = pd.DataFrame(list(data))

    # FORMATAÇÃO NUMÉRICA: duas casas, vírgula
    for col in ['qty', 'weight']:
        if col in df.columns:
            df[col] = df[col].apply(lambda x: '{:.2f}'.format(x).replace('.', ',') if pd.notnull(x) else '')

    # GERA O EXCEL PARA DOWNLOAD
    response = HttpResponse(content_type='application/vnd.ms-excel')
    response['Content-Disposition'] = 'attachment; filename=pmto_base_export.xlsx'
    df.to_excel(response, index=False)
    return response

# --------- AREA DE MATERIAL REQUISITION --------------- #

def mr_list(request):
    mr_items = MRBase.objects.all()
    return render(request, 'sistema/materialRequest/mr_list.html', {'mr_items': mr_items})

@csrf_exempt
def import_mr(request):
    if request.method == 'POST' and request.FILES.get('file'):
        try:
            file = request.FILES['file']
            df = pd.read_excel(file) if file.name.endswith('.xlsx') else pd.read_csv(file)
            mr_rev_set = set(zip(df['MR_NUMBER'], df['REV']))

            # Verifica se é preview ou overwrite:
            force = request.POST.get('force_overwrite') == 'true'

            # Verifica duplicidade
            existentes = [
                (mr, rev) for (mr, rev) in mr_rev_set
                if MRBase.objects.filter(mr_number=mr, rev=rev).exists()
            ]

            if existentes and not force:
                # Retorna para o frontend a lista de MR+REV que já existem
                return JsonResponse({'status': 'need_confirm', 'mr_rev': existentes})

            # Agora pode apagar e inserir
            for mr_number, rev in mr_rev_set:
                MRBase.objects.filter(mr_number=mr_number, rev=rev).delete()

            for _, row in df.iterrows():
                MRBase.objects.create(
                    mr_number=row['MR_NUMBER'],
                    pmto_code=row['PMTOCODE'],
                    type_items=row['TYPE ITEMS'],
                    basic_material=row['BASIC MATERIAL'],
                    description=row['DESCRIPTION'],
                    nps1=row['NPS 1'],
                    length_ft_inch=row["LENGTH (FT' INCH\")"],
                    thk_mm=row['THK (mm)'],
                    pid=row['P&ID'],
                    line_number=row['LINE Nº'],
                    qty=row['QTY'],
                    unit=row['UNIT'],
                    design_pressure_bar=row['DESIGN PRESSURE (Bar)'],
                    design_temperature_c=row['DESIGN TEMPERATURE (ºC)'],
                    service=row['SERVICE'],
                    spec=row['SPEC'],
                    proposer_sap_code=row['PROPOSER CODE (SAP CODE)'],
                    rev=row['REV'],
                    notes=row.get('NOTES', '')
                )
            return JsonResponse({'status': 'ok'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'invalid', 'message': 'No file uploaded'})

@login_required
def export_mr_excel(request):
    mr_number = request.GET.get('mr_number', '')
    pmto_code = request.GET.get('pmto_code', '')
    basic_material = request.GET.get('basic_material', '')
    global_search = request.GET.get('search', '')

    qs = MRBase.objects.all()

    if mr_number:
        qs = qs.filter(mr_number__icontains=mr_number)
    if pmto_code:
        qs = qs.filter(pmto_code__icontains=pmto_code)
    if basic_material:
        qs = qs.filter(basic_material__icontains=basic_material)

    if global_search:
        qs = qs.filter(
            Q(mr_number__icontains=global_search) |
            Q(pmto_code__icontains=global_search) |
            Q(basic_material__icontains=global_search) |
            Q(description__icontains=global_search)
        )

    data = qs.values(
        'mr_number', 'pmto_code', 'type_items', 'basic_material', 'description',
        'nps1', 'length_ft_inch', 'thk_mm', 'pid', 'line_number',
        'qty', 'unit', 'design_pressure_bar', 'design_temperature_c',
        'service', 'spec', 'proposer_sap_code', 'rev', 'notes'
    )

    df = pd.DataFrame(list(data))
    if 'qty' in df.columns:
        df['qty'] = df['qty'].apply(lambda x: '{:.2f}'.format(x).replace('.', ',') if pd.notnull(x) else '')

    response = HttpResponse(content_type='application/vnd.ms-excel')
    response['Content-Disposition'] = 'attachment; filename=mr_base_export.xlsx'
    df.to_excel(response, index=False)
    return response


# --------- AREA DE PROCUREMENT BASE --------------- #

def procurement_list(request):
    procurement_items = ProcurementBase.objects.all()
    return render(request, 'sistema/ProcurementBase/procurement_list.html', {'procurement_items': procurement_items})

@csrf_exempt
def import_procurement(request):
    if request.method == 'POST' and request.FILES.get('file'):
        try:
            file = request.FILES['file']
            df = pd.read_excel(file) if file.name.endswith('.xlsx') else pd.read_csv(file)
            for _, row in df.iterrows():
                ProcurementBase.objects.update_or_create(
                    po_number=row['PO NUMBER'],
                    po_issue_date=row['PO ISSUE DATE'],
                    mr_number=row['MR NUMBER'],
                    latest_rev=row['LATEST REV.'],
                    mto_item_no=row['MTO ITEM NO'],
                    pmto_code=row['PMTOCODE'],
                    type_items=row['TYPE ITEMS'],
                    basic_material=row['BASIC MATERIAL'],
                    description=row['DESCRIPTION'],
                    nps1=row.get('NPS 1', ''),
                    nps2=row.get('NPS 2', ''),
                    sch1=row.get('SCH 1', ''),
                    sch2=row.get('SCH 2', ''),
                    unit=row['UNIT'],
                    qty_mr=row['QTY_MR'],
                    qty_mr_unit=row['QTY_MR Unit'],
                    qty_purchased=row['QTY PURCHASED'],
                    qty_purchased_unit=row['QTY PURCHASED Unit'],
                    delivery_term=row['DELIVERY TERM'],
                    delivery_time=row['DELIVERY TIME'],
                    supplier_vendor=row['SUPPLIER/VENDOR'],
                    status_remarks=row.get('STATUS / REMARKS', ''),
                )
            return JsonResponse({'status': 'ok'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'invalid', 'message': 'No file uploaded'})

@login_required
def export_procurement_excel(request):
    mr_number = request.GET.get('mr_number', '')
    pmto_code = request.GET.get('pmto_code', '')
    basic_material = request.GET.get('basic_material', '')
    global_search = request.GET.get('search', '')

    qs = ProcurementBase.objects.all()
    if mr_number:
        qs = qs.filter(mr_number__icontains=mr_number)
    if pmto_code:
        qs = qs.filter(pmto_code__icontains=pmto_code)
    if basic_material:
        qs = qs.filter(basic_material__icontains=basic_material)
    if global_search:
        qs = qs.filter(
            Q(mr_number__icontains=global_search) |
            Q(pmto_code__icontains=global_search) |
            Q(basic_material__icontains=global_search) |
            Q(description__icontains=global_search)
        )

    data = qs.values(
        'mr_number',
        'latest_rev',
        'mto_item_no',
        'pmto_code',
        'type_items',
        'basic_material',
        'description',
        'nps1',
        'nps2',
        'sch1',
        'sch2',
        'unit',
        'qty_mr',
        'qty_mr_unit',
        'qty_purchased',
        'qty_purchased_unit',
        'delivery_term',
        'delivery_time',
        'po_issue_date',
        'po_number',
        'supplier_vendor',
        'status_remarks'
    )

    df = pd.DataFrame(list(data))

    # Formatação de QTYs (duas casas, vírgula)
    for col in ['qty_mr', 'qty_purchased']:
        if col in df.columns:
            df[col] = df[col].apply(lambda x: '{:.2f}'.format(x).replace('.', ',') if pd.notnull(x) else '')

    # Formatação de data para exportação
    if 'po_issue_date' in df.columns:
        df['po_issue_date'] = pd.to_datetime(df['po_issue_date']).dt.strftime('%Y-%m-%d')

    response = HttpResponse(content_type='application/vnd.ms-excel')
    response['Content-Disposition'] = 'attachment; filename=procurement_base_export.xlsx'
    df.to_excel(response, index=False)
    return response


# AREA PARA NOTIFICAÇÕES DO USUARIO

from jobcards.models import EngineeringBase, DocumentoRevisaoAlterada

def api_revisoes_ultimas(request):
    # Filtra apenas revisões cujo código existe na EngineeringBase.document
    codigos_validos = EngineeringBase.objects.values_list('document', flat=True)
    revisoes = DocumentoRevisaoAlterada.objects.filter(
        codigo__in=codigos_validos
    ).order_by('-data_mudanca')[:7]
    data = [
        {
            "codigo": rev.codigo,
            "nome_projeto": rev.nome_projeto,
            "revisao_anterior": rev.revisao_anterior,
            "revisao_nova": rev.revisao_nova,
            "data_mudanca": rev.data_mudanca.strftime("%d/%m/%Y %H:%M"),
        }
        for rev in revisoes
    ]
    return JsonResponse({"revisoes": data})
