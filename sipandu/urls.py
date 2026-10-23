"""
URL configuration for SIPANDU project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('accounts/', include('apps.accounts.urls')),
    path('surat/', include('apps.surat.urls')),
    path('pengajuan/', include('apps.pengajuan.urls')),
    path('approval/', include('apps.approval.urls')),
    path('', include('apps.core.urls')),
    # Keep the application admin pages above Django Admin so the shared
    # /admin/ prefix resolves to the intended core views.
    path('admin/', admin.site.urls),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
