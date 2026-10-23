from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from apps.pengajuan.models import Pengajuan, DokumenPengajuan, Persyaratan
from apps.surat.models import JenisSurat, Surat
from apps.accounts.forms import validate_image_file


def validate_doc_file(file):
    max_mb = 2
    if file.size > max_mb * 1024 * 1024:
        raise ValidationError(f'Ukuran file lampiran maksimal {max_mb}MB (§5.1).')
    ext = file.name.split('.')[-1].lower()
    if ext not in ['pdf', 'jpg', 'jpeg', 'png']:
        raise ValidationError('Format file yang diperbolehkan hanya PDF, JPG, JPEG, atau PNG.')


class PengajuanCreateForm(forms.ModelForm):
    # Field opsional sesuai jenis surat
    nama_usaha = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nama Usaha / Toko (Khusus SKU)'}))
    jenis_usaha = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Bidang Usaha misal: Kuliner, Perdagangan'}))
    penghasilan_bulanan = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Estimasi Penghasilan per Bulan (Khusus SKTM)'}))
    tanggungan = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Jumlah Anggota Keluarga Tanggungan'}))

    class Meta:
        model = Pengajuan
        fields = ['jenis_surat', 'keperluan']
        widgets = {
            'jenis_surat': forms.Select(attrs={'class': 'form-select', 'id': 'select-jenis-surat'}),
            'keperluan': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Jelaskan tujuan dan keperluan pengajuan surat keterangan ini'}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        self.fields['jenis_surat'].queryset = JenisSurat.objects.filter(is_active=True)

    def clean(self):
        cleaned_data = super().clean()
        jenis_surat = cleaned_data.get('jenis_surat')

        if jenis_surat and self.user:
            # Aturan Bisnis §15.2: Periksa surat sejenis yang masih AKTIF
            surat_aktif = Surat.objects.filter(
                warga=self.user,
                jenis_surat=jenis_surat,
                status_surat=Surat.StatusSurat.AKTIF,
                tanggal_kadaluarsa__gte=timezone.now().date()
            ).first()

            if surat_aktif:
                raise ValidationError(
                    f"Anda masih memiliki {jenis_surat.nama} yang masih berlaku "
                    f"(Nomor: {surat_aktif.nomor_surat}, Berlaku sampai: {surat_aktif.tanggal_kadaluarsa.strftime('%d-%m-%Y')}). "
                    f"Pengajuan surat sejenis tidak diizinkan selama surat sebelumnya masih aktif (§15.2)."
                )

        return cleaned_data


class PengajuanRevisiForm(forms.ModelForm):
    class Meta:
        model = Pengajuan
        fields = ['keperluan']
        widgets = {
            'keperluan': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }
