# sistema/views_account.py
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import update_session_auth_hash
from django.shortcuts import render, redirect
from django.utils import timezone, translation
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import ensure_csrf_cookie
from django.http import JsonResponse

from .forms import ProfileForm, CustomPasswordChangeForm


@ensure_csrf_cookie  # Ensure CSRF cookie is set so AJAX can send it back
@login_required
def user_profile(request):
    """
    User profile screen.
    - ProfileForm updates first_name/last_name/email.
    - Password change is handled via AJAX (api_change_password).
    - Force English UI/help_text using translation.override('en') for this page.
    """
    user = request.user

    # Render in English (labels/help_text/messages) regardless of site locale
    with translation.override('en'):
        if request.method == "POST":
            action = request.POST.get("action")

            if action == "update_profile":
                # Update basic profile fields
                form = ProfileForm(request.POST, instance=user)
                if form.is_valid():
                    form.save()
                    messages.success(request, "Profile updated successfully.")
                    return redirect("user_profile")
                else:
                    # Keep password form clean on profile validation errors
                    pwd_form = CustomPasswordChangeForm(user=user)

            elif action == "change_password":
                # Legacy fallback — prefer using the AJAX endpoint instead
                form = ProfileForm(instance=user)
                pwd_form = CustomPasswordChangeForm(user=user, data=request.POST)
                if pwd_form.is_valid():
                    pwd_form.save()
                    update_session_auth_hash(request, pwd_form.user)  # keep user logged in
                    messages.success(request, "Password changed successfully.")
                    return redirect("user_profile")
                else:
                    messages.error(request, "Please correct the errors in the password form.")

            else:
                # Unknown action → just show both forms
                form = ProfileForm(instance=user)
                pwd_form = CustomPasswordChangeForm(user=user)
        else:
            # GET: initial forms
            form = ProfileForm(instance=user)
            pwd_form = CustomPasswordChangeForm(user=user)

    # Read-only groups (group memberships should be managed by admins)
    groups = list(user.groups.values_list("name", flat=True))

    context = {
        "form": form,
        "pwd_form": pwd_form,  # used by the modal fields
        "groups": groups,
        "now": timezone.now(),
    }
    # Keep your current template path
    return render(request, "sistema/user_profile/user_profile.html", context)


@login_required
@require_POST
def api_change_password(request):
    """
    AJAX endpoint for changing the user's password.
    - Validates using PasswordChangeForm (via CustomPasswordChangeForm).
    - Forces English messages regardless of site locale.
    - Returns JSON with success or field-level errors (inline-friendly for the modal).
    """
    with translation.override('en'):
        form = CustomPasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            form.save()
            update_session_auth_hash(request, form.user)  # keep user logged in
            return JsonResponse({"ok": True, "message": "Password changed successfully."})

        # Serialize errors safely:
        # - form.errors is an ErrorDict (no .getlist); use get_json_data() for clean messages/codes.
        # - Do NOT HTML-escape here; the frontend already escapes when rendering.
        raw = form.errors.get_json_data(escape_html=False)
        errors = {k: [item["message"] for item in v] for k, v in raw.items() if k != "__all__"}
        non_field = [item["message"] for item in raw.get("__all__", [])]

        return JsonResponse(
            {"ok": False, "errors": errors, "non_field_errors": non_field},
            status=400
        )
