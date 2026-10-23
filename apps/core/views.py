from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Q
from django.utils import timezone
from apps.accounts.models import CustomUser, VerifikasiAkun, Wilayah
from apps.pengajuan.models import Pengajuan
from apps.surat.models import Surat, JenisSurat
from apps.core.models import SystemConfig, Notifikasi, AuditLog
from apps.accounts.decorators import admin_required, petugas_required


@login_required
def dashboard_view(request):
    """
    Dashboard Terpusat dengan Tampilan Khusus per Role (§23).
    - Warga: total pengajuan, surat aktif, status pengajuan terkini
    - RT/RW, Sekdes, Kades: antrian tugas menunggu tindakan & riwayat
    - Admin: statistik sistem, verifikasi KTP tertunda, mode B tertunda, surat aktif
    """
    user = request.user

    if user.is_warga:
        pengajuan_list = Pengajuan.objects.filter(warga=user).select_related('jenis_surat').order_by('-created_at')[:5]
        surat_aktif = Surat.objects.filter(
            warga=user,
            status_surat=Surat.StatusSurat.AKTIF,
            tanggal_kadaluarsa__gte=timezone.now().date()
        ).select_related('jenis_surat')

        context = {
            'role': 'WARGA',
            'total_pengajuan': Pengajuan.objects.filter(warga=user).count(),
            'total_diproses': Pengajuan.objects.filter(warga=user).exclude(
                status__in=[Pengajuan.StatusPengajuan.DITERBITKAN, Pengajuan.StatusPengajuan.DITOLAK, Pengajuan.StatusPengajuan.DIBATALKAN]
            ).count(),
            'total_selesai': Surat.objects.filter(warga=user).count(),
            'surat_aktif': surat_aktif,
            'recent_pengajuan': pengajuan_list,
        }
        return render(request, 'core/dashboard_warga.html', context)

    elif user.is_rt_rw:
        antrian_count = 0
        if user.wilayah:
            antrian_count = Pengajuan.objects.filter(
                status=Pengajuan.StatusPengajuan.MENUNGGU_RT_RW,
                wilayah=user.wilayah
            ).count()
        recent_tasks = Pengajuan.objects.filter(
            wilayah=user.wilayah,
            status=Pengajuan.StatusPengajuan.MENUNGGU_RT_RW
        ).select_related('warga', 'jenis_surat')[:5]

        context = {
            'role': 'RT_RW',
            'antrian_count': antrian_count,
            'recent_tasks': recent_tasks,
            'wilayah': user.wilayah,
        }
        return render(request, 'core/dashboard_petugas.html', context)

    elif user.is_sekdes:
        antrian_count = Pengajuan.objects.filter(status=Pengajuan.StatusPengajuan.MENUNGGU_SEKDES).count()
        recent_tasks = Pengajuan.objects.filter(
            status=Pengajuan.StatusPengajuan.MENUNGGU_SEKDES
        ).select_related('warga', 'jenis_surat', 'wilayah')[:5]

        context = {
            'role': 'SEKDES',
            'antrian_count': antrian_count,
            'recent_tasks': recent_tasks,
        }
        return render(request, 'core/dashboard_petugas.html', context)

    elif user.is_kades:
        antrian_count = Pengajuan.objects.filter(status=Pengajuan.StatusPengajuan.MENUNGGU_KEPALA_DESA).count()
        recent_tasks = Pengajuan.objects.filter(
            status=Pengajuan.StatusPengajuan.MENUNGGU_KEPALA_DESA
        ).select_related('warga', 'jenis_surat', 'wilayah')[:5]

        context = {
            'role': 'KADES',
            'antrian_count': antrian_count,
            'recent_tasks': recent_tasks,
        }
        return render(request, 'core/dashboard_petugas.html', context)

    else:  # Admin Desa
        pending_verif_akun = VerifikasiAkun.objects.filter(status=CustomUser.StatusAkun.PENDING_VERIFIKASI).count()
        mode_b_pending = Pengajuan.objects.filter(status=Pengajuan.StatusPengajuan.MENUNGGU_RT_RW).count()
        total_warga = CustomUser.objects.filter(role=CustomUser.Role.WARGA).count()
        total_surat_terbit = Surat.objects.count()
        surat_aktif_count = Surat.objects.filter(status_surat=Surat.StatusSurat.AKTIF).count()

        recent_verifikasi = VerifikasiAkun.objects.filter(
            status=CustomUser.StatusAkun.PENDING_VERIFIKASI
        ).select_related('user', 'user__wilayah')[:5]

        recent_pengajuan = Pengajuan.objects.all().select_related('warga', 'jenis_surat', 'wilayah').order_by('-created_at')[:5]

        context = {
            'role': 'ADMIN',
            'pending_verif_akun': pending_verif_akun,
            'mode_b_pending': mode_b_pending,
            'total_warga': total_warga,
            'total_surat_terbit': total_surat_terbit,
            'surat_aktif_count': surat_aktif_count,
            'recent_verifikasi': recent_verifikasi,
            'recent_pengajuan': recent_pengajuan,
        }
        return render(request, 'core/dashboard_admin.html', context)


