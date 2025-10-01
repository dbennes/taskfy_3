# jobcards/admin.py
from django.contrib import admin, messages
from django.utils import timezone
from django.utils.html import format_html
from django.db.models import Count
from django.http import HttpResponse
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.conf import settings
import csv, json

from .models import (
    JobCard, ManpowerBase, ToolsBase, EngineeringBase, TaskBase, MaterialBase,
    AllocatedManpower, AllocatedMaterial, AllocatedTool, AllocatedEngineering, AllocatedTask,
    Discipline, Area, WorkingCode, System, Impediments, PMTOBase, MRBase, ProcurementBase,
    DocumentoControle, DocumentoRevisaoAlterada, WarehouseStock, WarehousePiece, DailyFieldReport
)

from django.contrib import admin, messages
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from .utils.account_email import send_profile_change_password_email

User = get_user_model()

# ===============================
# Branding e ajustes globais
# ===============================
admin.site.site_header  = "Taskfy — Administração"
admin.site.site_title   = "Taskfy Admin"
admin.site.index_title  = "Painel de Controle"

# ===============================
# Mixins utilitários
# ===============================
class ExportActionsMixin:
    """Ações genéricas de exportação para qualquer ModelAdmin."""
    @admin.action(description="Exportar selecionados como CSV")
    def export_as_csv(self, request, queryset):
        fields = [f.name for f in queryset.model._meta.fields]
        response = HttpResponse(content_type="text/csv")
        filename = f"{queryset.model._meta.model_name}_{timezone.now().strftime('%Y%m%d_%H%M%S')}.csv"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        writer = csv.writer(response)
        writer.writerow(fields)
        for obj in queryset:
            row = [str(getattr(obj, f, "")) for f in fields]
            writer.writerow(row)
        return response

    @admin.action(description="Exportar selecionados como JSON")
    def export_as_json(self, request, queryset):
        fields = [f.name for f in queryset.model._meta.fields]
        data = [{f: getattr(obj, f, None) for f in fields} for obj in queryset]
        response = HttpResponse(content_type="application/json")
        filename = f"{queryset.model._meta.model_name}_{timezone.now().strftime('%Y%m%d_%H%M%S')}.json"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        response.write(json.dumps(data, ensure_ascii=False, indent=2, default=str))
        return response


class SafeBasicAdmin(ExportActionsMixin, admin.ModelAdmin):
    """Admin básico seguro: não assume campos além de 'id' e __str__."""
    def obj_display(self, obj):
        return str(obj)
    obj_display.short_description = "Registro"
    list_display = ("obj_display", "id")
    search_fields = ("id", )
    list_per_page = 25
    save_on_top = True
    actions = ("export_as_csv", "export_as_json")


# ===============================
# Impediments
# ===============================
@admin.register(Impediments)
class ImpedimentsAdmin(ExportActionsMixin, admin.ModelAdmin):
    list_display = ("jobcard_number", "created_by", "created_at",
                    "scaffold", "material", "engineering", "notes_preview")
    list_display_links = ("jobcard_number",)
    list_editable = ("scaffold", "material", "engineering")
    search_fields = ("jobcard_number", "created_by", "notes")
    list_filter = ("scaffold", "material", "engineering",
                   ("created_at", admin.DateFieldListFilter))
    date_hierarchy = "created_at"
    ordering = ("-created_at",)
    list_per_page = 25
    save_on_top = True
    actions = ("export_as_csv", "export_as_json")

    def notes_preview(self, obj):
        txt = (obj.notes or "")
        return "-" if not txt else (txt if len(txt) <= 80 else txt[:80] + "...")
    notes_preview.short_description = "Notes"


# ===============================
# JobCard
# ===============================
@admin.register(JobCard)
class JobCardAdmin(ExportActionsMixin, admin.ModelAdmin):
    list_display = ("job_card_number", "discipline", "working_code", "system",
                    "start", "finish", "jobcard_status")
    search_fields = ("job_card_number", "tag", "working_code",
                     "working_code_description", "system", "subsystem")
    list_filter = ("discipline", "system", "jobcard_status",
                   ("start", admin.DateFieldListFilter), ("finish", admin.DateFieldListFilter))
    date_hierarchy = "start"
    ordering = ("job_card_number",)
    list_per_page = 25
    save_on_top = True
    actions = ("export_as_csv", "export_as_json")


