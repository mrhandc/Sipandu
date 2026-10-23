from django.urls import path
from apps.approval import views

app_name = 'approval'

urlpatterns = [
    path('antrian/', views.approval_queue_view, name='queue'),
    path('detail/<int:pk>/', views.approval_detail_view, name='detail'),
    path('mode-b/<int:pk>/', views.mode_b_verification_view, name='mode_b'),
]
