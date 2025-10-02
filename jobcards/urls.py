from django.urls import path, include
from . import views
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from . import views_pdf_api
from . import views_schedule, views_documents, views_allocated_manpower, views_sync
from . import views_downloads_jobcards
from . import views_account
from . import views_dashboardWorkpack

from .views_auth  import TaskfyPasswordChangeView


from sistema.authz import allow_groups, cbv_group_protect
from sistema import roles

# IMPORTANTE: use apenas UMA definição para cada rota de API
urlpatterns = [
    path('', views.index, name='index'),
    path('login/', views.login, name='login'),

    # ===== HTML BÁSICO =====
    path('dashboard/',     allow_groups(views.dashboard,     roles.PLANNER, roles.PROCUREMENT, roles.WAREHOUSE, roles.VIEWER), name='dashboard'),
    path('jobcards_list/', allow_groups(views.jobcards_list, roles.PLANNER, roles.PROCUREMENT, roles.WAREHOUSE, roles.VIEWER), name='jobcards_list'),

    # ===== CRUD/HTML =====
    path('create_jobcard',                allow_groups(views.create_jobcard,     roles.PLANNER), name='create_jobcard'),
    path('edit/<str:jobcard_id>/',        allow_groups(views.edit_jobcard,       roles.PLANNER), name='edit_jobcard'),
    path('allocate/<str:jobcard_id>/',    allow_groups(views.allocate_resources, roles.PLANNER), name='allocate_resources'),
    path('pdf/<str:jobcard_id>/',         allow_groups(views.generate_pdf,       roles.PLANNER), name='generate_pdf'),
    path('jobcard/<str:jobcard_id>/pdf/', allow_groups(views.generate_pdf,       roles.PLANNER), name='generate_pdf'),
    path('jobcards-overview/',            allow_groups(views.jobcards_overview,  roles.PLANNER, roles.VIEWER), name='jobcards_overview'),
    path('materials/',   allow_groups(views.materials_list,   roles.PLANNER, roles.PROCUREMENT, roles.WAREHOUSE, roles.VIEWER), name='materials_list'),
    path('manpower/',    allow_groups(views.manpower_list,    roles.PLANNER, roles.PROCUREMENT, roles.WAREHOUSE, roles.VIEWER), name='manpower_list'),
    path('tools/',       allow_groups(views.tools_list,       roles.PLANNER, roles.PROCUREMENT, roles.WAREHOUSE, roles.VIEWER), name='tools_list'),
    path('engineering/', allow_groups(views.engineering_list, roles.PLANNER, roles.PROCUREMENT, roles.WAREHOUSE, roles.VIEWER), name='engineering_list'),
    path('tasks/',       allow_groups(views.task_list,        roles.PLANNER, roles.PROCUREMENT, roles.WAREHOUSE, roles.VIEWER), name='task_list'),

    # ===== Telas de alocação =====
    path('allocated-materials/',   allow_groups(views.allocated_material_list,    roles.PLANNER, roles.PROCUREMENT, roles.WAREHOUSE, roles.VIEWER), name='allocated_material_list'),
    path('allocated-tools/',       allow_groups(views.allocated_tool_list,        roles.PLANNER, roles.PROCUREMENT, roles.WAREHOUSE, roles.VIEWER), name='allocated_tool_list'),
    path('allocated-engineering/', allow_groups(views.allocated_engineering_list, roles.PLANNER, roles.PROCUREMENT, roles.WAREHOUSE, roles.VIEWER), name='allocated_engineering_list'),
    path('allocated-tasks/',       allow_groups(views.allocated_task_list,        roles.PLANNER, roles.PROCUREMENT, roles.WAREHOUSE, roles.VIEWER), name='allocated_task_list'),

    # ===== Importações =====
    path('import_materials/',   allow_groups(views.import_materials,   roles.PLANNER, roles.PROCUREMENT), name='import_materials'),
    path('import_jobcard/',     allow_groups(views.import_jobcard,     roles.PLANNER), name='import_jobcard'),
    path('import_manpower/',    allow_groups(views.import_manpower,    roles.PLANNER), name='import_manpower'),
    path('import_toolsbase/',   allow_groups(views.import_toolsbase,   roles.PLANNER), name='import_toolsbase'),
    path('import_engineering/', allow_groups(views.import_engineering, roles.PLANNER), name='import_engineering'),
    path('import_taskbase/',    allow_groups(views.import_taskbase,    roles.PLANNER), name='import_taskbase'),

    # ===== References (CBV) =====
    path('disciplines/',  cbv_group_protect(views.DisciplineListView,  roles.PLANNER), name='disciplines_list'),
    path('areas/',        cbv_group_protect(views.AreaListView,        roles.PLANNER), name='areas_list'),
    path('workingcodes/', cbv_group_protect(views.WorkingCodeListView, roles.PLANNER), name='workingcodes_list'),
    path('systems/',      cbv_group_protect(views.SystemListView,      roles.PLANNER), name='systems_list'),

    # ===== Deletes =====
    path('disciplines/delete/<int:pk>/',  allow_groups(views.delete_discipline,  roles.PLANNER), name='delete_discipline'),
    path('systems/delete/<int:pk>/',      allow_groups(views.delete_system,      roles.PLANNER), name='delete_system'),
    path('workingcodes/delete/<int:pk>/', allow_groups(views.delete_working_code, roles.PLANNER), name='delete_working_code'),
    path('areas/delete/<int:pk>/',        allow_groups(views.delete_area,        roles.PLANNER), name='delete_area'),

    # ===== Exportações =====
    path('export_materials_excel/', allow_groups(views.export_materials_excel, roles.PLANNER, roles.PROCUREMENT, roles.WAREHOUSE, roles.VIEWER), name='export_materials_excel'),
    path('manpower/export/',        allow_groups(views.export_manpower_excel,  roles.PLANNER, roles.PROCUREMENT, roles.WAREHOUSE, roles.VIEWER), name='export_manpower_excel'),
    path('toolsbase/export/',       allow_groups(views.export_toolsbase_excel, roles.PLANNER, roles.PROCUREMENT, roles.WAREHOUSE, roles.VIEWER), name='export_toolsbase_excel'),
    path('jobcards-export-excel/',  allow_groups(views.export_jobcard_excel,   roles.PLANNER, roles.PROCUREMENT, roles.WAREHOUSE, roles.VIEWER), name='export_jobcard_excel'),

    # ===== Reports =====
    path('jobcards/tam/', allow_groups(views.jobcards_tam, roles.PLANNER, roles.PROCUREMENT, roles.WAREHOUSE, roles.VIEWER), name='jobcards_tam'),

    # ===== Avançar jobcards (TELA HTML principal) =====
    path('jobcard_progress/', allow_groups(views.jobcard_progress, roles.PLANNER), name='jobcard_progress'),

    # ===== Impedimentos =====
    path('impediments/create/', allow_groups(views.create_impediment, roles.PLANNER), name='create_impediment'),
    path('impediments/',        allow_groups(views.impediments_list,  roles.PLANNER, roles.PROCUREMENT, roles.WAREHOUSE, roles.VIEWER), name='impediments_list'),
    path('impediments/update/', allow_groups(views.impediment_update, roles.PLANNER), name='impediment_update'),
    path('impediments/delete/', allow_groups(views.impediment_delete, roles.PLANNER), name='impediment_delete'),

    # ===== PMTO =====
    path('engineering/pmto/',        allow_groups(views.pmto_list,        roles.PLANNER, roles.PROCUREMENT, roles.WAREHOUSE, roles.VIEWER), name='pmto_list'),
    path('engineering/pmto/import/', allow_groups(views.import_pmto,      roles.PLANNER), name='import_pmto'),
    path('engineering/pmto/export/', allow_groups(views.export_pmto_excel, roles.PLANNER, roles.PROCUREMENT, roles.WAREHOUSE, roles.VIEWER), name='export_pmto_excel'),

    # ===== MR =====
    path('materialRequest/', allow_groups(views.mr_list,   roles.PLANNER, roles.PROCUREMENT, roles.WAREHOUSE, roles.VIEWER), name='mr_list'),
    path('mr/import/',       allow_groups(views.import_mr, roles.PROCUREMENT, roles.PLANNER), name='import_mr'),
    path('mr/export/',       allow_groups(views.export_mr_excel, roles.PLANNER, roles.PROCUREMENT, roles.WAREHOUSE, roles.VIEWER), name='export_mr_excel'),

    # ===== Procurement =====
    path('procurement/',                          allow_groups(views.procurement_list,        roles.PLANNER, roles.PROCUREMENT, roles.WAREHOUSE, roles.VIEWER), name='procurement_list'),
    path('procurement/import/',                   allow_groups(views.import_procurement,      roles.PROCUREMENT, roles.PLANNER), name='import_procurement'),
    path('procurement/export/',                   allow_groups(views.export_procurement_excel, roles.PLANNER, roles.PROCUREMENT, roles.WAREHOUSE, roles.VIEWER), name='export_procurement_excel'),
    path('procurement/po-tracking/',              allow_groups(views.po_tracking,             roles.PLANNER, roles.PROCUREMENT, roles.WAREHOUSE, roles.VIEWER), name='po_tracking'),
    path('procurement/po-tracking/update-status/',allow_groups(views.po_tracking_update_status, roles.PROCUREMENT, roles.PLANNER), name='po_tracking_update_status'),
    path('procurement/po-tracking/detail/<int:po_id>/', allow_groups(views.po_tracking_detail, roles.PROCUREMENT, roles.PLANNER), name='po_tracking_detail'),
    path('procurement/po-tracking/search/',       allow_groups(views.po_tracking_search,      roles.PLANNER, roles.PROCUREMENT, roles.WAREHOUSE, roles.VIEWER), name='po_tracking_search'),

    # ===== Warehouse / RFID =====
    path('warehouse/warehouse_rfid/',  allow_groups(views.warehouse_rfid,  roles.PLANNER, roles.PROCUREMENT, roles.WAREHOUSE, roles.VIEWER), name='warehouse_rfid'),
    path('kanban/',                    allow_groups(views.warehouse_kanban, roles.PLANNER, roles.PROCUREMENT, roles.WAREHOUSE, roles.VIEWER), name='warehouse_kanban'),
    path('kanban/update-status/',      allow_groups(views.update_warehouse_status, roles.WAREHOUSE, roles.PROCUREMENT, roles.PLANNER), name='update_warehouse_status'),
    path('kanban/detail/<int:pk>/',    allow_groups(views.warehouse_detail, roles.WAREHOUSE, roles.PROCUREMENT, roles.PLANNER), name='warehouse_detail'),
    path('kanban/receive/<int:pk>/',   allow_groups(views.warehouse_receive, roles.WAREHOUSE, roles.PROCUREMENT, roles.PLANNER), name='warehouse_receive'),
    path('warehouse/receive-form/<int:pk>/', allow_groups(views.warehouse_receive_form, roles.WAREHOUSE, roles.PROCUREMENT, roles.PLANNER), name='warehouse_receive_form'),
    path('procurement/po-tracking/search/', allow_groups(views.po_tracking_search, roles.PLANNER, roles.PROCUREMENT, roles.WAREHOUSE, roles.VIEWER), name='po_tracking_search'),  # (duplicada por você; mantida)
    
    path('warehouse-logistics/',              allow_groups(views.warehouse_logistics, roles.PLANNER, roles.PROCUREMENT, roles.WAREHOUSE, roles.VIEWER), name='warehouse_logistics'),
    path('warehouse-logistics/update-area/',  allow_groups(views.warehouse_logistics_update_area, roles.WAREHOUSE, roles.PROCUREMENT, roles.PLANNER), name='warehouse_logistics_update_area'),
    path('warehouse-logistics/search/',       allow_groups(views.warehouse_logistics_search, roles.PLANNER, roles.PROCUREMENT, roles.WAREHOUSE, roles.VIEWER), name='warehouse_logistics_search'),
    path('warehouse-logistics/export-excel/', allow_groups(views.export_warehouse_pieces_excel, roles.PLANNER, roles.PROCUREMENT, roles.WAREHOUSE, roles.VIEWER), name='export_warehouse_pieces_excel'),

    # ===== Jobcard planning =====
    path('jobcards/planning/',                 allow_groups(views.jobcards_planning_list, roles.PLANNER, roles.PROCUREMENT, roles.WAREHOUSE, roles.VIEWER), name='jobcards_planning_list'),
    path('jobcards/<str:jobcard_id>/advance/', allow_groups(views.change_jobcard_status,  roles.PLANNER), name='change_jobcard_status'),

    path('rfid/modal/<int:stock_id>/', allow_groups(views.rfid_modal, roles.PLANNER), name='rfid_modal'),
    path('rfid/add/<int:stock_id>/',   allow_groups(views.rfid_add, roles.PLANNER), name='rfid_add'),

    # ===== Tokens =====
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # -------- API (FBVs DRF + JWT) --------
    path('api/jobcard/list/',                         views.api_jobcard_list,   name='api_jobcard_list'),
    path('api/jobcard/advance/<str:jobcard_number>/', views.api_jobcard_advance, name='api_jobcard_advance'),
    path('api/jobcard/<str:jobcard_number>/',         views.api_jobcard_detail, name='api_jobcard_detail'),
    path('api/jobcards/pdfs/', views.jobcard_pdfs, name='jobcard_pdfs'),
    path('api/revisoes_ultimas/', views.api_revisoes_ultimas, name='api_revisoes_ultimas'),

    path('jobcard/<str:jobcard_id>/allocation/<int:task_order>/', views.save_allocation, name='save_allocation'),
    path("api/rfid/check/",           views.check_rfid,   name="check_rfid"),
    path("api/rfid/all/",             views.api_rfid_all, name="api_rfid_all"),
    path("api/rfid/update-location/", views.update_location, name="update_location"),

    # -------- API Impediments --------
    path('api/impediments/',                views.api_list_impediments,    name='api_list_impediments'),
    path('api/impediments/create/',         views.api_create_impediment,   name='api_create_impediment'),
    path('api/impediments/<int:pk>/',       views.api_impediment_detail,   name='api_impediment_detail'),
    path('api/impediments/<int:pk>/update/',views.api_update_impediment,   name='api_update_impediment'),
    path('api/impediments/<int:pk>/delete/',views.api_delete_impediment,   name='api_delete_impediment'),

    path("api/jobcard/<str:jobcard_number>/manpowers/", views.api_jobcard_manpowers, name="api_jobcard_manpowers"),
    path("api/dfr/<str:jobcard_number>/close/",         views.api_dfr_close,      name="api_dfr_close"),
    
    # ===== Ações HTML auxiliares =====
    path('jobcard/delete_image/',    allow_groups(views.delete_jobcard_image, roles.PLANNER), name='delete_jobcard_image'),
    path('jobcard/upload_documents/',allow_groups(views.upload_documents,     roles.PLANNER), name='upload_documents'),
    path('ajax_tools_for_manpowers/', allow_groups(views.ajax_tools_for_manpowers, roles.PLANNER), name='ajax_tools_for_manpowers'),

    # -------- MODIFICAR JOBCARDS -------- #
    path("jobcards/modify/",                   allow_groups(views.modify_jobcard_entry,       roles.PLANNER), name="modify_jobcard_entry"),
    path("jobcards/<str:jobcard>/edit/patch/", allow_groups(views.modify_jobcard_excel_patch, roles.PLANNER), name="modify_jobcard_excel_patch"),
    path('jobcards/modify/<str:jobcard>/',     allow_groups(views.modify_jobcard_edit,        roles.PLANNER), name='modify_jobcard_edit'),
    path('jobcards/import/modify/',            allow_groups(views.import_jobcard_modify,      roles.PLANNER), name='import_jobcard_modify'),
    path('jobcards/export/',                   allow_groups(views.export_jobcard_excel,       roles.PLANNER, roles.PROCUREMENT, roles.WAREHOUSE, roles.VIEWER), name='export_jobcard_excel'),
    path('jobcards/template/',                 allow_groups(views.download_jobcard_modify_template, roles.PLANNER), name='download_jobcard_template'),

    # ===== PDFs em batch (APIs mantidas) =====
    path("api/pdf/run/batch",    views.api_regenerate_jobcards_pdfs, name="api_regenerate_jobcards_pdfs"),
    path('api/pdf/run/start',    views_pdf_api.api_pdf_run_start,    name='api_pdf_run_start'),
    path('api/pdf/run/progress', views_pdf_api.api_pdf_run_progress, name='api_pdf_run_progress'),
    path('api/pdf/run/stop',     views_pdf_api.api_pdf_run_stop,     name='api_pdf_run_stop'),
    path("api/pdf/run/log",      views_pdf_api.api_pdf_run_log,      name="api_pdf_run_log"),

    # --- CRONOGRAMA / P6 ---
    path('schedule/gantt/',        allow_groups(views_schedule.schedule_gantt,  roles.PLANNER, roles.PROCUREMENT, roles.WAREHOUSE, roles.VIEWER), name='schedule_gantt'),
    path('schedule/upload/',       allow_groups(views_schedule.schedule_upload, roles.PLANNER), name='schedule_upload'),
    path('schedule/api/',          views_schedule.schedule_api, name='schedule_api'),
    path('schedule/template/',     allow_groups(views_schedule.schedule_template, roles.PLANNER), name='schedule_template'),
    path("schedule/export-excel/", allow_groups(views_schedule.schedule_export_excel, roles.PLANNER, roles.PROCUREMENT, roles.WAREHOUSE, roles.VIEWER), name="schedule_export_excel"),

    path("engineering/docs/revisions/",                     allow_groups(views_documents.docs_revision_review, roles.PLANNER, roles.PROCUREMENT, roles.WAREHOUSE, roles.VIEWER), name="docs_revision_review"),
    path("engineering/docs/revisions/accept/<int:eng_id>/", allow_groups(views_documents.accept_doc_revision,  roles.PLANNER), name="accept_doc_revision"),
    path("engineering/docs/revisions/accept-bulk/",         allow_groups(views_documents.accept_doc_revision_bulk, roles.PLANNER), name="accept_doc_revision_bulk"),
    path('api/docs/to-accept-count/', views_documents.api_docs_to_accept_count, name='api_docs_to_accept_count'),

    # ===== ALOCAÇÃO DE MÃO DE OBRA AJUSTADA =====
    path('allocated/manpower/',              allow_groups(views_allocated_manpower.allocated_manpower_list, roles.PLANNER, roles.PROCUREMENT, roles.WAREHOUSE, roles.VIEWER), name='allocated_manpower_list'),
    path('allocated/manpower/data/',         allow_groups(views_allocated_manpower.allocated_manpower_table_data, roles.PLANNER), name='allocated_manpower_table_data'),
    path('allocated/manpower/import/',       allow_groups(views_allocated_manpower.import_allocated_manpower, roles.PLANNER), name='import_allocated_manpower'),
    path('allocated/manpower/export/',       allow_groups(views_allocated_manpower.export_allocated_manpower_csv, roles.PLANNER, roles.PROCUREMENT, roles.WAREHOUSE, roles.VIEWER), name='export_allocated_manpower_csv'),
    path("allocated/manpower/template/",     allow_groups(views_allocated_manpower.allocated_manpower_template, roles.PLANNER), name="allocated_manpower_template"),
    path("allocated/manpower/export/xlsx/",  allow_groups(views_allocated_manpower.export_allocated_manpower_xlsx, roles.PLANNER, roles.PROCUREMENT, roles.WAREHOUSE, roles.VIEWER), name="export_allocated_manpower_xlsx"),

    # ===== BAIXAR JOBCARDS EM PDF EM LOTE (ZIP) =====
    path("jobcards/downloads/",          allow_groups(views_downloads_jobcards.page,              roles.PLANNER, roles.PROCUREMENT, roles.WAREHOUSE, roles.VIEWER), name="download_jobcards_page"),
    path("jobcards/downloads/template/", allow_groups(views_downloads_jobcards.download_template, roles.PLANNER, roles.PROCUREMENT, roles.WAREHOUSE, roles.VIEWER), name="jobcards_download_template"),
    path("jobcards/downloads/by-list/",  allow_groups(views_downloads_jobcards.download_jobcards_by_list, roles.PLANNER, roles.PROCUREMENT, roles.WAREHOUSE, roles.VIEWER), name="download_jobcards_by_list"),
    path("jobcards/downloads/all/",      allow_groups(views_downloads_jobcards.download_all_jobcards,      roles.PLANNER), name="download_all_jobcards"),

    # ===== Sync (funciona como ação/HTML; protegido) =====
    path('jobcards/sync-all/',                   allow_groups(views_sync.api_sync_allocations_all, roles.PLANNER), name='jobcard_sync_allocations_all'),
    path('jobcards/<str:job_card_number>/sync/', allow_groups(views_sync.jobcard_sync_allocations,  roles.PLANNER), name='jobcard_sync_allocations'),


    # ===== MUDAR A SENHA DO SISTEMA =====
    path("account/profile/", views_account.user_profile, name="user_profile"),
    path("account/api/change-password/", views_account.api_change_password, name="api_change_password"),


    # ===== E-MAIL DE NOVO USUARIO ===== #
    path("accounts/password_change/", TaskfyPasswordChangeView.as_view(), name="password_change"),
    path("accounts/", include("django.contrib.auth.urls")),  # inclui /reset/<uid>/<token>/ etc.

    
    path("account/api/change-password/", views_account.api_change_password, name="api_change_password"),

    # ===== DASHBOARD WORKPACK (HTML) =====
    path("dashboard/workpack/", views_dashboardWorkpack.dashboard_workpack, name="dashboard_workpack"),
    path("dashboard/workpack/<str:wp_number>/", views_dashboardWorkpack.dashboard_workpack, name="dashboard_workpack_detail"),
    path("dashboard/workpack/", allow_groups(views_dashboardWorkpack.dashboard_workpack, roles.PLANNER, roles.PROCUREMENT, roles.WAREHOUSE, roles.VIEWER), name="dashboard_workpack"),

    path("jobcard/<str:jobcard_number>/pdf/", views_dashboardWorkpack.jobcard_pdf_view, name="jobcard_pdf"),

]
