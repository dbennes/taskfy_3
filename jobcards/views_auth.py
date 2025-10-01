# jobcards/views_auth.py
from django.contrib.auth.views import PasswordChangeView
from django.urls import reverse_lazy

class TaskfyPasswordChangeView(PasswordChangeView):
    success_url = reverse_lazy("password_change_done")

    def form_valid(self, form):
        response = super().form_valid(form)
        flag = getattr(self.request.user, "securityflag", None)
        if flag and flag.must_change_password:
            flag.must_change_password = False
            flag.save(update_fields=["must_change_password"])
        return response
