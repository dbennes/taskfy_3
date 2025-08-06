from django.urls import path
from django.urls.conf import include
from . import views
from jobcards.views import api_revisoes_ultimas

from .views import (
    DisciplineListView,
    AreaListView,
    WorkingCodeListView,
    SystemListView, 
    jobcard_progress, 
    create_impediment,
    export_jobcard_excel
    

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
    path('export_materials_excel/', views.export_materials_excel, name='export_materials_excel'),
    path('manpower/export/', views.export_manpower_excel, name='export_manpower_excel'),
    path('toolsbase/export/', views.export_toolsbase_excel, name='export_toolsbase_excel'),
    path('jobcards-export-excel/', export_jobcard_excel, name='export_jobcard_excel'),

    #REPORTS
    path('jobcards/tam/', views.jobcards_tam, name='jobcards_tam'),

    #AVANÇAR JOBCARDS
    path('jobcard_progress/', views.jobcard_progress, name='jobcard_progress'),  # tela principal
    path('api/jobcard/<str:jobcard_number>/', views.api_jobcard_detail, name='api_jobcard_detail'),
    path('api/jobcard/advance/<str:jobcard_number>/', views.api_jobcard_advance, name='api_jobcard_advance'),

    #IMPEDIMENTOS
    path('impediments/create/', create_impediment, name='create_impediment'),
    path('impediments/', views.impediments_list, name='impediments_list'),
    path('impediments/update/', views.impediment_update, name='impediment_update'),
    path('impediments/delete/', views.impediment_delete, name='impediment_delete'),
    
    # PMTO Base
    path('engineering/pmto/', views.pmto_list, name='pmto_list'),
    path('engineering/pmto/import/', views.import_pmto, name='import_pmto'),
    path('engineering/pmto/export/', views.export_pmto_excel, name='export_pmto_excel'),
    
    # MR Base
    path('materialRequest/', views.mr_list, name='mr_list'),
    path('mr/import/', views.import_mr, name='import_mr'),
    path('mr/export/', views.export_mr_excel, name='export_mr_excel'),
    
    # PROCUREMENT Base
    path('procurement/', views.procurement_list, name='procurement_list'),
    path('procurement/import/', views.import_procurement, name='import_procurement'),
    path('procurement/export/', views.export_procurement_excel, name='export_procurement_excel'),
    path('procurement/po-tracking/', views.po_tracking, name='po_tracking'),
    path('procurement/po-tracking/update-status/', views.po_tracking_update_status, name='po_tracking_update_status'),  # AJAX para atualizar status
    path('procurement/po-tracking/detail/<int:po_id>/', views.po_tracking_detail, name='po_tracking_detail'), # Detalhe modal
   
    # NOTIFICAÇÕES
    path('api/revisoes_ultimas/', api_revisoes_ultimas, name='api_revisoes_ultimas'),
    path('jobcard/<str:jobcard_id>/allocation/<int:task_order>/', views.save_allocation, name='save_allocation'),
    
    # CONTROLE DE ESTOQUE
    path('kanban/', views.warehouse_kanban, name='warehouse_kanban'),
    path('kanban/update-status/', views.update_warehouse_status, name='update_warehouse_status'),
    path('kanban/detail/<int:pk>/', views.warehouse_detail, name='warehouse_detail'),
    path('kanban/receive/<int:pk>/', views.warehouse_receive, name='warehouse_receive'),
    # Nova rota para renderizar o formulário no modal
    path('warehouse/receive-form/<int:pk>/', views.warehouse_receive_form, name='warehouse_receive_form'),
    path('procurement/po-tracking/search/', views.po_tracking_search, name='po_tracking_search'),
    
    path('warehouse/warehouse_rfid/', views.warehouse_rfid, name='warehouse_rfid'),
    path('rfid/modal/<int:stock_id>/', views.rfid_modal, name='rfid_modal'),
    path('rfid/add/<int:stock_id>/', views.rfid_add, name='rfid_add'),
    
    # WAREHOUSE LOGISTIC
    path('warehouse-logistics/', views.warehouse_logistics, name='warehouse_logistics'),
    path('warehouse-logistics/update-area/', views.warehouse_logistics_update_area, name='warehouse_logistics_update_area'),
    path('warehouse-logistics/search/', views.warehouse_logistics_search, name='warehouse_logistics_search'),
    path('warehouse-logistics/export-excel/', views.export_warehouse_pieces_excel, name='export_warehouse_pieces_excel'),
    
    # JOBCARD PLANNING
    path('jobcards/planning/', views.jobcards_planning_list, name='jobcards_planning_list'),
    path('jobcards/<str:jobcard_id>/advance/', views.change_jobcard_status, name='change_jobcard_status'),
]