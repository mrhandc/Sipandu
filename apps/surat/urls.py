from django.urls import path
from apps.surat import views

app_name = 'surat'

urlpatterns = [
    path('verifikasi/<uuid:uuid>/', views.verifikasi_publik_view, name='verifikasi_publik'),
    path('saya/', views.daftar_surat_saya_view, name='surat_saya'),
    path('download/<int:pk>/', views.download_pdf_view, name='download_pdf'),
    path('admin/kelola/', views.admin_daftar_surat_view, name='admin_daftar_surat'),
    path('admin/batalkan/<int:pk>/', views.admin_batalkan_surat_view, name='admin_batalkan_surat'),
]
