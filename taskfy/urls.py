# taskfy/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # Painel admin
    path('admin/', admin.site.urls),

    # Inclui todas as rotas do app jobcards (HTML + API FBVs)
    path('', include('jobcards.urls')),
    path('django-rq/', include('django_rq.urls')),
    
    
    

    # Se quiser, inclua outros apps com suas próprias rotas API aqui
    # path('api/outro_app/', include(outro_router.urls)),
]

# Servir arquivos de mídia no modo DEBUG
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
