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
from .forms import DisciplineForm, AreaForm, WorkingCodeForm, SystemForm
import datetime

from django.conf import settings

from .models import (
    JobCard, TaskBase, ManpowerBase, MaterialBase, ToolsBase, EngineeringBase,
    AllocatedEngineering, AllocatedManpower, AllocatedMaterial, AllocatedTool, AllocatedTask,
    Discipline, Area, WorkingCode, System,
)

import tempfile
from django.db.models import Sum
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from .models import MaterialBase, JobCard
import pandas as pd
from django.utils import timezone




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
@login_required(login_url='dashboard') # EXIGE O USUARIO A ESTAR LOGADO
def dashboard(request):
    # Summary cards
    total_jobcards = JobCard.objects.count()
    not_checked_count = JobCard.objects.filter(jobcard_status='not checked').count()
    checked_count = JobCard.objects.filter(jobcard_status='checked').count()

    # Charts
    not_checked_qs = (
        JobCard.objects
        .filter(jobcard_status='not checked')
        .values('discipline')
        .annotate(count=Count('id'))
        .order_by('discipline')
    )
    labels_not_checked = [entry['discipline'] for entry in not_checked_qs]
    data_not_checked   = [entry['count']      for entry in not_checked_qs]

    total_by_disc = (
        JobCard.objects
        .values('discipline')
        .annotate(count=Count('id'))
        .order_by('discipline')
    )
    labels_total = [entry['discipline'] for entry in total_by_disc]
    data_total   = [entry['count']      for entry in total_by_disc]

    # AWP Monitor: System > WorkPack > JobCards
    awp_data = defaultdict(lambda: defaultdict(list))
    for jc in JobCard.objects.all().order_by('system', 'workpack_number', 'job_card_number'):
        if jc.system and jc.workpack_number:
            awp_data[jc.system][jc.workpack_number].append(jc)

    context = {
        'total_jobcards': total_jobcards,
        'not_checked_count': not_checked_count,
        'checked_count': checked_count,
        'labels_not_checked': labels_not_checked,
        'data_not_checked': data_not_checked,
        'labels_total': labels_total,
        'data_total': data_total,
        'awp_data': awp_data,
    }
    return render(request, 'sistema/dashboard.html', context)

@login_required(login_url='jobcards')
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
        try:
            start = datetime.strptime(start_date, '%Y-%m-%d').date()
            qs = qs.filter(date_prepared__gte=start)
        except ValueError:
            pass

    if end_date:
        try:
            end = datetime.strptime(end_date, '%Y-%m-%d').date()
            qs = qs.filter(date_prepared__lte=end)
        except ValueError:
            pass

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
@login_required(login_url='create_jobcard') # EXIGE O USUARIO A ESTAR LOGADO
def create_jobcard(request, jobcard_id=None):
    return render(request, 'sistema/create_jobcard.html')

