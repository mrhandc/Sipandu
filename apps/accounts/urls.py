from django.urls import path
from apps.accounts import views

app_name = 'accounts'

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register_warga_view, name='register'),
    path('status/', views.status_akun_view, name='status_akun'),
    path('admin/verifikasi/', views.admin_verifikasi_list_view, name='admin_verifikasi_list'),
    path('admin/verifikasi/<int:pk>/', views.admin_verifikasi_detail_view, name='admin_verifikasi_detail'),
]
