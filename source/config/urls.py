from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from core import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.home, name='home'),
    path('upload/', views.upload_pdf, name='upload_pdf'),
    path('generate/<str:input_type>/<str:input_filename>/<str:podcast_title>/', views.generate_podcast, name='generate_podcast'),
    path('podcasts/', views.podcast_list, name='podcast_list'),
    path('podcast/<int:podcast_id>/', views.podcast_detail, name='podcast_detail'),
    path('generate_standalone_html/<int:podcast_id>/', views.generate_standalone_html, name='generate_standalone_html'),
    path('upload_text/', views.upload_text, name='upload_text'),
]

if settings.DEBUG:
    urlpatterns = static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT) + urlpatterns