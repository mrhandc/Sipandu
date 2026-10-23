from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from apps.accounts.models import CustomUser, Wilayah, VerifikasiAkun


@admin.register(Wilayah)
class WilayahAdmin(admin.ModelAdmin):
    list_display = ('rt', 'rw', 'dusun', 'nama_desa', 'kecamatan', 'kabupaten')
    search_fields = ('rt', 'rw', 'dusun')


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'first_name', 'nik', 'role', 'status_akun', 'wilayah', 'is_staff')
    list_filter = ('role', 'status_akun', 'is_staff', 'is_active')
    search_fields = ('username', 'first_name', 'nik', 'email')
    fieldsets = UserAdmin.fieldsets + (
        ('Informasi SIPANDU', {
            'fields': ('role', 'nik', 'no_hp', 'wilayah', 'alamat', 'status_akun', 'catatan_penolakan')
        }),
    )


@admin.register(VerifikasiAkun)
class VerifikasiAkunAdmin(admin.ModelAdmin):
    list_display = ('user', 'status', 'verified_by', 'verified_at', 'created_at')
    list_filter = ('status',)
    search_fields = ('user__username', 'user__nik', 'user__first_name')
