from django.contrib import admin
from apps.core.models import SystemConfig, Notifikasi, AuditLog


@admin.register(SystemConfig)
class SystemConfigAdmin(admin.ModelAdmin):
    list_display = ('key', 'value', 'deskripsi', 'updated_at')
    search_fields = ('key', 'deskripsi')


@admin.register(Notifikasi)
class NotifikasiAdmin(admin.ModelAdmin):
    list_display = ('user', 'judul', 'is_read', 'created_at')
    list_filter = ('is_read',)
    search_fields = ('user__username', 'judul', 'pesan')


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('actor', 'action', 'module', 'ip_address', 'created_at')
    list_filter = ('module', 'action')
    search_fields = ('actor__username', 'action', 'details')