@login_required(login_url='login')
def edit_jobcard(request, jobcard_id=None):
    job = get_object_or_404(JobCard, job_card_number=jobcard_id) if jobcard_id else None

    if request.method == 'POST' and job:
        # Atualiza os campos principais da JobCard
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

        # Incrementa a revisão
        if job.rev and job.rev.isdigit():
            job.rev = str(int(job.rev) + 1)
        else:
            job.rev = '1'

        # Salva quem alterou
        job.last_modified_by = request.user.username
        job.save()

        def safe_float(s):
            return float(s.replace('%', '')) if s and s.strip() else 0.0

        mp_pattern = re.compile(r'^mp-(\d+)-(\d+)-qty$')

        with transaction.atomic():
            AllocatedManpower.objects.filter(jobcard_number=job.job_card_number).delete()
            AllocatedTask.objects.filter(jobcard_number=job.job_card_number).delete()
            AllocatedMaterial.objects.filter(jobcard_number=job.job_card_number).delete()

            task_list = TaskBase.objects.filter(working_code=job.working_code).order_by('item')
            task_index_map = {str(idx): task.item for idx, task in enumerate(task_list, start=1)}

            not_applicable_tasks = set()
            for key in request.POST.keys():
                if key.startswith('task-not-applicable-'):
                    task_index = int(key.replace('task-not-applicable-', ''))
                    not_applicable_tasks.add(task_index)

            # Salvar manpowers
            for key, val in request.POST.items():
                match = mp_pattern.match(key)
                if not match:
                    continue

                task_idx, mp_id = match.group(1), int(match.group(2))
                if int(task_idx) in not_applicable_tasks:
                    continue

                qty = safe_float(val)
                hh_key = f"mp-{task_idx}-{mp_id}-hh"
                hours = safe_float(request.POST.get(hh_key, ''))

                if qty == 0.0 and hours == 0.0:
                    continue

                mp = ManpowerBase.objects.get(pk=mp_id)
                AllocatedManpower.objects.create(
                    jobcard_number=job.job_card_number,
                    discipline=mp.discipline,
                    working_code=mp.working_code,
                    direct_labor=mp.direct_labor,
                    qty=qty,
                    hours=hours,
                    task_order=task_index_map.get(task_idx, int(task_idx)),
                )

            # Salvar tarefas alocadas
            for idx, task in enumerate(task_list, start=1):
                max_hh = request.POST.get(f"hh-max-{idx}", '0')
                total_hh = request.POST.get(f"hh-total-{idx}", '0')
                percent = request.POST.get(f"hh-percent-{idx}", '0')

                if request.POST.get(f"task-not-applicable-{idx}") == 'on':
                    continue

                AllocatedTask.objects.create(
                    jobcard_number=job.job_card_number,
                    task_order=task.item,
                    description=task.typical_task,
                    max_hours=safe_float(max_hh),
                    total_hours=safe_float(total_hh),
                    percent=safe_float(percent),
                )

            # Salvar materiais alocados
            project_codes = request.POST.getlist('project_code[]')
            descriptions = request.POST.getlist('description[]')
            jobcard_required_qtys = request.POST.getlist('jobcard_required_qty[]')
            comments = request.POST.getlist('comments[]')
            nps1_list = request.POST.getlist('nps1[]')  # Captura o campo NPS1

            for code, desc, qty, comment, nps1 in zip(project_codes, descriptions, jobcard_required_qtys, comments, nps1_list):
                AllocatedMaterial.objects.create(
                    jobcard_number=job.job_card_number,
                    discipline=job.discipline,
                    working_code=job.working_code,
                    pmto_code=code,
                    description=desc,
                    qty=float(qty.replace(',', '.')) if qty else 0.0,
                    comments=comment,
                    nps1=nps1  # Aqui você passa o valor correto
                )


            # Salvar ferramentas alocadas
            tool_items = request.POST.getlist('tool_item[]')
            tool_disciplines = request.POST.getlist('tool_discipline[]')
            tool_working_codes = request.POST.getlist('tool_working_code[]')
            tool_direct_labors = request.POST.getlist('tool_direct_labor[]')
            tool_qty_direct_labors = request.POST.getlist('tool_qty_direct_labor[]')
            tool_special_toolings = request.POST.getlist('tool_special_tooling[]')
            tool_qtys = request.POST.getlist('tool_qty[]')

            AllocatedTool.objects.filter(jobcard_number=job.job_card_number).delete()

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

            AllocatedEngineering.objects.filter(jobcard_number=job.job_card_number).delete()

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

        # Calcula o TOTAL DURATION (hs)
        total_duration_hs = AllocatedTask.objects.filter(jobcard_number=job.job_card_number).aggregate(total=Sum('max_hours'))['total'] or 0

        # Calcula o TOTAL MAN-HOURS
        total_man_hours = AllocatedTask.objects.filter(jobcard_number=job.job_card_number).aggregate(total=Sum('total_hours'))['total'] or 0

        # Salva na JobCard
        job.total_duration_hs = f'{total_duration_hs:.2f}'
        job.total_man_hours = f'{total_man_hours:.2f}'
        job.save(update_fields=['total_duration_hs', 'total_man_hours'])

        return redirect('generate_pdf', jobcard_id=job.job_card_number)

    # GET: Prepara contexto
    disciplinas = JobCard.objects.values_list('discipline', flat=True).distinct().order_by('discipline')
    discipline_codes = JobCard.objects.values_list('discipline_code', flat=True).distinct().order_by('discipline_code')
    locations = JobCard.objects.values_list('location', flat=True).distinct().order_by('location')
    levels = JobCard.objects.values_list('level', flat=True).distinct().order_by('level')
    activity_ids = JobCard.objects.values_list('activity_id', flat=True).distinct().order_by('activity_id')
    systems = JobCard.objects.values_list('system', flat=True).distinct().order_by('system')
    subsystems = JobCard.objects.values_list('subsystem', flat=True).distinct().order_by('subsystem')
    workpacks = JobCard.objects.values_list('workpack_number', flat=True).distinct().order_by('workpack_number')

    task_list = TaskBase.objects.filter(working_code=job.working_code) if job else []
    manpowers = ManpowerBase.objects.filter(working_code__in=[t.working_code for t in task_list])
    manpowers_dict = defaultdict(list)
    for mp in manpowers:
        manpowers_dict[mp.working_code].append(mp)

    materials_list = MaterialBase.objects.filter(job_card_number=job.job_card_number) if job else []
    tools_list = ToolsBase.objects.filter(working_code=job.working_code) if job else []
    engineering_list = EngineeringBase.objects.filter(jobcard_number=job.job_card_number) if job else []

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

    if job.jobcard_status != 'checked':
        job.jobcard_status = 'checked'
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

