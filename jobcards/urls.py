from django.urls import path
from . import views
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from . import views_pdf_api
from . import views_schedule, views_documents, views_allocated_manpower, views_sync
from . import views_downloads_jobcards

# IMPORTANTE: use apenas UMA definição para cada rota de API
urlpatterns = [
    path('', views.index, name='index'),
    path('login/', views.login, name='login'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('jobcards_list/', views.jobcards_list, name='jobcards_list'),

    # CRUD/HTML
    path('create_jobcard', views.create_jobcard, name='create_jobcard'),
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

    # Telas de alocação
    
    path('allocated-materials/', views.allocated_material_list, name='allocated_material_list'),
    path('allocated-tools/', views.allocated_tool_list, name='allocated_tool_list'),
    path('allocated-engineering/', views.allocated_engineering_list, name='allocated_engineering_list'),
    path('allocated-tasks/', views.allocated_task_list, name='allocated_task_list'),

    # Importações
    path('import_materials/', views.import_materials, name='import_materials'),
    path('import_jobcard/', views.import_jobcard, name='import_jobcard'),
    path('import_manpower/', views.import_manpower, name='import_manpower'),
    path('import_toolsbase/', views.import_toolsbase, name='import_toolsbase'),
    path('import_engineering/', views.import_engineering, name='import_engineering'),
    path('import_taskbase/', views.import_taskbase, name='import_taskbase'),

    # References
    path('disciplines/', views.DisciplineListView.as_view(), name='disciplines_list'),
    path('areas/', views.AreaListView.as_view(), name='areas_list'),
    path('workingcodes/', views.WorkingCodeListView.as_view(), name='workingcodes_list'),
    path('systems/', views.SystemListView.as_view(), name='systems_list'),

    # Deletes
    path('disciplines/delete/<int:pk>/', views.delete_discipline, name='delete_discipline'),
    path('systems/delete/<int:pk>/', views.delete_system, name='delete_system'),
    path('workingcodes/delete/<int:pk>/', views.delete_working_code, name='delete_working_code'),
    path('areas/delete/<int:pk>/', views.delete_area, name='delete_area'),

    # Exportações
    path('export_materials_excel/', views.export_materials_excel, name='export_materials_excel'),
    path('manpower/export/', views.export_manpower_excel, name='export_manpower_excel'),
    path('toolsbase/export/', views.export_toolsbase_excel, name='export_toolsbase_excel'),
    path('jobcards-export-excel/', views.export_jobcard_excel, name='export_jobcard_excel'),

    # Reports
    path('jobcards/tam/', views.jobcards_tam, name='jobcards_tam'),

    # Avançar jobcards (TELA HTML principal)
    path('jobcard_progress/', views.jobcard_progress, name='jobcard_progress'),

    # Impedimentos
    path('impediments/create/', views.create_impediment, name='create_impediment'),
    path('impediments/', views.impediments_list, name='impediments_list'),
    path('impediments/update/', views.impediment_update, name='impediment_update'),
    path('impediments/delete/', views.impediment_delete, name='impediment_delete'),

    # PMTO
    path('engineering/pmto/', views.pmto_list, name='pmto_list'),
    path('engineering/pmto/import/', views.import_pmto, name='import_pmto'),
    path('engineering/pmto/export/', views.export_pmto_excel, name='export_pmto_excel'),

    # MR
    path('materialRequest/', views.mr_list, name='mr_list'),
    path('mr/import/', views.import_mr, name='import_mr'),
    path('mr/export/', views.export_mr_excel, name='export_mr_excel'),

    # Procurement
    path('procurement/', views.procurement_list, name='procurement_list'),
    path('procurement/import/', views.import_procurement, name='import_procurement'),
    path('procurement/export/', views.export_procurement_excel, name='export_procurement_excel'),
    path('procurement/po-tracking/', views.po_tracking, name='po_tracking'),
    path('procurement/po-tracking/update-status/', views.po_tracking_update_status, name='po_tracking_update_status'),
    path('procurement/po-tracking/detail/<int:po_id>/', views.po_tracking_detail, name='po_tracking_detail'),
    path('procurement/po-tracking/search/', views.po_tracking_search, name='po_tracking_search'),

    # Warehouse / RFID
    path('warehouse/warehouse_rfid/', views.warehouse_rfid, name='warehouse_rfid'),
    path('kanban/', views.warehouse_kanban, name='warehouse_kanban'),
    path('kanban/update-status/', views.update_warehouse_status, name='update_warehouse_status'),
    path('kanban/detail/<int:pk>/', views.warehouse_detail, name='warehouse_detail'),
    path('kanban/receive/<int:pk>/', views.warehouse_receive, name='warehouse_receive'),
    path('warehouse/receive-form/<int:pk>/', views.warehouse_receive_form, name='warehouse_receive_form'),
    path('procurement/po-tracking/search/', views.po_tracking_search, name='po_tracking_search'),
    path('warehouse-logistics/', views.warehouse_logistics, name='warehouse_logistics'),
    path('warehouse-logistics/update-area/', views.warehouse_logistics_update_area, name='warehouse_logistics_update_area'),
    path('warehouse-logistics/search/', views.warehouse_logistics_search, name='warehouse_logistics_search'),
    path('warehouse-logistics/export-excel/', views.export_warehouse_pieces_excel, name='export_warehouse_pieces_excel'),

    # Jobcard planning
    path('jobcards/planning/', views.jobcards_planning_list, name='jobcards_planning_list'),
    path('jobcards/<str:jobcard_id>/advance/', views.change_jobcard_status, name='change_jobcard_status'),

    path('rfid/modal/<int:stock_id>/', views.rfid_modal, name='rfid_modal'),
    path('rfid/add/<int:stock_id>/', views.rfid_add, name='rfid_add'),

    # Tokens
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # -------- API (FBVs DRF + JWT) --------
    # Coloque a lista ANTES das rotas com <str:...>
    path('api/jobcard/list/', views.api_jobcard_list, name='api_jobcard_list'),
    path('api/jobcard/advance/<str:jobcard_number>/', views.api_jobcard_advance, name='api_jobcard_advance'),
    path('api/jobcard/<str:jobcard_number>/', views.api_jobcard_detail, name='api_jobcard_detail'),
    
    # Endpoint para PDFs de Jobcards
    path('api/jobcards/pdfs/', views.jobcard_pdfs, name='jobcard_pdfs'),

    # Outros endpoints auxiliares
    path('api/revisoes_ultimas/', views.api_revisoes_ultimas, name='api_revisoes_ultimas'),
    path('jobcard/<str:jobcard_id>/allocation/<int:task_order>/', views.save_allocation, name='save_allocation'),

    # Atualização do Estoque 
    path("api/rfid/check/", views.check_rfid, name="check_rfid"),
    path("api/rfid/all/", views.api_rfid_all, name="api_rfid_all"),
    path("api/rfid/update-location/", views.update_location, name="update_location"),


    # -------- API Impediments --------
    path('api/impediments/', views.api_list_impediments, name='api_list_impediments'),
    path('api/impediments/create/', views.api_create_impediment, name='api_create_impediment'),
    path('api/impediments/<int:pk>/', views.api_impediment_detail, name='api_impediment_detail'),
    path('api/impediments/<int:pk>/update/', views.api_update_impediment, name='api_update_impediment'),
    path('api/impediments/<int:pk>/delete/', views.api_delete_impediment, name='api_delete_impediment'),

    path("api/jobcard/<str:jobcard_number>/manpowers/", views.api_jobcard_manpowers, name="api_jobcard_manpowers"),
    path("api/dfr/<str:jobcard_number>/close/", views.api_dfr_close, name="api_dfr_close"),
    
    #deleta imagens do 3D
    path('jobcard/delete_image/', views.delete_jobcard_image, name='delete_jobcard_image'),
    path ('jobcard/upload_documents/', views.upload_documents, name='upload_documents'),



    path('ajax_tools_for_manpowers/', views.ajax_tools_for_manpowers, name='ajax_tools_for_manpowers'),

    # -------- MODIFICAR JOBCARDS -------- #

    # ENTRADA (sem parâmetro) → tela para digitar a JobCard
    path("jobcards/modify/", views.modify_jobcard_entry, name="modify_jobcard_entry"),
    path("jobcards/<str:jobcard>/edit/patch/", views.modify_jobcard_excel_patch, name="modify_jobcard_excel_patch"),
    
    path('jobcards/modify/<str:jobcard>/', views.modify_jobcard_edit, name='modify_jobcard_edit'),  # se você já tem essa view, mantenha
    path('jobcards/import/modify/', views.import_jobcard_modify, name='import_jobcard_modify'),
    path('jobcards/export/', views.export_jobcard_excel, name='export_jobcard_excel'),
    path('jobcards/template/', views.download_jobcard_modify_template, name='download_jobcard_template'),


    # AQUI EU GERO OS PDFs EM BATCH USANDO RQ (Redis Queue) - APLICAÇÃO DE FILA DE TAREFAS E EMISSAO DE PDF ASSÍNCRONA

    path("api/pdf/run/batch",    views.api_regenerate_jobcards_pdfs, name="api_regenerate_jobcards_pdfs"),

    path('api/pdf/run/start',    views_pdf_api.api_pdf_run_start,    name='api_pdf_run_start'),
    path('api/pdf/run/progress', views_pdf_api.api_pdf_run_progress, name='api_pdf_run_progress'),
    path('api/pdf/run/stop',     views_pdf_api.api_pdf_run_stop,     name='api_pdf_run_stop'),
    path("api/pdf/run/log",      views_pdf_api.api_pdf_run_log,      name="api_pdf_run_log"),


    # --- CRONOGRAMA / P6 ---

    path('schedule/gantt/',     views_schedule.schedule_gantt,   name='schedule_gantt'),
    path('schedule/upload/',    views_schedule.schedule_upload,  name='schedule_upload'),
    path('schedule/api/',       views_schedule.schedule_api,     name='schedule_api'),
    path('schedule/template/',  views_schedule.schedule_template, name='schedule_template'),  # NOVA
    path("schedule/export-excel/", views_schedule.schedule_export_excel, name="schedule_export_excel"),

    path("engineering/docs/revisions/", views_documents.docs_revision_review, name="docs_revision_review"),
    path("engineering/docs/revisions/accept/<int:eng_id>/", views_documents.accept_doc_revision, name="accept_doc_revision"),
    path("engineering/docs/revisions/accept-bulk/", views_documents.accept_doc_revision_bulk, name="accept_doc_revision_bulk"),
    path('api/docs/to-accept-count/', views_documents.api_docs_to_accept_count, name='api_docs_to_accept_count'),


    # ALOCAÇÃO DE MAO DE OBRA AJUSTADA
    path('allocated/manpower/', views_allocated_manpower.allocated_manpower_list, name='allocated_manpower_list'),
    path('allocated/manpower/data/', views_allocated_manpower.allocated_manpower_table_data, name='allocated_manpower_table_data'),
    path('allocated/manpower/import/', views_allocated_manpower.import_allocated_manpower, name='import_allocated_manpower'),
    path('allocated/manpower/export/', views_allocated_manpower.export_allocated_manpower_csv, name='export_allocated_manpower_csv'),
    path("allocated/manpower/template/", views_allocated_manpower.allocated_manpower_template, name="allocated_manpower_template"),

    path("allocated/manpower/export/xlsx/", views_allocated_manpower.export_allocated_manpower_xlsx, name="export_allocated_manpower_xlsx"),

    # BAIXAR JOBCARDS EM PDF EM LOTE (ZIP) 
    path("jobcards/downloads/", views_downloads_jobcards.page, name="download_jobcards_page"),
    path("jobcards/downloads/template/", views_downloads_jobcards.download_template, name="jobcards_download_template"),
    path("jobcards/downloads/by-list/", views_downloads_jobcards.download_jobcards_by_list, name="download_jobcards_by_list"),
    path("jobcards/downloads/all/", views_downloads_jobcards.download_all_jobcards, name="download_all_jobcards"),

    path('jobcards/sync-all/', views_sync.api_sync_allocations_all, name='jobcard_sync_allocations_all'),
    path('jobcards/<str:job_card_number>/sync/', views_sync.jobcard_sync_allocations, name='jobcard_sync_allocations'),

    
]


