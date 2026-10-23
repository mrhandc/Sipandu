from django.contrib import admin
from apps.approval.models import ApprovalHistory


@admin.register(ApprovalHistory)
class ApprovalHistoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'pengajuan', 'actor', 'action', 'status_dari', 'status_ke', 'is_mode_b', 'created_at')
    list_filter = ('action', 'is_mode_b', 'status_ke')
    search_fields = ('pengajuan__id', 'actor__username', 'actor__first_name', 'catatan')