# DATABASES - EXIBIÇÕES

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
    context = {
        'tasks': tasks
    }
    return render(request, 'sistema/databases/task_list.html', context)

#ALOCAÇÕES NOS BANCOS

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

#IMPORTAÇÕES PARA O BANCO

@csrf_exempt
def import_materials(request):
    if request.method == "POST":
        overwrite = request.POST.get('overwrite') == '1'
        file = request.FILES.get('file')
        if not file:
            return JsonResponse({'status': 'error', 'message': 'No file uploaded.'})

        # Lê o arquivo
        try:
            if file.name.endswith('.csv'):
                df = pd.read_csv(file)
            else:
                df = pd.read_excel(file)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f'Could not read file: {str(e)}'})

        # Lista das colunas obrigatórias
        required_columns = [
            'job_card_number', 'working_code', 'discipline', 'tag_jobcard_base',
            'jobcard_required_qty', 'unit_req_qty', 'weight_kg', 'material_segmentation',
            'comments', 'sequenc_no_procurement', 'status_procurement', 'mto_item_no',
            'basic_material', 'description', 'project_code', 'nps1', 'qty', 'unit', 'po'
        ]
        # item é opcional — só inclua se quiser importar a coluna "item" do Excel/CSV.

        # Valida colunas
        missing = [col for col in required_columns if col not in df.columns]
        if missing:
            return JsonResponse({'status': 'error', 'message': f"Missing columns: {', '.join(missing)}"})

        # Pega o job_card_number da primeira linha
        job_card_number = str(df['job_card_number'].iloc[0]).strip()
        if not JobCard.objects.filter(job_card_number=job_card_number).exists():
            return JsonResponse({'status': 'error', 'message': f"Job Card '{job_card_number}' does not exist."})

        materials_exist = MaterialBase.objects.filter(job_card_number=job_card_number).exists()

        # Se já existe material e não é overwrite, pede confirmação
        if materials_exist and not overwrite:
            return JsonResponse({'status': 'duplicate', 'message': 'Materials already registered for this Job Card.'})

        # Se é overwrite, apaga antes de inserir os novos
        if overwrite and materials_exist:
            MaterialBase.objects.filter(job_card_number=job_card_number).delete()

        # Insere os novos materiais
        for idx, row in df.iterrows():
            try:
                MaterialBase.objects.create(
                    # Se quiser importar 'item', descomente a linha abaixo:
                    # item = row.get('item') if 'item' in row else None,
                    job_card_number = str(row['job_card_number']).strip(),
                    working_code = str(row.get('working_code', '')).strip(),
                    discipline = str(row.get('discipline', '')).strip(),
                    tag_jobcard_base = str(row.get('tag_jobcard_base', '')).strip(),
                    jobcard_required_qty = float(row.get('jobcard_required_qty', 0)) if row.get('jobcard_required_qty') not in [None, ''] else None,
                    unit_req_qty = str(row.get('unit_req_qty', '')).strip(),
                    weight_kg = float(row.get('weight_kg', 0)) if row.get('weight_kg') not in [None, ''] else None,
                    material_segmentation = str(row.get('material_segmentation', '')).strip(),
                    comments = str(row.get('comments', '')).strip(),
                    sequenc_no_procurement = str(row.get('sequenc_no_procurement', '')).strip(),
                    status_procurement = str(row.get('status_procurement', '')).strip(),
                    mto_item_no = str(row.get('mto_item_no', '')).strip(),
                    basic_material = str(row.get('basic_material', '')).strip(),
                    description = str(row.get('description', '')).strip(),
                    project_code = str(row.get('project_code', '')).strip(),
                    nps1 = str(row.get('nps1', '')).strip(),
                    qty = float(row.get('qty', 0)) if row.get('qty') not in [None, ''] else None,
                    unit = str(row.get('unit', '')).strip(),
                    po = str(row.get('po', '')).strip(),
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
                jobcard = JobCard.objects.create(**data)

        return JsonResponse({'status': 'ok'})
    return JsonResponse({'status': 'error', 'message': 'Invalid request.'})

@login_required
def import_manpower(request):
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

        for _, row in df.iterrows():
            # Verifica se working_code existe na tabela WorkingCode (campo code)
            if not WorkingCode.objects.filter(code=row["working_code"]).exists():
                return JsonResponse({
                    'status': 'error',
                    'message': f"Working code '{row['working_code']}' is not registered in the WorkingCode base. Only registered codes are allowed."
                })

            exists = ManpowerBase.objects.filter(
                working_code=row["working_code"],
                direct_labor=row["direct_labor"]
            ).exists()
            if exists and not overwrite:
                return JsonResponse({
                    'status': 'duplicate',
                    'message': f"Manpower with working_code '{row['working_code']}' and direct_labor '{row['direct_labor']}' already exists. Overwrite?"
                })

            if exists and overwrite:
                mp = ManpowerBase.objects.get(
                    working_code=row["working_code"],
                    direct_labor=row["direct_labor"]
                )
                for field in required_fields:
                    setattr(mp, field, row[field])
                mp.save()
            else:
                data = {field: row[field] for field in required_fields}
                ManpowerBase.objects.create(**data)

        return JsonResponse({'status': 'ok'})
    return JsonResponse({'status': 'error', 'message': 'Invalid request.'})

@login_required
def import_toolsbase(request):
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
            if df[field].isnull().any() or (df[field] == '').any():
                empty_fields.append(field)
        if empty_fields:
            return JsonResponse({'status': 'error', 'message': f"Please fill all required fields: {', '.join(empty_fields)}"})

        for _, row in df.iterrows():
            # VALIDAÇÃO: working_code deve existir em WorkingCode
            if not WorkingCode.objects.filter(code=row["working_code"]).exists():
                return JsonResponse({
                    'status': 'error',
                    'message': f"Working code '{row['working_code']}' is not registered in the WorkingCode base. Only registered codes are allowed."
                })

            exists = ToolsBase.objects.filter(
                direct_labor=row["direct_labor"],
                special_tooling=row["special_tooling"]
            ).exists()

            if exists and not overwrite:
                return JsonResponse({
                    'status': 'duplicate',
                    'message': f"Tool '{row['special_tooling']}' already registered for direct labor '{row['direct_labor']}'. Overwrite?"
                })

            if exists and overwrite:
                tool = ToolsBase.objects.get(
                    direct_labor=row["direct_labor"],
                    special_tooling=row["special_tooling"]
                )
                for field in required_fields:
                    setattr(tool, field, row[field])
                tool.save()
            else:
                data = {field: row[field] for field in required_fields}
                ToolsBase.objects.create(**data)

        return JsonResponse({'status': 'ok'})
    return JsonResponse({'status': 'error', 'message': 'Invalid request.'})

@login_required
def import_engineering(request):
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
            "discipline",
            "document",
            "tag",
            "rev",
            "status"
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
            exists = EngineeringBase.objects.filter(
                document=row["document"],
                tag=row["tag"]
            ).exists()

            if exists and not overwrite:
                return JsonResponse({
                    'status': 'duplicate',
                    'message': f"Document '{row['document']}' already registered for tag '{row['tag']}'. Overwrite?"
                })

            if exists and overwrite:
                eng = EngineeringBase.objects.get(
                    document=row["document"],
                    tag=row["tag"]
                )
                for field in required_fields:
                    setattr(eng, field, row[field])
                eng.save()
            else:
                data = {field: row[field] for field in required_fields}
                EngineeringBase.objects.create(**data)

        return JsonResponse({'status': 'ok'})
    return JsonResponse({'status': 'error', 'message': 'Invalid request.'})

@login_required
def import_taskbase(request):
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
            if df[field].isnull().any() or (df[field] == '').any():
                empty_fields.append(field)
        if empty_fields:
            return JsonResponse({'status': 'error', 'message': f"Please fill all required fields: {', '.join(empty_fields)}"})

        for _, row in df.iterrows():
            # VALIDAÇÃO: working_code deve existir em WorkingCode
            if not WorkingCode.objects.filter(code=row["working_code"]).exists():
                return JsonResponse({
                    'status': 'error',
                    'message': f"Working code '{row['working_code']}' is not registered in the WorkingCode base. Only registered codes are allowed."
                })

            exists = TaskBase.objects.filter(
                working_code=row["working_code"],
                typical_task=row["typical_task"]
            ).exists()

            if exists and not overwrite:
                return JsonResponse({
                    'status': 'duplicate',
                    'message': f"Task '{row['typical_task']}' already registered for working code '{row['working_code']}'. Overwrite?"
                })

            if exists and overwrite:
                task = TaskBase.objects.get(
                    working_code=row["working_code"],
                    typical_task=row["typical_task"]
                )
                for field in required_fields:
                    setattr(task, field, row[field])
                task.save()
            else:
                data = {field: row[field] for field in required_fields}
                TaskBase.objects.create(**data)

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
