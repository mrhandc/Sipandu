import re
from django import forms
from django.core.exceptions import ValidationError
from apps.accounts.models import CustomUser, Wilayah, VerifikasiAkun


def validate_indonesia_phone(value):
    if not value:
        return
    cleaned = re.sub(r'[\s\-]', '', value)
    if not re.match(r'^(\+62|62|08)[0-9]{8,13}$', cleaned):
        raise ValidationError('Format nomor telepon tidak valid. Gunakan format Indonesia (misal: 08123456789 atau +628123456789).')


def validate_image_file(file):
    max_mb = 2
    if file.size > max_mb * 1024 * 1024:
        raise ValidationError(f'Ukuran file maksimal {max_mb}MB.')
    ext = file.name.split('.')[-1].lower()
    if ext not in ['jpg', 'jpeg', 'png']:
        raise ValidationError('Format foto harus JPG, JPEG, atau PNG.')


class WargaRegistrationForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Minimal 6 karakter'}),
        label="Kata Sandi",
        min_length=6
    )
    password_confirm = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Ulangi kata sandi'}),
        label="Konfirmasi Kata Sandi"
    )
    foto_ktp = forms.ImageField(
        label="Foto KTP Asli",
        help_text="Pastikan seluruh sisi KTP terlihat jelas dan tidak buram (Maks. 2MB)",
        widget=forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
        validators=[validate_image_file]
    )
    foto_wajah = forms.ImageField(
        label="Foto Wajah / Pas Foto (Selfie)",
        help_text="Foto wajah tampak depan dengan pencahayaan jelas (Maks. 2MB)",
        widget=forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
        validators=[validate_image_file]
    )

    class Meta:
        model = CustomUser
        fields = ['username', 'first_name', 'nik', 'email', 'no_hp', 'wilayah', 'alamat']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username login'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nama lengkap sesuai KTP'}),
            'nik': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '16 digit NIK', 'maxlength': '16'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'nama@email.com'}),
            'no_hp': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '08xxxxxxxxxx'}),
            'wilayah': forms.Select(attrs={'class': 'form-select'}),
            'alamat': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Alamat jalan, nomor rumah, gang'}),
        }
        labels = {
            'first_name': 'Nama Lengkap Sesuai KTP',
            'nik': 'Nomor Induk Kependudukan (NIK)',
        }

    def clean_nik(self):
        nik = self.cleaned_data.get('nik', '').strip()
        if not re.match(r'^\d{16}$', nik):
            raise ValidationError('NIK wajib terdiri dari tepat 16 digit angka (§5.1).')
        if CustomUser.objects.filter(nik=nik).exists():
            raise ValidationError('NIK ini sudah terdaftar dalam sistem.')
        return nik

    def clean_first_name(self):
        nama = self.cleaned_data.get('first_name', '').strip()
        if not nama:
            raise ValidationError('Nama lengkap wajib diisi.')
        if not re.match(r'^[A-Za-z\s\.,\'\-\`]+$', nama):
            raise ValidationError('Nama hanya boleh mengandung huruf, spasi, dan tanda baca umum.')
        return nama

    def clean_alamat(self):
        alamat = self.cleaned_data.get('alamat', '').strip()
        if len(alamat) < 5:
            raise ValidationError('Alamat domisili minimal 5 karakter.')
        return alamat

    def clean_no_hp(self):
        no_hp = self.cleaned_data.get('no_hp', '').strip()
        validate_indonesia_phone(no_hp)
        return no_hp

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get('password')
        p2 = cleaned_data.get('password_confirm')
        if p1 and p2 and p1 != p2:
            self.add_error('password_confirm', 'Konfirmasi kata sandi tidak cocok.')
        return cleaned_data


class AdminVerifyAkunForm(forms.Form):
    status = forms.ChoiceField(
        choices=[
            (CustomUser.StatusAkun.AKTIF, 'Setujui & Aktifkan Akun (AKTIF)'),
            (CustomUser.StatusAkun.DITOLAK, 'Tolak Verifikasi (DITOLAK)'),
        ],
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'})
    )
    catatan = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Wajib diisi jika menolak pendaftaran'}),
        label="Catatan / Alasan"
    )

    def clean(self):
        cleaned_data = super().clean()
        status = cleaned_data.get('status')
        catatan = cleaned_data.get('catatan', '').strip()
        if status == CustomUser.StatusAkun.DITOLAK and not catatan:
            self.add_error('catatan', 'Catatan alasan wajib diisi saat menolak verifikasi (§10.1).')
        return cleaned_data
