from datetime import timedelta
from django.test import TestCase
from django.utils import timezone
from apps.accounts.models import CustomUser, Wilayah
from apps.surat.models import JenisSurat, Surat
from apps.pengajuan.models import Pengajuan
from apps.pengajuan.forms import PengajuanCreateForm
from apps.core.models import SystemConfig


class PengajuanBusinessLogicTest(TestCase):
    def setUp(self):
        self.wilayah = Wilayah.objects.create(rt="001", rw="002", dusun="Krajan")
        self.warga = CustomUser.objects.create_user(
            username="warga_uji",
            password="password123",
            nik="3507999988887777",
            role=CustomUser.Role.WARGA,
            status_akun=CustomUser.StatusAkun.AKTIF,
            wilayah=self.wilayah
        )
        self.jenis_domisili = JenisSurat.objects.create(
            kode="DOMISILI",
            nama="Surat Keterangan Domisili",
            masa_berlaku_hari=365
        )
        SystemConfig.objects.create(key="MAX_REVISION_LIMIT", value="3", deskripsi="Batas revisi")

    def test_blokir_pengajuan_sejenis_jika_surat_masih_aktif(self):
        """Sistem menolak pengajuan baru selama surat sejenis masih berlaku (§15.2)"""
        # Terbitkan surat domisili aktif
        pengajuan_awal = Pengajuan.objects.create(
            warga=self.warga,
            jenis_surat=self.jenis_domisili,
            wilayah=self.wilayah,
            keperluan="Awal",
            status=Pengajuan.StatusPengajuan.DITERBITKAN
        )
        Surat.objects.create(
            nomor_surat="DOM/001/DSA/X/2026",
            pengajuan=pengajuan_awal,
            jenis_surat=self.jenis_domisili,
            warga=self.warga,
            tanggal_terbit=timezone.now().date(),
            tanggal_kadaluarsa=timezone.now().date() + timedelta(days=365),
            status_surat=Surat.StatusSurat.AKTIF
        )

        # Coba ajukan surat sejenis
        form = PengajuanCreateForm(
            data={'jenis_surat': self.jenis_domisili.id, 'keperluan': 'Ajukan lagi'},
            user=self.warga
        )
        self.assertFalse(form.is_valid())
        self.assertIn("masih memiliki Surat Keterangan Domisili yang masih berlaku", str(form.errors))

    def test_aturan_pembatalan_oleh_warga(self):
        """Warga hanya bisa membatalkan sebelum masuk MENUNGGU_KEPALA_DESA (§16)"""
        p_bisa = Pengajuan.objects.create(
            warga=self.warga,
            jenis_surat=self.jenis_domisili,
            wilayah=self.wilayah,
            status=Pengajuan.StatusPengajuan.MENUNGGU_RT_RW
        )
        self.assertTrue(p_bisa.can_be_cancelled_by_warga)

        p_tidak_bisa = Pengajuan.objects.create(
            warga=self.warga,
            jenis_surat=self.jenis_domisili,
            wilayah=self.wilayah,
            status=Pengajuan.StatusPengajuan.MENUNGGU_KEPALA_DESA
        )
        self.assertFalse(p_tidak_bisa.can_be_cancelled_by_warga)
