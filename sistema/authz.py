# sistema/authz.py
from functools import wraps
from typing import Iterable, Set
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.decorators import method_decorator

def _user_groups(user) -> Set[str]:
    return set(user.groups.values_list("name", flat=True)) if user.is_authenticated else set()

def user_in_groups(user, groups: Iterable[str], any_: bool = True) -> bool:
    if not user.is_authenticated:
        return False
    wanted = set(groups)
    has = _user_groups(user)
    return bool(has & wanted) if any_ else wanted.issubset(has)

def _deny_with_modal(
    request,
    msg="Access denied. You do not have sufficient privileges to perform this action. "
        "If you believe this is an error, please contact your system administrator."
):
    # AJAX → JSON 403 (frontend mostra o mesmo modal)
    if request.headers.get("x-requested-with") == "XMLHttpRequest" or "application/json" in request.headers.get("Accept",""):
        return JsonResponse({"ok": False, "error": "forbidden", "message": msg}, status=403)

    # Padrão → mensagem + redirect para a página anterior (ou dashboard)
    messages.error(request, msg, extra_tags="modal-permission")
    back = request.META.get("HTTP_REFERER") or reverse("dashboard")
    return redirect(back)

def group_required(*groups: str, any_: bool = True):
    def decorator(view_func):
        @login_required(login_url="login")
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if not user_in_groups(request.user, groups, any_=any_):
                return _deny_with_modal(request)
            return view_func(request, *args, **kwargs)
        return _wrapped
    return decorator

def allow_groups(view_func, *groups: str, any_: bool = True):
    return group_required(*groups, any_=any_)(view_func)

def cbv_group_protect(ViewClass, *groups: str, any_: bool = True):
    decorated = method_decorator(group_required(*groups, any_=any_), name="dispatch")(ViewClass)
    return decorated.as_view()
