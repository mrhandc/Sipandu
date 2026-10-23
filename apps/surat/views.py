import os
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, Http404, FileResponse
from django.contrib import messages
from django.utils import timezone
from django.conf import settings
from apps.surat.models import Surat, JenisSurat
from apps.accounts.decorators import warga_required, admin_required, petugas_required
from apps.core.models import AuditLog


def verifikasi_publik_view(request, uuid):
    """
    Halaman Publik Verifikasi Keaslian Surat Digital SIPANDU (§14).
    Dapat diakses oleh siapa saja via scan QR Code.
    """
    surat = get_object_or_404(Surat, kode_verifikasi=uuid)
    surat.update_expiration_status()

    return render(request, 'surat/verifikasi_publik.html', {
        'surat': surat,
        'is_valid': surat.is_currently_valid
    })


@warga_required
def daftar_surat_saya_view(request):
    """Daftar surat yang telah diterbitkan untuk warga login (§15.3, §23)"""
    surat_list = Surat.objects.filter(warga=request.user).select_related('jenis_surat', 'pengajuan')
    for s in surat_list:
        s.update_expiration_status()

    return render(request, 'surat/daftar_surat_saya.html', {
        'surat_list': surat_list
    })


@login_required
def download_pdf_view(request, pk):
    """Unduh file PDF surat resmi"""
    surat = get_object_or_404(Surat, pk=pk)

    # Permission check: Warga hanya bisa download suratnya sendiri, Petugas bisa lihat
    if request.user.is_warga and surat.warga != request.user:
        messages.error(request, "Anda tidak memiliki hak untuk mengunduh dokumen ini.")
        return redirect('surat:surat_saya')

    if not surat.file_pdf or not os.path.exists(surat.file_pdf.path):
        raise Http404("Dokumen PDF belum digenerate atau file tidak ditemukan.")

    return FileResponse(open(surat.file_pdf.path, 'rb'), content_type='application/pdf', filename=os.path.basename(surat.file_pdf.name))


@admin_required
def admin_daftar_surat_view(request):
    """Daftar seluruh surat terbit untuk Admin Desa (§23)"""
    surat_list = Surat.objects.all().select_related('warga', 'jenis_surat', 'pengajuan').order_by('-tanggal_terbit')
    for s in surat_list:
        s.update_expiration_status()

    return render(request, 'surat/admin_daftar_surat.html', {
        'surat_list': surat_list
    })


@admin_required
def admin_batalkan_surat_view(request, pk):
    """
    Jalur Pengecualian Admin Desa (§15.4):
    Membatalkan status surat lama menjadi DIBATALKAN secara manual
    dengan catatan wajib di AUDIT_LOG, sehingga warga dapat mengajukan surat baru.
    """
    surat = get_object_or_404(Surat, pk=pk)

    if request.method == 'POST':
        alasan = request.POST.get('alasan_pembatalan', '').strip()
        if not alasan:
            messages.error(request, "Alasan pembatalan wajib diisi untuk catatan audit (§15.4).")
            return redirect('surat:admin_daftar_surat')

        surat.status_surat = Surat.StatusSurat.DIBATALKAN
        surat.catatan_pembatalan = alasan
        surat.dibatalkan_oleh = request.user
        surat.dibatalkan_pada = timezone.now()
        surat.save()

        # Audit Log
        AuditLog.objects.create(
            actor=request.user,
            action="PENGEQUALIAN_BATAL_SURAT",
            module="surat",
            details=f"Admin membatalkan surat #{surat.nomor_surat} milik {surat.warga.username}. Alasan: {alasan}",
            ip_address=request.META.get('REMOTE_ADDR', '')
        )

        messages.success(request, f"Surat {surat.nomor_surat} berhasil dibatalkan. Warga sekarang dapat mengajukan surat baru.")
        return redirect('surat:admin_daftar_surat')

    return render(request, 'surat/admin_batalkan_surat_confirm.html', {'surat': surat})
