from django.urls import path
from apps.core import views

app_name = 'core'

urlpatterns = [
    path('', views.dashboard_view, name='dashboard'),
    path('notifikasi/', views.notifikasi_list_view, name='notifikasi_list'),
    path('admin/config/', views.system_config_view, name='system_config'),
    path('admin/whatsapp-test/', views.whatsapp_test_view, name='whatsapp_test'),
    path('admin/audit-log/', views.audit_log_list_view, name='audit_log_list'),
    path('laporan/', views.laporan_pelayanan_view, name='laporan_pelayanan'),
]
