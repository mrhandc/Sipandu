from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from apps.pengajuan.models import Pengajuan, DokumenPengajuan, Persyaratan
from apps.pengajuan.forms import PengajuanCreateForm, PengajuanRevisiForm, validate_doc_file
from apps.accounts.decorators import warga_required
from apps.approval.models import ApprovalHistory
from apps.core.models import SystemConfig, Notifikasi, AuditLog
from apps.accounts.models import CustomUser
from apps.core.services.whatsapp import send_whatsapp_to_user, send_whatsapp_to_role


@warga_required
def pengajuan_list_view(request):
    """Daftar riwayat dan status pengajuan surat warga (§23 Dashboard Warga)"""
    pengajuan_list = Pengajuan.objects.filter(warga=request.user).select_related('jenis_surat', 'wilayah').order_by('-created_at')
    return render(request, 'pengajuan/pengajuan_list.html', {
        'pengajuan_list': pengajuan_list
    })


@warga_required
def pengajuan_create_view(request):
    """Formulir Pengajuan Surat Baru oleh Warga (§11.2, §15.2)"""
    warga = request.user
    if not warga.wilayah:
        messages.error(request, "Akun Anda belum terhubung dengan wilayah RT/RW. Silakan hubungi Admin.")
        return redirect('pengajuan:pengajuan_list')

    if request.method == 'POST':
        form = PengajuanCreateForm(request.POST, user=warga)
        if form.is_valid():
            pengajuan = form.save(commit=False)
            pengajuan.warga = warga
            pengajuan.wilayah = warga.wilayah
            pengajuan.submitted_at = timezone.now()

            # Simpan data tambahan spesifik
            extra_data = {}
            if form.cleaned_data.get('nama_usaha'):
                extra_data['nama_usaha'] = form.cleaned_data['nama_usaha']
            if form.cleaned_data.get('jenis_usaha'):
                extra_data['jenis_usaha'] = form.cleaned_data['jenis_usaha']
            if form.cleaned_data.get('penghasilan_bulanan'):
                extra_data['penghasilan_bulanan'] = form.cleaned_data['penghasilan_bulanan']
            if form.cleaned_data.get('tanggungan'):
                extra_data['tanggungan'] = form.cleaned_data['tanggungan']
            pengajuan.data_tambahan = extra_data

            # Validasi data & dokumen sistem (§11.2 Tahap 2) -> Status masuk ke antrian RT/RW
            pengajuan.status = Pengajuan.StatusPengajuan.MENUNGGU_RT_RW
            pengajuan.save()

            # Upload Dokumen Lampiran yang diinputkan warga
            files = request.FILES
            for field_name, uploaded_file in files.items():
                if field_name.startswith('dokumen_'):
                    try:
                        validate_doc_file(uploaded_file)
                        doc_name = field_name.replace('dokumen_', '').replace('_', ' ').capitalize()
                        DokumenPengajuan.objects.create(
                            pengajuan=pengajuan,
                            nama_dokumen=doc_name,
                            file=uploaded_file
                        )
                    except Exception as e:
                        messages.warning(request, f"File {uploaded_file.name} bermasalah: {e}")

            # Catat Riwayat Approval awal (Audit Trail §21)
            ApprovalHistory.objects.create(
                pengajuan=pengajuan,
                actor=warga,
                action=ApprovalHistory.ActionType.MENGAJUKAN,
                status_dari=Pengajuan.StatusPengajuan.DIAJUKAN,
                status_ke=Pengajuan.StatusPengajuan.MENUNGGU_RT_RW,
                catatan="Pengajuan baru dikirimkan oleh pemohon."
            )

            # Notifikasi ke RT/RW wilayah terkait
            rt_rw_users = CustomUser.objects.filter(role=CustomUser.Role.RT_RW, wilayah=warga.wilayah)
            for petugas in rt_rw_users:
                Notifikasi.objects.create(
                    user=petugas,
                    judul=f"Pengajuan Baru: {pengajuan.jenis_surat.kode}",
                    pesan=f"Warga {warga.get_full_name()} (RT {warga.wilayah.rt}/RW {warga.wilayah.rw}) mengajukan {pengajuan.jenis_surat.nama}.",
                    link=f"/approval/detail/{pengajuan.id}/"
                )
                wa_rt = (
                    f"Halo Bapak/Ibu Pengurus *RT {warga.wilayah.rt}/RW {warga.wilayah.rw}*,\n\n"
                    f"📩 *Permohonan Surat Baru Masuk SIPANDU:*\n"
                    f"- ID: #{pengajuan.id}\n"
                    f"- Jenis: *{pengajuan.jenis_surat.nama}*\n"
                    f"- Pemohon: {warga.get_full_name()} (NIK: {warga.masked_nik})\n"
                    f"- Keperluan: {pengajuan.keperluan}\n\n"
                    f"Silakan periksa dan verifikasi permohonan melalui portal SIPANDU."
                )
                send_whatsapp_to_user(petugas, wa_rt)

            send_whatsapp_to_role(
                CustomUser.Role.ADMIN,
                (
                    f"🔔 *PENGAJUAN SURAT BARU SIPANDU*\n\n"
                    f"Pengajuan #{pengajuan.id} dari *{warga.get_full_name()}* "
                    f"({pengajuan.jenis_surat.nama}) telah masuk ke antrian "
                    f"RT {warga.wilayah.rt}/RW {warga.wilayah.rw}.\n"
                    f"Status: *Menunggu Verifikasi RT/RW*."
                )
            )

            # Notifikasi WhatsApp ke Pemohon (Warga)
            wa_warga = (
                f"Halo Bapak/Ibu *{warga.get_full_name()}*,\n\n"
                f"📝 Permohonan surat *{pengajuan.jenis_surat.nama}* (#{pengajuan.id}) berhasil dikirimkan.\n"
                f"Keperluan: {pengajuan.keperluan}\n"
                f"Status: *Menunggu Verifikasi Ketua RT/RW*.\n\n"
                f"Anda dapat memantau perkembangan status permohonan secara real-time di portal SIPANDU.\n"
                f"_Pemerintah Desa Sukamaju_"
            )
            send_whatsapp_to_user(warga, wa_warga)

            messages.success(request, f"Pengajuan {pengajuan.jenis_surat.nama} berhasil dikirim dan kini menunggu verifikasi Ketua RT/RW.")
            return redirect('pengajuan:pengajuan_detail', pk=pengajuan.id)
    else:
        form = PengajuanCreateForm(user=warga)

    persyaratan_list = Persyaratan.objects.select_related('jenis_surat')
    return render(request, 'pengajuan/pengajuan_create.html', {
        'form': form,
        'persyaratan_list': persyaratan_list
    })


