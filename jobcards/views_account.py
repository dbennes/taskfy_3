# jobcards/views_account.py
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.password_validation import validate_password
from django.contrib import messages
from django.http import JsonResponse, HttpResponseBadRequest
from django.shortcuts import render, redirect

from .forms import ProfileForm, CustomPasswordChangeForm  # <-- seus forms

@login_required
def user_profile(request):
    """
    Página de Profile:
    - GET: entrega ProfileForm preenchido + CustomPasswordChangeForm para o modal.
    - POST (action=update_profile): salva nome/sobrenome/email e volta pra página.
    """
    if request.method == "POST" and request.POST.get("action") == "update_profile":
        form = ProfileForm(request.POST, instance=request.user)
        pwd_form = CustomPasswordChangeForm(user=request.user)  # só para renderizar o modal
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully.")
            return redirect("user_profile")
        else:
            messages.error(request, "Please fix the errors below.")
    else:
        form = ProfileForm(instance=request.user)
        pwd_form = CustomPasswordChangeForm(user=request.user)

    context = {
        "form": form,
        "pwd_form": pwd_form,
        "groups": request.user.groups.all(),  # seu template usa
        "sessions": [],                      # preencha se tiver sua lógica
    }
    # ATENÇÃO: confirme se este é o mesmo template que você mostrou
    return render(request, "sistema/user_profile/user_profile.html", context)


@login_required
def api_change_password(request):
    """
    Troca de senha via AJAX.
    Aceita tanto os nomes do PasswordChangeForm (old_password/new_password1/new_password2)
    quanto o seu formato (current_password/new_password/new_password2).
    Retorna JSON no formato esperado pelo seu JS do modal.
    """
    if request.method != "POST" or request.headers.get("X-Requested-With") != "XMLHttpRequest":
        return HttpResponseBadRequest("Invalid request")

    # 1) Se vier com os campos do PasswordChangeForm, use-o (mais seguro/clean)
    if any(k in request.POST for k in ("old_password", "new_password1", "new_password2")):
        form = PasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # mantém sessão
            return JsonResponse({"ok": True, "message": "Password changed successfully."})
        errors = {k: [str(e) for e in v] for k, v in form.errors.items()}
        nfe = [str(e) for e in form.non_field_errors()]
        return JsonResponse({"ok": False, "errors": errors, "non_field_errors": nfe}, status=400)

    # 2) Caso contrário, trate o formato "current_password/new_password/new_password2"
    user = request.user
    current = request.POST.get("current_password", "")
    new1 = request.POST.get("new_password", "")
    new2 = request.POST.get("new_password2", "")

    if new1 != new2:
        return JsonResponse({"ok": False, "detail": "Senhas novas não conferem."}, status=400)
    if not user.check_password(current):
        return JsonResponse({"ok": False, "detail": "Senha atual incorreta."}, status=400)
    try:
        validate_password(new1, user=user)
    except Exception as e:
        msgs = getattr(e, "messages", None) or [str(e)]
        return JsonResponse({"ok": False, "detail": "; ".join(str(x) for x in msgs)}, status=400)

    user.set_password(new1)
    user.save(update_fields=["password"])
    auth_user = authenticate(request, username=user.username, password=new1)
    if auth_user is not None:
        login(request, auth_user)
    return JsonResponse({"ok": True, "message": "Password changed successfully."})
