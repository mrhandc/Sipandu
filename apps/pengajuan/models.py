from django.db import models
from django.conf import settings
from apps.surat.models import JenisSurat
from apps.accounts.models import Wilayah


class Persyaratan(models.Model):
    jenis_surat = models.ForeignKey(
        JenisSurat,
        on_delete=models.CASCADE,
        related_name='daftar_persyaratan'
    )
    nama_dokumen = models.CharField(max_length=150, verbose_name="Nama Dokumen Persyaratan")
    keterangan = models.CharField(max_length=255, blank=True, verbose_name="Keterangan / Panduan")
    is_required = models.BooleanField(default=True, verbose_name="Wajib Diunggah")

    class Meta:
        verbose_name = "Persyaratan Surat"
        verbose_name_plural = "Daftar Persyaratan Surat"

    def __str__(self):
        return f"[{self.jenis_surat.kode}] {self.nama_dokumen}"


class Pengajuan(models.Model):
    class StatusPengajuan(models.TextChoices):
        DRAFT = 'DRAFT', 'Belum diajukan'
        DIAJUKAN = 'DIAJUKAN', 'Baru dikirim warga'
        MENUNGGU_RT_RW = 'MENUNGGU_RT_RW', 'Menunggu verifikasi RT/RW'
        PERLU_REVISI_RT_RW = 'PERLU_REVISI_RT_RW', 'RT/RW meminta revisi'
        MENUNGGU_SEKDES = 'MENUNGGU_SEKDES', 'Menunggu verifikasi Sekdes'
        PERLU_REVISI_SEKDES = 'PERLU_REVISI_SEKDES', 'Sekdes meminta revisi'
        MENUNGGU_KEPALA_DESA = 'MENUNGGU_KEPALA_DESA', 'Menunggu persetujuan Kades'
        PERLU_REVISI_KADES = 'PERLU_REVISI_KADES', 'Kades meminta revisi'
        DISETUJUI = 'DISETUJUI', 'Disetujui, siap diterbitkan'
        MENUNGGU_PENERBITAN = 'MENUNGGU_PENERBITAN', 'Proses cetak & tanda tangan'
        DITERBITKAN = 'DITERBITKAN', 'Surat selesai'
        DITOLAK = 'DITOLAK', 'Ditolak final'
        DIBATALKAN = 'DIBATALKAN', 'Dibatalkan oleh warga'

    warga = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='pengajuan_surat'
    )
    jenis_surat = models.ForeignKey(
        JenisSurat,
        on_delete=models.PROTECT,
        related_name='pengajuan_list'
    )
    wilayah = models.ForeignKey(
        Wilayah,
        on_delete=models.PROTECT,
        related_name='pengajuan_wilayah'
    )
    keperluan = models.TextField(verbose_name="Tujuan / Keperluan Pengajuan")
    data_tambahan = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Data Spesifik Formulir"
    )
    status = models.CharField(
        max_length=30,
        choices=StatusPengajuan.choices,
        default=StatusPengajuan.DIAJUKAN,
        verbose_name="Status Pengajuan (§12)"
    )
    jumlah_revisi = models.PositiveIntegerField(
        default=0,
        verbose_name="Jumlah Kali Direvisi (§13.2)"
    )
    catatan_terakhir = models.TextField(
        blank=True,
        verbose_name="Catatan Approval/Revisi Terakhir"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    submitted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Pengajuan Surat"
        verbose_name_plural = "Daftar Pengajuan Surat"
        ordering = ['-updated_at']

    @property
    def can_be_cancelled_by_warga(self):
        """
        Warga dapat membatalkan pengajuan sendiri selama status masih:
        DRAFT, DIAJUKAN, MENUNGGU_RT_RW, PERLU_REVISI_RT_RW, MENUNGGU_SEKDES, PERLU_REVISI_SEKDES (§16)
        """
        cancellable_statuses = [
            self.StatusPengajuan.DRAFT,
            self.StatusPengajuan.DIAJUKAN,
            self.StatusPengajuan.MENUNGGU_RT_RW,
            self.StatusPengajuan.PERLU_REVISI_RT_RW,
            self.StatusPengajuan.MENUNGGU_SEKDES,
            self.StatusPengajuan.PERLU_REVISI_SEKDES,
        ]
        return self.status in cancellable_statuses

    @property
    def is_in_revision(self):
        return self.status in [
            self.StatusPengajuan.PERLU_REVISI_RT_RW,
            self.StatusPengajuan.PERLU_REVISI_SEKDES,
            self.StatusPengajuan.PERLU_REVISI_KADES
        ]

    @property
    def progress_percentage(self):
        """Menghitung persentase progress untuk progress bar real-time warga (§22)"""
        mapping = {
            self.StatusPengajuan.DRAFT: 10,
            self.StatusPengajuan.DIAJUKAN: 20,
            self.StatusPengajuan.MENUNGGU_RT_RW: 30,
            self.StatusPengajuan.PERLU_REVISI_RT_RW: 30,
            self.StatusPengajuan.MENUNGGU_SEKDES: 55,
            self.StatusPengajuan.PERLU_REVISI_SEKDES: 55,
            self.StatusPengajuan.MENUNGGU_KEPALA_DESA: 80,
            self.StatusPengajuan.PERLU_REVISI_KADES: 80,
            self.StatusPengajuan.DISETUJUI: 90,
            self.StatusPengajuan.MENUNGGU_PENERBITAN: 95,
            self.StatusPengajuan.DITERBITKAN: 100,
            self.StatusPengajuan.DITOLAK: 100,
            self.StatusPengajuan.DIBATALKAN: 100,
        }
        return mapping.get(self.status, 0)

    def __str__(self):
        return f"Pengajuan #{self.id} - {self.jenis_surat.nama} ({self.warga.get_full_name() or self.warga.username})"


class DokumenPengajuan(models.Model):
    pengajuan = models.ForeignKey(
        Pengajuan,
        on_delete=models.CASCADE,
        related_name='dokumen_lampiran'
    )
    persyaratan = models.ForeignKey(
        Persyaratan,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    nama_dokumen = models.CharField(max_length=150)
    file = models.FileField(upload_to='dokumen_pengajuan/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Dokumen Lampiran Pengajuan"
        verbose_name_plural = "Dokumen Lampiran Pengajuan"

    def __str__(self):
        return f"{self.nama_dokumen} (Pengajuan #{self.pengajuan_id})"
