from django import forms
from django.core.exceptions import ValidationError
from apps.approval.models import ApprovalHistory
from apps.pengajuan.models import Pengajuan


class ApprovalActionForm(forms.Form):
    KEPUTUSAN_CHOICES = [
        ('SETUJU', 'Setujui Permohonan (Lanjut ke Tahap Berikutnya)'),
        ('REVISI', 'Perlu Revisi Dokumen/Data (Kembalikan ke Warga)'),
        ('TOLAK', 'Tolak Permohonan (Keputusan Final)'),
    ]

    keputusan = forms.ChoiceField(
        choices=KEPUTUSAN_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'})
    )
    catatan = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Wajib diisi jika memilih Perlu Revisi atau Tolak (§13.1)'}),
        label="Catatan / Alasan Keputusan"
    )

    def clean(self):
        cleaned_data = super().clean()
        keputusan = cleaned_data.get('keputusan')
        catatan = cleaned_data.get('catatan', '').strip()

        # Aturan PRD §13.1: Setiap keputusan PERLU_REVISI atau DITOLAK wajib disertai catatan alasan
        if keputusan in ['REVISI', 'TOLAK'] and not catatan:
            self.add_error('catatan', 'Catatan alasan wajib diisi saat memilih Perlu Revisi atau Tolak (§13.1).')

        return cleaned_data


class ModeBApprovalForm(forms.Form):
    """
    Form Verifikasi Terwakilkan oleh Admin untuk RT/RW (§17 Mode B).
    Wajib melampirkan bukti komunikasi (foto/screenshot/tanda tangan basah).
    """
    KEPUTUSAN_CHOICES = [
        ('SETUJU', 'Setujui (Sesuai Konfirmasi RT/RW)'),
        ('REVISI', 'Perlu Revisi (Sesuai Konfirmasi RT/RW)'),
        ('TOLAK', 'Tolak (Sesuai Konfirmasi RT/RW)'),
    ]

    keputusan = forms.ChoiceField(
        choices=KEPUTUSAN_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'})
    )
    catatan = forms.CharField(
        required=True,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Uraikan hasil komunikasi/konfirmasi dengan Ketua RT/RW terkait'}),
        label="Catatan Hasil Verifikasi Offline"
    )
    lampiran_bukti = forms.FileField(
        required=True,
        widget=forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*,.pdf'}),
        label="Lampiran Bukti Komunikasi (§17)",
        help_text="Wajib mengunggah screenshot percakapan WhatsApp/SMS, scan form tanda tangan basah, atau bukti dokumentasi lain."
    )
