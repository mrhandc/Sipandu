from django.contrib import admin
from apps.surat.models import JenisSurat, Surat, LetterNumberSequence


@admin.register(JenisSurat)
class JenisSuratAdmin(admin.ModelAdmin):
    list_display = ('kode', 'nama', 'masa_berlaku_hari', 'is_active', 'created_at')
    list_editable = ('masa_berlaku_hari', 'is_active')
    search_fields = ('kode', 'nama')


@admin.register(LetterNumberSequence)
class LetterNumberSequenceAdmin(admin.ModelAdmin):
    list_display = ('jenis_surat', 'tahun', 'last_number')
    list_filter = ('tahun', 'jenis_surat')


@admin.register(Surat)
class SuratAdmin(admin.ModelAdmin):
    list_display = ('nomor_surat', 'jenis_surat', 'warga', 'tanggal_terbit', 'tanggal_kadaluarsa', 'status_surat')
    list_filter = ('status_surat', 'jenis_surat', 'tanggal_terbit')
    search_fields = ('nomor_surat', 'warga__first_name', 'warga__nik', 'warga__username')
    readonly_fields = ('kode_verifikasi', 'created_at')
