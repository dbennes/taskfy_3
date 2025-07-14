from django.urls import path
from django.urls.conf import include
from . import views

from .views import (
    DisciplineListView,
    AreaListView,
    WorkingCodeListView,
    SystemListView,
)

urlpatterns = [
    path('', views.index, name='index'),
    path('login/', views.login, name='login'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('jobcards_list/', views.jobcards_list, name='jobcards_list'),
    
    # Rota para criar um novo JobCard
    path('create_jobcard', views.create_jobcard, name='create_jobcard'),
    
    # Rota para editar um JobCard existente
    path('edit/<str:jobcard_id>/', views.edit_jobcard, name='edit_jobcard'),
    
    path('allocate/<str:jobcard_id>/', views.allocate_resources, name='allocate_resources'),
    path('pdf/<str:jobcard_id>/', views.generate_pdf, name='generate_pdf'),
    path('jobcard/<str:jobcard_id>/pdf/', views.generate_pdf, name='generate_pdf'),
    
    path('jobcards-overview/', views.jobcards_overview, name='jobcards_overview'),
    path('materials/', views.materials_list, name='materials_list'),
    path('manpower/', views.manpower_list, name='manpower_list'),
    path('tools/', views.tools_list, name='tools_list'),
    path('engineering/', views.engineering_list, name='engineering_list'),
    path('tasks/', views.task_list, name='task_list'),
    
    # TELAS DE ALOCAÇÕES  
    path('allocated-manpower/', views.allocated_manpower_list, name='allocated_manpower_list'),
    path('allocated-materials/', views.allocated_material_list, name='allocated_material_list'),
    path('allocated-tools/', views.allocated_tool_list, name='allocated_tool_list'),
    path('allocated-engineering/', views.allocated_engineering_list, name='allocated_engineering_list'),
    path('allocated-tasks/', views.allocated_task_list, name='allocated_task_list'),
    
    # IMPORTAÇÕES
    path('import_materials/', views.import_materials, name='import_materials'),
    path('import_jobcard/', views.import_jobcard, name='import_jobcard'),
    path('import_manpower/', views.import_manpower, name='import_manpower'),
    path('import_toolsbase/', views.import_toolsbase, name='import_toolsbase'),
    path('import_engineering/', views.import_engineering, name='import_engineering'),
    path('import_taskbase/', views.import_taskbase, name='import_taskbase'),
     
    # REFERENCES
    path('disciplines/', DisciplineListView.as_view(), name='disciplines_list'),
    path('areas/', AreaListView.as_view(), name='areas_list'),
    path('workingcodes/', WorkingCodeListView.as_view(), name='workingcodes_list'),
    path('systems/', SystemListView.as_view(), name='systems_list'),
    
    #DELETES
    path('disciplines/delete/<int:pk>/', views.delete_discipline, name='delete_discipline'),
    path('systems/delete/<int:pk>/', views.delete_system, name='delete_system'),
    path('workingcodes/delete/<int:pk>/', views.delete_working_code, name='delete_working_code'),
    path('areas/delete/<int:pk>/', views.delete_area, name='delete_area'),
    
    #EXPORTAÇÕES
    path('export_materials_excel/', views.export_materials_excel, name='export_materials_excel')


]