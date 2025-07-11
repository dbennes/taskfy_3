from django import forms
from .models import Discipline, Area, WorkingCode, System


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

