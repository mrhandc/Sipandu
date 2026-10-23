from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from apps.accounts.models import CustomUser, VerifikasiAkun, Wilayah
from apps.accounts.forms import WargaRegistrationForm, AdminVerifyAkunForm
from apps.accounts.decorators import admin_required
from apps.core.models import AuditLog, Notifikasi
from apps.core.services.whatsapp import send_whatsapp_to_user, send_whatsapp_to_role


def login_view(request):
    if request.user.is_authenticated:
        return redirect('core:dashboard')

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f"Selamat datang kembali, {user.get_full_name() or user.username}!")
            
            # Cek status akun warga (§10.2)
            if user.is_warga and user.status_akun != CustomUser.StatusAkun.AKTIF:
                return redirect('accounts:status_akun')
            return redirect('core:dashboard')
        else:
            messages.error(request, "Nama pengguna atau kata sandi tidak valid.")
    else:
        form = AuthenticationForm()

    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    logout(request)
    messages.info(request, "Anda telah berhasil keluar dari sistem.")
    return redirect('accounts:login')


def register_warga_view(request):
    if request.user.is_authenticated:
        return redirect('core:dashboard')

    if request.method == 'POST':
        form = WargaRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save(commit=False)
            user.role = CustomUser.Role.WARGA
            user.status_akun = CustomUser.StatusAkun.PENDING_VERIFIKASI
            user.set_password(form.cleaned_data['password'])
            user.save()

            # Simpan Verifikasi Identitas (§10.1)
            VerifikasiAkun.objects.create(
                user=user,
                foto_ktp=form.cleaned_data['foto_ktp'],
                foto_wajah=form.cleaned_data['foto_wajah'],
                status=CustomUser.StatusAkun.PENDING_VERIFIKASI
            )

            # Audit Log
            AuditLog.objects.create(
                actor=user,
                action="REGISTRASI_WARGA",
                module="accounts",
                details=f"Pendaftaran akun warga NIK: {user.nik}",
                ip_address=request.META.get('REMOTE_ADDR', '')
            )

            send_whatsapp_to_role(
                CustomUser.Role.ADMIN,
                (
                    f"🔔 *PENDAFTARAN WARGA BARU SIPANDU*\n\n"
                    f"Nama: *{user.get_full_name() or user.username}*\n"
                    f"NIK: {user.masked_nik}\n"
                    f"Wilayah: {user.wilayah or '-'}\n\n"
                    f"Silakan lakukan verifikasi KTP dan foto wajah melalui menu Admin Desa."
                )
            )

            login(request, user)
            messages.success(
                request,
                "Pendaftaran berhasil! Akun Anda sedang menunggu verifikasi KTP & wajah oleh Admin Desa."
            )
            return redirect('accounts:status_akun')
    else:
        form = WargaRegistrationForm()

    return render(request, 'accounts/register.html', {'form': form})


@login_required
def status_akun_view(request):
    """Halaman status verifikasi akun untuk warga (§10.2)"""
    verifikasi = getattr(request.user, 'verifikasi_identitas', None)
    return render(request, 'accounts/status_akun.html', {
        'verifikasi': verifikasi
    })


@admin_required
def admin_verifikasi_list_view(request):
    """Daftar warga yang menunggu verifikasi KTP & wajah oleh Admin Desa (§10.1, §23)"""
    pending_list = VerifikasiAkun.objects.filter(
        status=CustomUser.StatusAkun.PENDING_VERIFIKASI
    ).select_related('user', 'user__wilayah').order_by('-created_at')

    history_list = VerifikasiAkun.objects.exclude(
        status=CustomUser.StatusAkun.PENDING_VERIFIKASI
    ).select_related('user', 'user__wilayah').order_by('-verified_at')[:20]

    return render(request, 'accounts/admin_verifikasi_list.html', {
        'pending_list': pending_list,
        'history_list': history_list
    })


@admin_required
def admin_verifikasi_detail_view(request, pk):
    """
    Detail verifikasi KTP & wajah oleh Admin Desa (§10.1, §19 Data Privacy).
    Hanya Admin yang dapat mengakses foto KTP dan selfie ini.
    """
    item = get_object_or_404(VerifikasiAkun, pk=pk)
    user = item.user

    if request.method == 'POST':
        form = AdminVerifyAkunForm(request.POST)
        if form.is_valid():
            status = form.cleaned_data['status']
            catatan = form.cleaned_data['catatan']

            item.status = status
            item.catatan = catatan
            item.verified_by = request.user
            item.verified_at = timezone.now()
            item.save()

            user.status_akun = status
            if status == CustomUser.StatusAkun.DITOLAK:
                user.catatan_penolakan = catatan
            else:
                user.catatan_penolakan = ""
            user.save()

            # Buat notifikasi untuk warga
            if status == CustomUser.StatusAkun.AKTIF:
                Notifikasi.objects.create(
                    user=user,
                    judul="Akun Terverifikasi",
                    pesan="Selamat! Akun Anda telah berhasil diverifikasi oleh Admin Desa. Anda sekarang dapat mengajukan surat.",
                    link="/pengajuan/buat/"
                )
                wa_msg = (
                    f"Halo Bapak/Ibu *{user.get_full_name() or user.username}*,\n\n"
                    f"✅ *Selamat! Akun SIPANDU Anda Telah Terverifikasi & Aktif.*\n"
                    f"NIK: {user.masked_nik}\n\n"
                    f"Sekarang Anda dapat mengajukan permohonan surat keterangan desa secara digital melalui portal SIPANDU.\n\n"
                    f"Salam,\n_Pemerintah Desa Sukamaju_"
                )
                send_whatsapp_to_user(user, wa_msg)
            else:
                Notifikasi.objects.create(
                    user=user,
                    judul="Verifikasi Akun Ditolak",
                    pesan=f"Mohon maaf, verifikasi akun Anda ditolak dengan alasan: {catatan}",
                    link="/accounts/status/"
                )
                wa_msg = (
                    f"Halo Bapak/Ibu *{user.get_full_name() or user.username}*,\n\n"
                    f"⚠️ *Pemberitahuan: Verifikasi Akun SIPANDU Ditolak*\n"
                    f"Alasan: {catatan}\n\n"
                    f"Silakan periksa kembali foto KTP dan foto selfie wajah Anda melalui menu status akun SIPANDU.\n\n"
                    f"Salam,\n_Pemerintah Desa Sukamaju_"
                )
                send_whatsapp_to_user(user, wa_msg)

            # Audit Log
            AuditLog.objects.create(
                actor=request.user,
                action=f"VERIFIKASI_AKUN_{status}",
                module="accounts",
                details=f"Verifikasi identitas warga {user.username} (NIK: {user.nik}) diubah menjadi {status}. Catatan: {catatan}",
                ip_address=request.META.get('REMOTE_ADDR', '')
            )

            messages.success(request, f"Verifikasi akun {user.get_full_name() or user.username} berhasil disimpan ({status}).")
            return redirect('accounts:admin_verifikasi_list')
    else:
        form = AdminVerifyAkunForm(initial={'status': item.status, 'catatan': item.catatan})

    return render(request, 'accounts/admin_verifikasi_detail.html', {
        'item': item,
        'target_user': user,
        'form': form
    })