# ===============================
# DailyFieldReport (DFR)
# ===============================
@admin.register(DailyFieldReport)
class DailyFieldReportAdmin(ExportActionsMixin, admin.ModelAdmin):
    list_display = ("dfr_number", "line_seq", "jobcard_number", "discipline",
                    "working_code", "report_date", "total_lines", "total_hours",
                    "created_by", "created_at")
    search_fields = ("dfr_number", "jobcard_number", "discipline", "working_code", "created_by")
    list_filter = (("report_date", admin.DateFieldListFilter),
                   ("created_at", admin.DateFieldListFilter), "discipline", "working_code")
    date_hierarchy = "report_date"
    ordering = ("-report_date", "dfr_number", "line_seq")
    list_per_page = 30
    save_on_top = True
    readonly_fields = ("created_at", "snapshot_pretty")
    actions = ("export_as_csv", "export_as_json", "recount_total_lines")

    fieldsets = (
        ("Identificação", {
            "fields": ("dfr_number", "line_seq", "report_date", "jobcard_number", "discipline", "working_code")
        }),
        ("Totais", {
            "fields": ("total_lines", "total_hours")
        }),
        ("Metadados", {
            "fields": ("created_by", "created_at", "notes", "snapshot_pretty")
        }),
    )

    def snapshot_pretty(self, obj):
        data = getattr(obj, "snapshot", None)
        if not data:
            return "-"
        try:
            pretty = json.dumps(data, ensure_ascii=False, indent=2)
        except Exception:
            pretty = str(data)
        return format_html("<pre style='max-height:300px; overflow:auto; padding:8px; background:#f7f7f7;'>{}</pre>", pretty)
    snapshot_pretty.short_description = "Snapshot (visualização)"

    @admin.action(description="Recalcular 'total_lines' por DFR Number")
    def recount_total_lines(self, request, queryset):
        dfrs = list(queryset.values_list("dfr_number", flat=True).distinct())
        if not dfrs:
            self.message_user(request, "Nenhum DFR selecionado.", level=messages.WARNING)
            return
        count_map = (DailyFieldReport.objects
                     .filter(dfr_number__in=dfrs)
                     .values("dfr_number")
                     .annotate(total=Count("id")))
        updated = 0
        for dfr_number, total in {c["dfr_number"]: c["total"] for c in count_map}.items():
            updated += DailyFieldReport.objects.filter(dfr_number=dfr_number).update(total_lines=total)
        self.message_user(request, f"Recalcular finalizado. Registros atualizados: {updated}.", level=messages.SUCCESS)


# ===============================
# Cadastros básicos / bases
# ===============================
@admin.register(Discipline)
class DisciplineAdmin(SafeBasicAdmin):
    pass

@admin.register(Area)
class AreaAdmin(SafeBasicAdmin):
    pass

@admin.register(WorkingCode)
class WorkingCodeAdmin(SafeBasicAdmin):
    search_fields = ("id", )  # ajuste para ('code','description') se existirem

@admin.register(System)
class SystemAdmin(SafeBasicAdmin):
    pass


# ===============================
# Bases de recursos
# ===============================
@admin.register(ManpowerBase)
class ManpowerBaseAdmin(SafeBasicAdmin):
    pass

@admin.register(ToolsBase)
class ToolsBaseAdmin(SafeBasicAdmin):
    pass

@admin.register(EngineeringBase)
class EngineeringBaseAdmin(SafeBasicAdmin):
    pass

@admin.register(TaskBase)
class TaskBaseAdmin(SafeBasicAdmin):
    pass

@admin.register(MaterialBase)
class MaterialBaseAdmin(SafeBasicAdmin):
    pass


# ===============================
# Alocações
# ===============================
@admin.register(AllocatedManpower)
class AllocatedManpowerAdmin(SafeBasicAdmin):
    pass

@admin.register(AllocatedMaterial)
class AllocatedMaterialAdmin(SafeBasicAdmin):
    pass

@admin.register(AllocatedTool)
class AllocatedToolAdmin(SafeBasicAdmin):
    pass

@admin.register(AllocatedEngineering)
class AllocatedEngineeringAdmin(SafeBasicAdmin):
    pass

@admin.register(AllocatedTask)
class AllocatedTaskAdmin(SafeBasicAdmin):
    pass


# ===============================
# Documentos
# ===============================
@admin.register(DocumentoControle)
class DocumentoControleAdmin(SafeBasicAdmin):
    pass

@admin.register(DocumentoRevisaoAlterada)
class DocumentoRevisaoAlteradaAdmin(SafeBasicAdmin):
    pass


# ===============================
# Compras / Suprimentos
# ===============================
@admin.register(PMTOBase)
class PMTOBaseAdmin(SafeBasicAdmin):
    pass

@admin.register(MRBase)
class MRBaseAdmin(SafeBasicAdmin):
    pass

@admin.register(ProcurementBase)
class ProcurementBaseAdmin(SafeBasicAdmin):
    pass


# ===============================
# Almoxarifado
# ===============================
@admin.register(WarehouseStock)
class WarehouseStockAdmin(SafeBasicAdmin):
    pass

@admin.register(WarehousePiece)
class WarehousePieceAdmin(SafeBasicAdmin):
    pass


# ===============================
# Usuários — ação de reenviar boas-vindas
# ===============================
@admin.action(description="Enviar e-mail de troca de senha (Profile)")
def send_profile_change_password(modeladmin, request, queryset):
    ok, fail = 0, 0
    for u in queryset:
        sent, detail = send_profile_change_password_email(u)
        if sent:
            ok += 1
        else:
            fail += 1
            messages.warning(request, f"{u.username}: {detail}")
    if ok:
        messages.success(request, f"E-mails enviados: {ok}")
    if fail:
        messages.error(request, f"Falhas: {fail}")

class UserAdmin(DjangoUserAdmin):
    actions = [send_profile_change_password]

try:
    admin.site.unregister(User)
except admin.sites.NotRegistered:
    pass
admin.site.register(User, UserAdmin)