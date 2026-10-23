from datetime import timedelta
from django.test import TestCase
from django.utils import timezone
from apps.accounts.models import CustomUser, Wilayah
from apps.surat.models import JenisSurat, Surat, LetterNumberSequence
from apps.pengajuan.models import Pengajuan
from apps.surat.services import terbitkan_surat_digital


class SuratBusinessLogicTest(TestCase):
    def setUp(self):
        self.wilayah = Wilayah.objects.create(rt="001", rw="002", dusun="Krajan")
        self.warga = CustomUser.objects.create_user(
            username="warga_test",
            password="password123",
            nik="3507111122223333",
            role=CustomUser.Role.WARGA,
            status_akun=CustomUser.StatusAkun.AKTIF,
            wilayah=self.wilayah
        )
        self.kades = CustomUser.objects.create_user(
            username="kades_test",
            password="password123",
            role=CustomUser.Role.KADES,
            status_akun=CustomUser.StatusAkun.AKTIF
        )
        self.jenis_sktm = JenisSurat.objects.create(
            kode="SKTM",
            nama="Surat Keterangan Tidak Mampu",
            masa_berlaku_hari=180
        )
        self.pengajuan = Pengajuan.objects.create(
            warga=self.warga,
            jenis_surat=self.jenis_sktm,
            wilayah=self.wilayah,
            keperluan="Bantuan Pendidikan",
            status=Pengajuan.StatusPengajuan.MENUNGGU_KEPALA_DESA
        )

    def test_concurrency_safe_number_sequence(self):
        """Test generator nomor surat atomic increment (§20)"""
        nomor1 = LetterNumberSequence.generate_next_number(self.jenis_sktm, kode_desa="DSA")
        nomor2 = LetterNumberSequence.generate_next_number(self.jenis_sktm, kode_desa="DSA")

        self.assertIn("SKTM/001/DSA/", nomor1)
        self.assertIn("SKTM/002/DSA/", nomor2)
        self.assertNotEqual(nomor1, nomor2)

    def test_penerbitan_surat_dan_masa_berlaku(self):
        """Test perhitungan tanggal kadaluarsa otomatis (§15.1, §15.2)"""
        surat = terbitkan_surat_digital(self.pengajuan, request_host="testserver")
        
        self.assertIsNotNone(surat.file_pdf)
        self.assertEqual(surat.status_surat, Surat.StatusSurat.AKTIF)
        
        expected_kadaluarsa = timezone.now().date() + timedelta(days=180)
        self.assertEqual(surat.tanggal_kadaluarsa, expected_kadaluarsa)
        self.assertTrue(surat.is_currently_valid)

    def test_update_expiration_status(self):
        """Test perubahan status surat otomatis saat melewati tanggal kadaluarsa (§15.3)"""
        surat = terbitkan_surat_digital(self.pengajuan, request_host="testserver")
        # Simulasikan tanggal kadaluarsa kemarin
        surat.tanggal_kadaluarsa = timezone.now().date() - timedelta(days=1)
        surat.save()

        surat.update_expiration_status()
        self.assertEqual(surat.status_surat, Surat.StatusSurat.KEDALUWARSA)
        self.assertFalse(surat.is_currently_valid)
