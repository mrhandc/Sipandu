from django.db import models
from django.conf import settings
from apps.pengajuan.models import Pengajuan


class ApprovalHistory(models.Model):
    """
    Audit Trail (§21): Setiap perubahan status wajib tercatat di APPROVAL_HISTORY.
    Mendukung Mode A (Digital) & Mode B (Verifikasi Terwakilkan oleh Admin wajib bukti lampiran, §17).
    """
    class ActionType(models.TextChoices):
        MENGAJUKAN = 'MENGAJUKAN', 'Mengajukan Permohonan'
        MEREVISI = 'MEREVISI', 'Mengirimkan Revisi Permohonan'
        MEMBATALKAN = 'MEMBATALKAN', 'Membatalkan Permohonan'
        VERIFIKASI_SETUJU = 'VERIFIKASI_SETUJU', 'Menyetujui Verifikasi'
        PERLU_REVISI = 'PERLU_REVISI', 'Meminta Revisi Berkas/Data'
        MENOLAK = 'MENOLAK', 'Menolak Permohonan'
        FINAL_APPROVAL = 'FINAL_APPROVAL', 'Persetujuan Final & Terbitkan Surat'
        VERIFIKASI_MODE_B = 'VERIFIKASI_MODE_B', 'Verifikasi Terwakilkan RT/RW oleh Admin (Mode B)'

    pengajuan = models.ForeignKey(
        Pengajuan,
        on_delete=models.CASCADE,
        related_name='approval_history'
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='riwayat_approval_dilakukan',
        verbose_name="Petugas/Warga Pembuat Keputusan (§17 Akun Personal)"
    )
    action = models.CharField(
        max_length=50,
        choices=ActionType.choices,
        verbose_name="Tindakan"
    )
    status_dari = models.CharField(
        max_length=50,
        verbose_name="Status Sebelum"
    )
    status_ke = models.CharField(
        max_length=50,
        verbose_name="Status Sesudah"
    )
    catatan = models.TextField(
        blank=True,
        verbose_name="Catatan Keputusan (Wajib bila Revisi/Tolak, §13.1)"
    )
    lampiran_bukti = models.FileField(
        upload_to='bukti_approval/',
        blank=True,
        null=True,
        verbose_name="Bukti Komunikasi (Wajib untuk Mode B, §17)"
    )
    is_mode_b = models.BooleanField(
        default=False,
        verbose_name="Apakah Verifikasi Terwakilkan (Mode B)"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Waktu Tindakan")

    class Meta:
        verbose_name = "Riwayat Approval (Audit Trail)"
        verbose_name_plural = "Daftar Riwayat Approval"
        ordering = ['-created_at']

    def __str__(self):
        return f"Audit #{self.id}: {self.actor.username} -> {self.action} on Pengajuan #{self.pengajuan_id}"
