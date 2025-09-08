from django.http import JsonResponse, HttpResponseBadRequest
from django.core.cache import cache
from django_rq import get_queue
from django.utils.crypto import get_random_string
from django.views.decorators.http import require_POST, require_GET
from django_redis import get_redis_connection

from .models import JobCard
from .pdf_tasks import render_jobcard_pdf_job, compute_jobcard_fingerprint


def _queue_busy():
    """Retorna True se a fila 'pdf' tiver jobs pendentes."""
    q = get_queue('pdf')
    try:
        return q.count > 0
    except Exception:
        return False


@require_POST
def api_pdf_run_start(request):
    """
    Inicia um novo 'run' de regeneração:
    - Se houver um run ATIVO (fila ocupada ou progresso não finalizado), anexa ao run ativo (status='attached')
    - Se 'hard=1', limpa a fila atual e cancela o run anterior antes de enfileirar
    - Se 'force=1', ignora fingerprint e re-enfileira tudo
    """
    force = request.GET.get('force') == '1'
    hard  = request.GET.get('hard') == '1'
    q = get_queue('pdf')

    # Descobre se há run anterior "vivo"
    prev = cache.get('pdf:last_run')
    prev_total = int(cache.get(f'pdf:{prev}:total') or 0) if prev else 0
    prev_done  = int(cache.get(f'pdf:{prev}:done') or 0)  if prev else 0
    prev_open  = bool(prev and (prev_done < prev_total))

    # Se a fila está ocupada OU o run anterior não terminou, anexa ao anterior (a menos que seja "hard")
    if prev and (_queue_busy() or prev_open) and not hard:
        return JsonResponse({
            'status': 'attached',        # front só deve começar a fazer poll
            'run_id': prev,
            'total':  prev_total,
            'done':   prev_done,
        })

    # Se pediu "hard", limpamos a fila e marcamos stop no run anterior
    if prev and hard:
        try:
            q.empty()  # limpa jobs pendentes (atenção: limpa TUDO da fila 'pdf')
        except Exception:
            pass
        cache.set(f'pdf:{prev}:stop', 1, 24 * 3600)

    # Novo run
    run_id = get_random_string(8).upper()

    # zera contadores do novo run
    for k in ('done', 'ok', 'err', 'total'):
        cache.set(f'pdf:{run_id}:{k}', 0, 24 * 3600)

    owner_id = (
        request.user.id
        if getattr(request, "user", None) and request.user.is_authenticated
        else 1
    )

    jobs = []
    # Só processa quem NÃO está "NO CHECKED"/"NOT CHECKED"
    qs = JobCard.objects.exclude(jobcard_status__in=['NO CHECKED', 'NOT CHECKED']) \
                        .values_list('job_card_number', flat=True)

    for jc in qs:
        fp = compute_jobcard_fingerprint(jc)
        last = cache.get(f'pdf:lastfp:{jc}')
        if not force and last == fp:
            continue
        q.enqueue(render_jobcard_pdf_job, run_id, jc, owner_id, fp)
        jobs.append(jc)

    total = len(jobs)
    cache.set(f'pdf:{run_id}:total', total, 24 * 3600)
    cache.set('pdf:last_run', run_id, 24 * 3600)

    return JsonResponse({'status': 'ok', 'run_id': run_id, 'total': total})


@require_GET
def api_pdf_run_progress(request):
    """Retorna progresso do run atual (ou do run_id informado)."""
    run_id = request.GET.get('run_id') or cache.get('pdf:last_run')
    if not run_id:
        return JsonResponse({'status': 'ok', 'total': 0, 'done': 0, 'err': 0, 'ok': 0})

    total = int(cache.get(f'pdf:{run_id}:total') or 0)
    done  = int(cache.get(f'pdf:{run_id}:done') or 0)
    err   = int(cache.get(f'pdf:{run_id}:err') or 0)
    okc   = int(cache.get(f'pdf:{run_id}:ok') or 0)

    return JsonResponse({
        'status': 'ok',
        'run_id': run_id,
        'total': total,
        'done': done,
        'err': err,
        'ok': okc,
    })


@require_POST
def api_pdf_run_stop(request):
    """
    Marca o run_id como cancelado.
    Se 'hard=1', também esvazia a fila 'pdf'.
    """
    run_id = request.POST.get('run_id') or cache.get('pdf:last_run')
    if not run_id:
        return HttpResponseBadRequest('run_id required')

    cache.set(f'pdf:{run_id}:stop', 1, 24 * 3600)

    if request.GET.get('hard') == '1':
        q = get_queue('pdf')
        try:
            q.empty()
        except Exception:
            pass

    return JsonResponse({'status': 'ok'})


@require_GET
def api_pdf_run_log(request):
    """Lê as últimas linhas de log desse run no Redis."""
    run_id = request.GET.get('run_id') or cache.get('pdf:last_run')
    if not run_id:
        return HttpResponseBadRequest('run_id required')

    r = get_redis_connection('default')
    key = f'pdf:{run_id}:log'
    items = r.lrange(key, -200, -1)  # últimas 200 linhas
    lines = [(x.decode('utf-8') if isinstance(x, bytes) else x) for x in items]
    return JsonResponse({'status': 'ok', 'log': lines})