@warga_required
def pengajuan_detail_view(request, pk):
    """Lihat detail pengajuan, progress tracking bar, lampiran & riwayat persetujuan (§22)"""
    pengajuan = get_object_or_404(Pengajuan, pk=pk, warga=request.user)
    dokumen_list = pengajuan.dokumen_lampiran.all()
    history_list = pengajuan.approval_history.select_related('actor').order_by('created_at')

    max_revisi = SystemConfig.get_int('MAX_REVISION_LIMIT', 3)

    return render(request, 'pengajuan/pengajuan_detail.html', {
        'pengajuan': pengajuan,
        'dokumen_list': dokumen_list,
        'history_list': history_list,
        'max_revisi': max_revisi
    })


@warga_required
def pengajuan_revisi_view(request, pk):
    """
    Alur Revisi oleh Warga (§13).
    Pengajuan yang sama diedit (tidak buat record baru), histori tersimpan di APPROVAL_HISTORY.
    Maksimal revisi dibatasi (§13.2).
    """
    pengajuan = get_object_or_404(Pengajuan, pk=pk, warga=request.user)

    if not pengajuan.is_in_revision:
        messages.warning(request, "Pengajuan ini tidak dalam status perlu revisi.")
        return redirect('pengajuan:pengajuan_detail', pk=pengajuan.id)

    max_revisi = SystemConfig.get_int('MAX_REVISION_LIMIT', 3)

    # Cek apakah sudah melebihi batas revisi maksimal (§13.2)
    # Revisi ke-4 -> sistem memaksa status menjadi DITOLAK otomatis
    if pengajuan.jumlah_revisi >= max_revisi:
        status_lama = pengajuan.status
        pengajuan.status = Pengajuan.StatusPengajuan.DITOLAK
        pengajuan.catatan_terakhir = "Melebihi batas revisi maksimal."
        pengajuan.save()

        ApprovalHistory.objects.create(
            pengajuan=pengajuan,
            actor=request.user,
            action=ApprovalHistory.ActionType.MENOLAK,
            status_dari=status_lama,
            status_ke=Pengajuan.StatusPengajuan.DITOLAK,
            catatan="Sistem otomatis menolak: melebihi batas revisi maksimal (§13.2)."
        )
        messages.error(request, "Pengajuan ditolak otomatis oleh sistem karena telah melebihi batas revisi maksimal.")
        return redirect('pengajuan:pengajuan_detail', pk=pengajuan.id)

    if request.method == 'POST':
        form = PengajuanRevisiForm(request.POST, instance=pengajuan)
        if form.is_valid():
            pengajuan = form.save(commit=False)
            status_lama = pengajuan.status
            pengajuan.jumlah_revisi += 1

            # Kembalikan ke antrian tahap yang sama (§12 & §13):
            # PERLU_REVISI_* -> warga edit -> kembali ke antrian tahap yang sama
            if status_lama == Pengajuan.StatusPengajuan.PERLU_REVISI_RT_RW:
                target_status = Pengajuan.StatusPengajuan.MENUNGGU_RT_RW
            elif status_lama == Pengajuan.StatusPengajuan.PERLU_REVISI_SEKDES:
                target_status = Pengajuan.StatusPengajuan.MENUNGGU_SEKDES
            elif status_lama == Pengajuan.StatusPengajuan.PERLU_REVISI_KADES:
                target_status = Pengajuan.StatusPengajuan.MENUNGGU_KEPALA_DESA
            else:
                target_status = Pengajuan.StatusPengajuan.MENUNGGU_RT_RW

            pengajuan.status = target_status
            pengajuan.save()

            # Upload dokumen revisi baru bila ada
            for field_name, uploaded_file in request.FILES.items():
                if field_name.startswith('dokumen_'):
                    validate_doc_file(uploaded_file)
                    DokumenPengajuan.objects.create(
                        pengajuan=pengajuan,
                        nama_dokumen=f"Revisi-{uploaded_file.name}",
                        file=uploaded_file
                    )

            # Catat ke Riwayat Approval (§13, §21)
            ApprovalHistory.objects.create(
                pengajuan=pengajuan,
                actor=request.user,
                action=ApprovalHistory.ActionType.MEREVISI,
                status_dari=status_lama,
                status_ke=target_status,
                catatan=f"Warga mengirimkan perbaikan dokumen/data (Revisi ke-{pengajuan.jumlah_revisi})."
            )

            # Notifikasi WhatsApp ke Warga
            wa_warga_rev = (
                f"Halo Bapak/Ibu *{request.user.get_full_name()}*,\n\n"
                f"🔄 Perbaikan berkas permohonan *{pengajuan.jenis_surat.nama}* (#{pengajuan.id}) revisi ke-{pengajuan.jumlah_revisi} telah berhasil dikirim kembali.\n"
                f"Status: Menunggu verifikasi ulang oleh petugas.\n"
                f"_Pemerintah Desa Sukamaju_"
            )
            send_whatsapp_to_user(request.user, wa_warga_rev)

            # Notifikasi WhatsApp ke Petugas terkait
            wa_petugas_rev = (
                f"Halo Petugas SIPANDU,\n\n"
                f"🔄 Warga *{request.user.get_full_name()}* telah mengirimkan perbaikan berkas untuk pengajuan *{pengajuan.jenis_surat.nama}* (#{pengajuan.id}).\n"
                f"Silakan periksa kembali pada antrian SIPANDU."
            )
            if target_status == Pengajuan.StatusPengajuan.MENUNGGU_RT_RW:
                send_whatsapp_to_role(CustomUser.Role.RT_RW, wa_petugas_rev, wilayah=pengajuan.wilayah)
            elif target_status == Pengajuan.StatusPengajuan.MENUNGGU_SEKDES:
                send_whatsapp_to_role(CustomUser.Role.SEKDES, wa_petugas_rev)
            elif target_status == Pengajuan.StatusPengajuan.MENUNGGU_KEPALA_DESA:
                send_whatsapp_to_role(CustomUser.Role.KADES, wa_petugas_rev)

            messages.success(request, f"Revisi ke-{pengajuan.jumlah_revisi} berhasil dikirim kembali ke antrian verifikasi.")
            return redirect('pengajuan:pengajuan_detail', pk=pengajuan.id)
    else:
        form = PengajuanRevisiForm(instance=pengajuan)

    return render(request, 'pengajuan/pengajuan_revisi.html', {
        'form': form,
        'pengajuan': pengajuan,
        'max_revisi': max_revisi,
        'sisa_revisi': max(0, max_revisi - pengajuan.jumlah_revisi)
    })


