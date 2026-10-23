from django.contrib import admin
from apps.pengajuan.models import Persyaratan, Pengajuan, DokumenPengajuan


class DokumenPengajuanInline(admin.TabularInline):
    model = DokumenPengajuan
    extra = 0


@admin.register(Persyaratan)
class PersyaratanAdmin(admin.ModelAdmin):
    list_display = ('jenis_surat', 'nama_dokumen', 'is_required')
    list_filter = ('jenis_surat', 'is_required')


@admin.register(Pengajuan)
class PengajuanAdmin(admin.ModelAdmin):
    list_display = ('id', 'warga', 'jenis_surat', 'wilayah', 'status', 'jumlah_revisi', 'created_at')
    list_filter = ('status', 'jenis_surat', 'wilayah')
    search_fields = ('warga__username', 'warga__first_name', 'warga__nik', 'keperluan')
    inlines = [DokumenPengajuanInline]
