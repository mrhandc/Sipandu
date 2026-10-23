from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from apps.accounts.models import CustomUser, Wilayah
from apps.surat.models import JenisSurat
from apps.pengajuan.models import Pengajuan
from apps.approval.models import ApprovalHistory
from apps.approval.forms import ModeBApprovalForm


class ApprovalWorkflowTest(TestCase):
    def setUp(self):
        self.wilayah = Wilayah.objects.create(rt="001", rw="002", dusun="Krajan")
        self.warga = CustomUser.objects.create_user(
            username="warga1",
            password="password123",
            nik="3507123456789012",
            role=CustomUser.Role.WARGA,
            status_akun=CustomUser.StatusAkun.AKTIF,
            wilayah=self.wilayah
        )
        self.admin = CustomUser.objects.create_user(
            username="admin1",
            password="password123",
            role=CustomUser.Role.ADMIN,
            status_akun=CustomUser.StatusAkun.AKTIF
        )
        self.sku = JenisSurat.objects.create(kode="SKU", nama="Surat Keterangan Usaha", masa_berlaku_hari=365)
        self.pengajuan = Pengajuan.objects.create(
            warga=self.warga,
            jenis_surat=self.sku,
            wilayah=self.wilayah,
            keperluan="Kredit Usaha Rakyat",
            status=Pengajuan.StatusPengajuan.MENUNGGU_RT_RW
        )

    def test_mode_b_requires_proof_attachment(self):
        """Verifikasi Mode B WAJIB melampirkan file bukti komunikasi (§17)"""
        # Tanpa bukti file
        form_tanpa_file = ModeBApprovalForm(data={
            'keputusan': 'SETUJU',
            'catatan': 'Konfirmasi via telepon dengan ketua RT'
        })
        self.assertFalse(form_tanpa_file.is_valid())
        self.assertIn('lampiran_bukti', form_tanpa_file.errors)

        # Dengan bukti file
        dummy_file = SimpleUploadedFile("bukti_chat.jpg", b"dummy content", content_type="image/jpeg")
        form_lengkap = ModeBApprovalForm(
            data={
                'keputusan': 'SETUJU',
                'catatan': 'Konfirmasi via telepon dengan ketua RT'
            },
            files={'lampiran_bukti': dummy_file}
        )
        self.assertTrue(form_lengkap.is_valid())
