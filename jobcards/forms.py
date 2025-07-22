from django import forms
from .models import Discipline, Area, WorkingCode, System, Impediments


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