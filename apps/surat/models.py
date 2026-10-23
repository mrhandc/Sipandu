import uuid
from django.db import models, transaction
from django.conf import settings
from django.utils import timezone


class JenisSurat(models.Model):
    kode = models.CharField(max_length=20, unique=True, verbose_name="Kode Surat (mis: SKTM)")
    nama = models.CharField(max_length=150, verbose_name="Nama Surat")
    deskripsi = models.TextField(blank=True, verbose_name="Deskripsi / Kegunaan")
    masa_berlaku_hari = models.PositiveIntegerField(
        default=180,
        verbose_name="Masa Berlaku (Hari)",
        help_text="SKTM: 180 hari (6 bln), Domisili & SKU: 365 hari (1 thn) (§15.1)"
    )
    is_active = models.BooleanField(default=True, verbose_name="Aktif Dilayani")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Jenis Surat"
        verbose_name_plural = "Daftar Jenis Surat"

    def __str__(self):
        return f"{self.nama} ({self.kode})"


class LetterNumberSequence(models.Model):
    """
    Penomoran Surat Concurrency-Safe (§20).
    Atomic lock via select_for_update() inside transaction.
    """
    jenis_surat = models.ForeignKey(
        JenisSurat,
        on_delete=models.CASCADE,
        related_name='sequences'
    )
    tahun = models.PositiveIntegerField(verbose_name="Tahun")
    last_number = models.PositiveIntegerField(default=0, verbose_name="Nomor Terakhir")

    class Meta:
        verbose_name = "Sequence Nomor Surat"
        verbose_name_plural = "Sequence Nomor Surat"
        unique_together = ('jenis_surat', 'tahun')

    @staticmethod
    def to_roman(month: int) -> str:
        roman_map = {
            1: "I", 2: "II", 3: "III", 4: "IV", 5: "V", 6: "VI",
            7: "VII", 8: "VIII", 9: "IX", 10: "X", 11: "XI", 12: "XII"
        }
        return roman_map.get(month, "I")

    @classmethod
    def generate_next_number(cls, jenis_surat, kode_desa="DSA"):
        """
        BEGIN TRANSACTION
        lock sequence row (tahun + jenis_surat)
        ambil last_number, increment
        buat surat dengan nomor baru (§20)
        """
        with transaction.atomic():
            now = timezone.now()
            tahun = now.year
            bulan_romawi = cls.to_roman(now.month)

            seq, created = cls.objects.select_for_update().get_or_create(
                jenis_surat=jenis_surat,
                tahun=tahun,
                defaults={'last_number': 0}
            )
            seq.last_number += 1
            seq.save(update_fields=['last_number'])

            nomor_surat = f"{jenis_surat.kode}/{seq.last_number:03d}/{kode_desa}/{bulan_romawi}/{tahun}"
            return nomor_surat


class Surat(models.Model):
    class StatusSurat(models.TextChoices):
        AKTIF = 'AKTIF', 'Aktif (Berlaku)'
        KEDALUWARSA = 'KEDALUWARSA', 'Kedaluwarsa'
        DIBATALKAN = 'DIBATALKAN', 'Dibatalkan (Pengecualian Admin)'

    nomor_surat = models.CharField(max_length=100, unique=True, verbose_name="Nomor Surat")
    pengajuan = models.OneToOneField(
        'pengajuan.Pengajuan',
        on_delete=models.CASCADE,
        related_name='surat_terbit'
    )
    jenis_surat = models.ForeignKey(
        JenisSurat,
        on_delete=models.PROTECT,
        related_name='surat_diterbitkan'
    )
    warga = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='surat_saya'
    )
    tanggal_terbit = models.DateField(default=timezone.now, verbose_name="Tanggal Terbit")
    tanggal_kadaluarsa = models.DateField(verbose_name="Tanggal Kadaluarsa")
    status_surat = models.CharField(
        max_length=20,
        choices=StatusSurat.choices,
        default=StatusSurat.AKTIF,
        verbose_name="Status Keberlakuan Surat (§15.3)"
    )
    catatan_pembatalan = models.TextField(
        blank=True,
        verbose_name="Catatan Pembatalan Surat (Pengecualian)"
    )
    dibatalkan_oleh = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='surat_yang_dibatalkan'
    )
    dibatalkan_pada = models.DateTimeField(null=True, blank=True)
    kode_verifikasi = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        verbose_name="Kode Verifikasi QR"
    )
    file_pdf = models.FileField(
        upload_to='surat_pdf/',
        null=True,
        blank=True,
        verbose_name="Dokumen PDF Surat"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Surat Diterbitkan"
        verbose_name_plural = "Daftar Surat Diterbitkan"
        ordering = ['-tanggal_terbit']

    def update_expiration_status(self):
        """Update status surat otomatis jika sudah melewati tanggal kadaluarsa"""
        if self.status_surat == self.StatusSurat.AKTIF and timezone.now().date() > self.tanggal_kadaluarsa:
            self.status_surat = self.StatusSurat.KEDALUWARSA
            self.save(update_fields=['status_surat'])
        return self.status_surat

    @property
    def is_currently_valid(self):
        return (
            self.status_surat == self.StatusSurat.AKTIF and
            timezone.now().date() <= self.tanggal_kadaluarsa
        )

    def __str__(self):
        return f"{self.nomor_surat} - {self.warga.get_full_name() or self.warga.username}"