@login_required
def notifikasi_list_view(request):
    """Daftar notifikasi in-app untuk pengguna (§22)"""
    notif_list = Notifikasi.objects.filter(user=request.user)
    # Tandai semua sebagai dibaca
    notif_list.filter(is_read=False).update(is_read=True)

    return render(request, 'core/notifikasi_list.html', {
        'notifikasi_list': notif_list
    })


@admin_required
def system_config_view(request):
    """
    Manajemen SYSTEM_CONFIG oleh Admin Desa (§5.3, §13.2, §18).
    Admin dapat mengubah batas revisi dan threshold timeout tanpa deploy ulang kode.
    """
    configs = SystemConfig.objects.all().order_by('key')

    if request.method == 'POST':
        for config in configs:
            val = request.POST.get(f"config_{config.id}")
            if val is not None:
                config.value = val.strip()
                config.save()

        # Audit Log
        AuditLog.objects.create(
            actor=request.user,
            action="UPDATE_SYSTEM_CONFIG",
            module="core",
            details="Admin memperbarui konfigurasi sistem (SYSTEM_CONFIG)",
            ip_address=request.META.get('REMOTE_ADDR', '')
        )

        messages.success(request, "Konfigurasi sistem berhasil diperbarui.")
        return redirect('core:system_config')

    return render(request, 'core/system_config.html', {'configs': configs})


@admin_required
def audit_log_list_view(request):
    """Jejak Audit Trail Sistem untuk Admin Desa (§21)"""
    logs = AuditLog.objects.select_related('actor').order_by('-created_at')[:100]
    return render(request, 'core/audit_log_list.html', {'logs': logs})


@petugas_required
def laporan_pelayanan_view(request):
    """
    Laporan Pelayanan Surat Administrasi Desa (§23, §25 RBAC).
    Dapat diakses oleh Sekdes, Kades, dan Admin.
    """
    if request.user.is_rt_rw:
        messages.error(request, "Fitur laporan hanya dapat diakses oleh Sekdes, Kades, atau Admin.")
        return redirect('core:dashboard')

    jenis_list = JenisSurat.objects.all()
    stats_jenis = Pengajuan.objects.values('jenis_surat__nama').annotate(total=Count('id')).order_by('-total')
    stats_status = Pengajuan.objects.values('status').annotate(total=Count('id')).order_by('-total')
    total_pengajuan = Pengajuan.objects.count()
    total_selesai = Pengajuan.objects.filter(status=Pengajuan.StatusPengajuan.DITERBITKAN).count()
    total_ditolak = Pengajuan.objects.filter(status=Pengajuan.StatusPengajuan.DITOLAK).count()

    return render(request, 'core/laporan_pelayanan.html', {
        'stats_jenis': stats_jenis,
        'stats_status': stats_status,
        'total_pengajuan': total_pengajuan,
        'total_selesai': total_selesai,
        'total_ditolak': total_ditolak,
    })


@admin_required
def whatsapp_test_view(request):
    """Halaman pengujian integrasi gateway WhatsApp Fonnte.com oleh Admin Desa"""
    from apps.core.services.whatsapp import send_whatsapp_message, get_fonnte_token, is_fonnte_enabled

    token = get_fonnte_token()
    is_enabled = is_fonnte_enabled()
    has_token = bool(token)
    masked_token = f"{token[:6]}...{token[-4:]}" if len(token) > 10 else ("Tersedia" if token else "Belum Disetel")

    test_result = None

    if request.method == 'POST':
        target_phone = request.POST.get('target_phone', '').strip()
        test_message = request.POST.get('test_message', '').strip()

        if not target_phone or not test_message:
            messages.error(request, "Nomor WhatsApp dan pesan pengujian wajib diisi.")
        else:
            success, detail = send_whatsapp_message(target_phone, test_message, user=request.user)
            test_result = {
                'success': success,
                'detail': detail,
                'target': target_phone,
            }
            if success:
                messages.success(request, f"Pesan WhatsApp berhasil dikirim ke {target_phone} via Fonnte!")
            else:
                messages.warning(request, f"Hasil pengiriman: {detail}")

    return render(request, 'core/whatsapp_test.html', {
        'has_token': has_token,
        'masked_token': masked_token,
        'is_enabled': is_enabled,
        'test_result': test_result,
    })

