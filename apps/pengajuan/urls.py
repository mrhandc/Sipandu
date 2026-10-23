from django.urls import path
from apps.pengajuan import views

app_name = 'pengajuan'

urlpatterns = [
    path('', views.pengajuan_list_view, name='pengajuan_list'),
    path('buat/', views.pengajuan_create_view, name='pengajuan_create'),
    path('detail/<int:pk>/', views.pengajuan_detail_view, name='pengajuan_detail'),
    path('revisi/<int:pk>/', views.pengajuan_revisi_view, name='pengajuan_revisi'),
    path('batal/<int:pk>/', views.pengajuan_batal_view, name='pengajuan_batal'),
]
