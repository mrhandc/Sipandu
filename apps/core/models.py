from django.db import models
from django.conf import settings


class SystemConfig(models.Model):
    key = models.CharField(max_length=100, unique=True, verbose_name="Kunci Konfigurasi")
    value = models.TextField(verbose_name="Nilai Konfigurasi")
    deskripsi = models.CharField(max_length=255, blank=True, verbose_name="Keterangan")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Konfigurasi Sistem"
        verbose_name_plural = "Daftar Konfigurasi Sistem"

    def __str__(self):
        return f"{self.key}: {self.value}"

    @classmethod
    def get_value(cls, key, default=""):
        config = cls.objects.filter(key=key).first()
        return config.value if config else str(default)

    @classmethod
    def get_int(cls, key, default=0):
        val = cls.get_value(key, default)
        try:
            return int(val)
        except (ValueError, TypeError):
            return default


class Notifikasi(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifikasi_set'
    )
    judul = models.CharField(max_length=200, verbose_name="Judul Notifikasi")
    pesan = models.TextField(verbose_name="Pesan")
    link = models.CharField(max_length=255, blank=True, verbose_name="Tautan Aksi")
    is_read = models.BooleanField(default=False, verbose_name="Sudah Dibaca")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Notifikasi"
        verbose_name_plural = "Daftar Notifikasi"
        ordering = ['-created_at']

    def __str__(self):
        return f"Notif to {self.user.username}: {self.judul}"


class AuditLog(models.Model):
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs'
    )
    action = models.CharField(max_length=100, verbose_name="Aksi")
    module = models.CharField(max_length=50, verbose_name="Modul")
    details = models.TextField(blank=True, verbose_name="Detail Perubahan")
    ip_address = models.CharField(max_length=45, blank=True, verbose_name="IP Address")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Audit Log"
        verbose_name_plural = "Daftar Audit Log"
        ordering = ['-created_at']

    def __str__(self):
        actor_name = self.actor.username if self.actor else "System"
        return f"[{self.created_at:%Y-%m-%d %H:%M}] {actor_name} - {self.action}"
