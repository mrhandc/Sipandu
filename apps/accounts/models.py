from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator


class Wilayah(models.Model):
    rt = models.CharField(max_length=5, verbose_name="RT")
    rw = models.CharField(max_length=5, verbose_name="RW")
    dusun = models.CharField(max_length=100, blank=True, default="Dusun I", verbose_name="Dusun/Lingkungan")
    nama_desa = models.CharField(max_length=100, default="Desa Sukamaju", verbose_name="Nama Desa")
    kecamatan = models.CharField(max_length=100, default="Kecamatan Wonosari", verbose_name="Kecamatan")
    kabupaten = models.CharField(max_length=100, default="Kabupaten Malang", verbose_name="Kabupaten")
    provinsi = models.CharField(max_length=100, default="Jawa Timur", verbose_name="Provinsi")
    kode_pos = models.CharField(max_length=10, default="65100", verbose_name="Kode Pos")

    class Meta:
        verbose_name = "Wilayah RT/RW"
        verbose_name_plural = "Daftar Wilayah RT/RW"
        unique_together = ('rt', 'rw', 'dusun')

    def __str__(self):
        return f"RT {self.rt} / RW {self.rw} - {self.dusun}"


class CustomUser(AbstractUser):
    class Role(models.TextChoices):
        WARGA = 'WARGA', 'Warga'
        RT_RW = 'RT_RW', 'Ketua RT/RW'
        SEKDES = 'SEKDES', 'Sekretaris Desa'
        KADES = 'KADES', 'Kepala Desa'
        ADMIN = 'ADMIN', 'Admin Desa'

    class StatusAkun(models.TextChoices):
        PENDING_VERIFIKASI = 'PENDING_VERIFIKASI', 'Menunggu Verifikasi Identitas'
        AKTIF = 'AKTIF', 'Aktif (Terverifikasi)'
        DITOLAK = 'DITOLAK', 'Verifikasi Ditolak'
        NONAKTIF = 'NONAKTIF', 'Nonaktif'

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.WARGA,
        verbose_name="Peran Pengguna"
    )
    nik = models.CharField(
        max_length=16,
        unique=True,
        null=True,
        blank=True,
        validators=[
            RegexValidator(r'^\d{16}$', 'NIK wajib terdiri dari tepat 16 digit numerik.')
        ],
        verbose_name="NIK"
    )
    no_hp = models.CharField(
        max_length=20,
        blank=True,
        verbose_name="Nomor Telepon / WhatsApp"
    )
    alamat = models.TextField(blank=True, verbose_name="Alamat Domisili")
    wilayah = models.ForeignKey(
        Wilayah,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='warga_list',
        verbose_name="Wilayah RT/RW"
    )
    status_akun = models.CharField(
        max_length=25,
        choices=StatusAkun.choices,
        default=StatusAkun.PENDING_VERIFIKASI,
        verbose_name="Status Akun"
    )
    catatan_penolakan = models.TextField(
        blank=True,
        verbose_name="Alasan Penolakan Akun"
    )

    @property
    def is_warga(self):
        return self.role == self.Role.WARGA

    @property
    def is_rt_rw(self):
        return self.role == self.Role.RT_RW

    @property
    def is_sekdes(self):
        return self.role == self.Role.SEKDES

    @property
    def is_kades(self):
        return self.role == self.Role.KADES

    @property
    def is_admin_desa(self):
        return self.role == self.Role.ADMIN or self.is_superuser

    @property
    def masked_nik(self):
        """Minimalisasi data pribadi: samarkan NIK saat tampil di dashboard umum (§19)"""
        if self.nik and len(self.nik) == 16:
            return f"{self.nik[:6]}******{self.nik[-4:]}"
        return self.nik or "-"

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"


class VerifikasiAkun(models.Model):
    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='verifikasi_identitas'
    )
    foto_ktp = models.ImageField(
        upload_to='ktp/',
        verbose_name="Foto KTP"
    )
    foto_wajah = models.ImageField(
        upload_to='wajah/',
        verbose_name="Foto Wajah (Selfie)"
    )
    status = models.CharField(
        max_length=25,
        choices=CustomUser.StatusAkun.choices,
        default=CustomUser.StatusAkun.PENDING_VERIFIKASI
    )
    catatan = models.TextField(
        blank=True,
        verbose_name="Catatan Verifikasi Admin"
    )
    verified_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verifikasi_diproses'
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Verifikasi Identitas Akun"
        verbose_name_plural = "Daftar Verifikasi Identitas Akun"

    def __str__(self):
        return f"Verifikasi {self.user.username} - {self.get_status_display()}"