@warga_required
def pengajuan_batal_view(request, pk):
    """
    Pembatalan Pengajuan oleh Warga (§16).
    Hanya diizinkan selama status belum masuk MENUNGGU_KEPALA_DESA atau lebih lanjut.
    """
    pengajuan = get_object_or_404(Pengajuan, pk=pk, warga=request.user)

    if not pengajuan.can_be_cancelled_by_warga:
        messages.error(
            request,
            "Pengajuan sudah masuk tahap persetujuan Kepala Desa atau telah selesai, "
            "sehingga tidak dapat dibatalkan langsung oleh warga (§16). Hubungi Admin Desa."
        )
        return redirect('pengajuan:pengajuan_detail', pk=pengajuan.id)

    if request.method == 'POST':
        alasan = request.POST.get('alasan_batal', '').strip()
        status_lama = pengajuan.status
        pengajuan.status = Pengajuan.StatusPengajuan.DIBATALKAN
        pengajuan.catatan_terakhir = f"Dibatalkan oleh pemohon: {alasan}"
        pengajuan.save()

        ApprovalHistory.objects.create(
            pengajuan=pengajuan,
            actor=request.user,
            action=ApprovalHistory.ActionType.MEMBATALKAN,
            status_dari=status_lama,
            status_ke=Pengajuan.StatusPengajuan.DIBATALKAN,
            catatan=f"Dibatalkan sendiri oleh warga. Alasan: {alasan}"
        )

        wa_batal = (
            f"Halo Bapak/Ibu *{request.user.get_full_name()}*,\n\n"
            f"❌ Permohonan surat *{pengajuan.jenis_surat.nama}* (#{pengajuan.id}) telah DIBATALKAN.\n"
            f"Alasan: {alasan}\n\n"
            f"_Pemerintah Desa Sukamaju_"
        )
        send_whatsapp_to_user(request.user, wa_batal)
        send_whatsapp_to_role(
            CustomUser.Role.ADMIN,
            (
                f"❌ *PENGAJUAN DIBATALKAN WARGA*\n\n"
                f"Pengajuan #{pengajuan.id} ({pengajuan.jenis_surat.nama}) "
                f"milik *{request.user.get_full_name()}* telah dibatalkan.\n"
                f"Alasan: {alasan}"
            )
        )

        messages.info(request, "Pengajuan surat berhasil dibatalkan.")
        return redirect('pengajuan:pengajuan_list')

    return render(request, 'pengajuan/pengajuan_batal_confirm.html', {'pengajuan': pengajuan})
