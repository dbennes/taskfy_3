from django import forms
from .models import Discipline, Area, WorkingCode, System, Impediments, JobCard


class DisciplineForm(forms.ModelForm):
    class Meta:
        model = Discipline
        fields = ['code', 'name']
        widgets = {
            'code': forms.TextInput(attrs={
                'class': 'form-control',
                'style': 'border:1px solid #ced4da; border-radius:6px; padding:6px 12px; background-color:#f9f9f9; font-size:14px; width:100%; transition:all 0.3s ease-in-out;',
                'placeholder': 'Enter code'
            }),
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'style': 'border:1px solid #ced4da; border-radius:6px; padding:6px 12px; background-color:#f9f9f9; font-size:14px; width:100%; transition:all 0.3s ease-in-out;',
                'placeholder': 'Enter name'
            }),
        }

class AreaForm(forms.ModelForm):
    class Meta:
        model = Area
        fields = ['area_code', 'code', 'location', 'level']
        widgets = {
            'area_code': forms.TextInput(attrs={
                'class': 'form-control',
                'style': 'border:1px solid #ced4da; border-radius:6px; padding:6px 12px; background-color:#f9f9f9; font-size:14px; width:100%; transition:all 0.3s ease-in-out;',
                'placeholder': 'Enter area code'
            }),
            'code': forms.TextInput(attrs={
                'class': 'form-control',
                'style': 'border:1px solid #ced4da; border-radius:6px; padding:6px 12px; background-color:#f9f9f9; font-size:14px; width:100%; transition:all 0.3s ease-in-out;',
                'placeholder': 'Enter code'
            }),
            'location': forms.TextInput(attrs={
                'class': 'form-control',
                'style': 'border:1px solid #ced4da; border-radius:6px; padding:6px 12px; background-color:#f9f9f9; font-size:14px; width:100%; transition:all 0.3s ease-in-out;',
                'placeholder': 'Enter location'
            }),
            'level': forms.TextInput(attrs={
                'class': 'form-control',
                'style': 'border:1px solid #ced4da; border-radius:6px; padding:6px 12px; background-color:#f9f9f9; font-size:14px; width:100%; transition:all 0.3s ease-in-out;',
                'placeholder': 'Enter level'
            }),
        }

class WorkingCodeForm(forms.ModelForm):
    class Meta:
        model = WorkingCode
        fields = ['code', 'description']
        widgets = {
            'code': forms.TextInput(attrs={
                'class': 'form-control',
                'style': 'border:1px solid #ced4da; border-radius:6px; padding:6px 12px; background-color:#f9f9f9; font-size:14px; width:100%; transition:all 0.3s ease-in-out;',
                'placeholder': 'Enter working code'
            }),
            'description': forms.TextInput(attrs={
                'class': 'form-control',
                'style': 'border:1px solid #ced4da; border-radius:6px; padding:6px 12px; background-color:#f9f9f9; font-size:14px; width:100%; transition:all 0.3s ease-in-out;',
                'placeholder': 'Enter description'
            }),
        }

class SystemForm(forms.ModelForm):
    class Meta:
        model = System
        fields = ['system_code', 'subsystem_code']
        widgets = {
            'system_code': forms.TextInput(attrs={
                'class': 'form-control',
                'style': 'border:1px solid #ced4da; border-radius:6px; padding:6px 12px; background-color:#f9f9f9; font-size:14px; width:100%; transition:all 0.3s ease-in-out;',
                'placeholder': 'Enter system code'
            }),
            'subsystem_code': forms.TextInput(attrs={
                'class': 'form-control',
                'style': 'border:1px solid #ced4da; border-radius:6px; padding:6px 12px; background-color:#f9f9f9; font-size:14px; width:100%; transition:all 0.3s ease-in-out;',
                'placeholder': 'Enter subsystem code'
            }),
        }

class ImpedimentsForm(forms.ModelForm):
    class Meta:
        model = Impediments
        fields = [
            'jobcard_number', 'scaffold', 'material', 'engineering', 'mainpower',
            'tools', 'access', 'pwt', 'other', 'origin_shell', 'origin_utc', 'notes'
        ]
        widgets = {
            'jobcard_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter JobCard Number',
                'id': 'id_jobcard_number'
            }),
            'scaffold': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
                'id': 'id_scaffold'
            }),
            'material': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
                'id': 'id_material'
            }),
            'engineering': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
                'id': 'id_engineering'
            }),
            'other': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Other impediments...',
                'style': 'width: 450px;',
                'id': 'id_other'
            }),
            'origin_shell': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
                'id': 'id_origin_shell'
            }),
            'origin_utc': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
                'id': 'id_origin_utc'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 1,
                'placeholder': 'Additional notes...',
                'id': 'id_notes'
            }),
        }

class JobCardImageForm(forms.ModelForm):
    class Meta:
        model = JobCard
        fields = ['image_1', 'image_2', 'image_3', 'image_4']





# --- JobCardForm para edição + lista de campos liberados ---

from django import forms
from .models import JobCard

# Campos que poderão ser editados no formulário e também via patch Excel/CSV
EDITABLE_FIELDS = [
    "activity_id", "start", "finish",
    "system", "subsystem", "working_code",
    "tag", "working_code_description",
    "rev", "jobcard_status", "job_card_description",
    "total_weight", "unit", "total_duration_hs",
    "indice_kpi", "total_man_hours", "prepared_by",
    "date_prepared", "approved_br", "date_approved",
    "hot_work_required", "status", "comments",
]

class JobCardForm(forms.ModelForm):
    # Exibição somente leitura do número da JobCard no topo do form
    job_card_number_display = forms.CharField(
        label="JobCard Number",
        required=False,
        disabled=True
    )

    class Meta:
        model = JobCard
        fields = EDITABLE_FIELDS
        widgets = {
            "start": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "finish": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "date_prepared": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "date_approved": forms.DateInput(attrs={"type": "date", "class": "form-control"}),

            "working_code_description": forms.Textarea(attrs={"rows": 2, "class": "form-control"}),
            "job_card_description": forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
            "comments": forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        instance = kwargs.get("instance")
        super().__init__(*args, **kwargs)

        # adiciona classe bootstrap aos demais inputs
        for name, field in self.fields.items():
            if not isinstance(field.widget, (forms.Textarea, forms.DateInput)):
                css = field.widget.attrs.get("class", "")
                field.widget.attrs["class"] = (css + " form-control").strip()

        # Preenche o campo somente-leitura com o número da JobCard
        if instance:
            self.fields["job_card_number_display"].initial = instance.job_card_number


class ScheduleImportForm(forms.Form):
    file = forms.FileField(label="Template (CSV / XLSX / XML)")
    mode = forms.ChoiceField(
        choices=[("auto", "Auto-detect"), ("csv", "CSV"), ("xml", "Primavera XML"), ("excel", "Excel (.xlsx/.xlsm)")],
        initial="auto"
    )
    update_jobcards = forms.BooleanField(
        required=False, initial=True,
        label="Atualizar start/finish dos JobCards com mesmo Activity ID"
    )