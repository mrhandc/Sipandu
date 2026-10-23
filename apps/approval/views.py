from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from apps.accounts.models import CustomUser
from apps.pengajuan.models import Pengajuan
from apps.approval.models import ApprovalHistory
from apps.approval.forms import ApprovalActionForm, ModeBApprovalForm
from apps.accounts.decorators import petugas_required, admin_required
from apps.core.models import Notifikasi, AuditLog, SystemConfig
from apps.surat.services import terbitkan_surat_digital
from apps.core.services.whatsapp import send_whatsapp_to_user, send_whatsapp_to_role


@petugas_required
def approval_queue_view(request):
    """
    Antrian Masuk Verifikasi & Approval per Role (§23 Dashboard Petugas, §25 RBAC).
    - RT/RW: hanya melihat pengajuan di wilayahnya yang status MENUNGGU_RT_RW
    - Sekdes: melihat MENUNGGU_SEKDES
    - Kades: melihat MENUNGGU_KEPALA_DESA
    - Admin: melihat seluruh antrian dan Mode B
    """
    user = request.user
    role = user.role

    if user.is_rt_rw:
        if not user.wilayah:
            messages.warning(request, "Akun RT/RW Anda belum memiliki pemetaan wilayah.")
            antrian = Pengajuan.objects.none()
        else:
            antrian = Pengajuan.objects.filter(
                status=Pengajuan.StatusPengajuan.MENUNGGU_RT_RW,
                wilayah=user.wilayah
            )
        riwayat = Pengajuan.objects.filter(wilayah=user.wilayah).exclude(
            status=Pengajuan.StatusPengajuan.MENUNGGU_RT_RW
        ).order_by('-updated_at')[:20]

    elif user.is_sekdes:
        antrian = Pengajuan.objects.filter(status=Pengajuan.StatusPengajuan.MENUNGGU_SEKDES)
        riwayat = Pengajuan.objects.filter(
            status__in=[
                Pengajuan.StatusPengajuan.MENUNGGU_KEPALA_DESA,
                Pengajuan.StatusPengajuan.PERLU_REVISI_SEKDES,
                Pengajuan.StatusPengajuan.DITERBITKAN,
                Pengajuan.StatusPengajuan.DITOLAK
            ]
        ).order_by('-updated_at')[:20]

    elif user.is_kades:
        antrian = Pengajuan.objects.filter(status=Pengajuan.StatusPengajuan.MENUNGGU_KEPALA_DESA)
        riwayat = Pengajuan.objects.filter(
            status__in=[
                Pengajuan.StatusPengajuan.DISETUJUI,
                Pengajuan.StatusPengajuan.DITERBITKAN,
                Pengajuan.StatusPengajuan.PERLU_REVISI_KADES,
                Pengajuan.StatusPengajuan.DITOLAK
            ]
        ).order_by('-updated_at')[:20]

    else:  # Admin
        antrian = Pengajuan.objects.exclude(
            status__in=[
                Pengajuan.StatusPengajuan.DITERBITKAN,
                Pengajuan.StatusPengajuan.DITOLAK,
                Pengajuan.StatusPengajuan.DIBATALKAN
            ]
        )
        riwayat = Pengajuan.objects.filter(
            status__in=[
                Pengajuan.StatusPengajuan.DITERBITKAN,
                Pengajuan.StatusPengajuan.DITOLAK,
                Pengajuan.StatusPengajuan.DIBATALKAN
            ]
        ).order_by('-updated_at')[:30]

    antrian = antrian.select_related('warga', 'jenis_surat', 'wilayah').order_by('created_at')

    return render(request, 'approval/approval_queue.html', {
        'antrian': antrian,
        'riwayat': riwayat,
        'role': role
    })


@petugas_required
def approval_detail_view(request, pk):
    """
    Halaman Aksi Verifikasi / Approval oleh Petugas (§11.2, §13.1, §14).
    """
    pengajuan = get_object_or_404(Pengajuan.objects.select_related('warga', 'jenis_surat', 'wilayah'), pk=pk)
    user = request.user

    # Cek hak otorisasi akses
    if user.is_rt_rw and pengajuan.wilayah != user.wilayah:
        messages.error(request, "Anda hanya dapat memverifikasi pengajuan dari wilayah RT/RW Anda.")
        return redirect('approval:queue')

    # Cek apakah pengajuan saat ini berada pada tahap user
    can_act = False
    if user.is_rt_rw and pengajuan.status == Pengajuan.StatusPengajuan.MENUNGGU_RT_RW:
        can_act = True
    elif user.is_sekdes and pengajuan.status == Pengajuan.StatusPengajuan.MENUNGGU_SEKDES:
        can_act = True
    elif user.is_kades and pengajuan.status == Pengajuan.StatusPengajuan.MENUNGGU_KEPALA_DESA:
        can_act = True
    elif user.is_admin_desa and pengajuan.status == Pengajuan.StatusPengajuan.MENUNGGU_RT_RW:
        # Admin dapat melakukan Mode B (§17)
        can_act = True

    dokumen_list = pengajuan.dokumen_lampiran.all()
    history_list = pengajuan.approval_history.select_related('actor').order_by('created_at')

    if request.method == 'POST' and can_act:
        form = ApprovalActionForm(request.POST)
        if form.is_valid():
            keputusan = form.cleaned_data['keputusan']
            catatan = form.cleaned_data['catatan']
            status_lama = pengajuan.status

            if user.is_rt_rw:
                if keputusan == 'SETUJU':
                    status_baru = Pengajuan.StatusPengajuan.MENUNGGU_SEKDES
                    action_type = ApprovalHistory.ActionType.VERIFIKASI_SETUJU
                    notif_msg = f"Pengajuan Anda telah disetujui Ketua RT/RW dan diteruskan ke Sekretaris Desa."
                elif keputusan == 'REVISI':
                    status_baru = Pengajuan.StatusPengajuan.PERLU_REVISI_RT_RW
                    action_type = ApprovalHistory.ActionType.PERLU_REVISI
                    notif_msg = f"Ketua RT/RW meminta revisi berkas/data: {catatan}"
                else:  # TOLAK
                    status_baru = Pengajuan.StatusPengajuan.DITOLAK
                    action_type = ApprovalHistory.ActionType.MENOLAK
                    notif_msg = f"Pengajuan Anda ditolak oleh Ketua RT/RW. Alasan: {catatan}"

            elif user.is_sekdes:
                if keputusan == 'SETUJU':
                    status_baru = Pengajuan.StatusPengajuan.MENUNGGU_KEPALA_DESA
                    action_type = ApprovalHistory.ActionType.VERIFIKASI_SETUJU
                    notif_msg = f"Pengajuan Anda telah diverifikasi oleh Sekretaris Desa dan diteruskan ke Kepala Desa."
                elif keputusan == 'REVISI':
                    status_baru = Pengajuan.StatusPengajuan.PERLU_REVISI_SEKDES
                    action_type = ApprovalHistory.ActionType.PERLU_REVISI
                    notif_msg = f"Sekretaris Desa meminta revisi berkas/data: {catatan}"
                else:  # TOLAK
                    status_baru = Pengajuan.StatusPengajuan.DITOLAK
                    action_type = ApprovalHistory.ActionType.MENOLAK
                    notif_msg = f"Pengajuan Anda ditolak oleh Sekretaris Desa. Alasan: {catatan}"

            elif user.is_kades:
                if keputusan == 'SETUJU':
                    # Persetujuan Akhir & Penerbitan Surat Digital (§11.2, §14, §20)
                    status_baru = Pengajuan.StatusPengajuan.DITERBITKAN
                    action_type = ApprovalHistory.ActionType.FINAL_APPROVAL
                    notif_msg = f"Selamat! Pengajuan {pengajuan.jenis_surat.nama} Anda telah disetujui Kepala Desa dan surat resmi telah diterbitkan."
                elif keputusan == 'REVISI':
                    status_baru = Pengajuan.StatusPengajuan.PERLU_REVISI_KADES
                    action_type = ApprovalHistory.ActionType.PERLU_REVISI
                    notif_msg = f"Kepala Desa meminta revisi berkas/data: {catatan}"
                else:  # TOLAK
                    status_baru = Pengajuan.StatusPengajuan.DITOLAK
                    action_type = ApprovalHistory.ActionType.MENOLAK
                    notif_msg = f"Pengajuan Anda ditolak oleh Kepala Desa. Alasan: {catatan}"
            else:
                messages.error(request, "Aksi tidak diizinkan untuk peran ini.")
                return redirect('approval:detail', pk=pk)

            # Update pengajuan
            pengajuan.status = status_baru
            pengajuan.catatan_terakhir = catatan
            pengajuan.save()

            # Catat ke Riwayat Approval (Audit Trail §21)
            ApprovalHistory.objects.create(
                pengajuan=pengajuan,
                actor=user,
                action=action_type,
                status_dari=status_lama,
                status_ke=status_baru,
                catatan=catatan
            )

            # Jika Kades menyetujui, terbitkan surat PDF + QR Code (§14, §20)
            if user.is_kades and keputusan == 'SETUJU':
                surat = terbitkan_surat_digital(pengajuan, request_host=request.get_host())
                messages.success(request, f"Surat resmi berhasil diterbitkan dengan Nomor: {surat.nomor_surat}.")

            # Kirim notifikasi in-app ke pemohon
            Notifikasi.objects.create(
                user=pengajuan.warga,
                judul=f"Status Pengajuan: {pengajuan.jenis_surat.kode} ({pengajuan.get_status_display()})",
                pesan=notif_msg,
                link=f"/pengajuan/detail/{pengajuan.id}/"
            )

            # Notifikasi WhatsApp ke Pemohon (Warga)
            if user.is_kades and keputusan == 'SETUJU':
                wa_warga_msg = (
                    f"🎉 *SELAMAT! Surat Resmi Telah Diterbitkan*\n\n"
                    f"Halo Bapak/Ibu *{pengajuan.warga.get_full_name()}*,\n"
                    f"Permohonan surat *{pengajuan.jenis_surat.nama}* (#{pengajuan.id}) Anda telah disetujui Kepala Desa dan telah resmi diterbitkan.\n\n"
                    f"📋 *Nomor Surat:* {surat.nomor_surat}\n"
                    f"📅 *Masa Berlaku:* {surat.tanggal_terbit.strftime('%d-%m-%Y')} s.d. {surat.tanggal_kadaluarsa.strftime('%d-%m-%Y')}\n\n"
                    f"Dokumen PDF resmi ber-QR Code dapat langsung Anda unduh melalui akun SIPANDU Anda.\n"
                    f"_Pemerintah Desa Sukamaju_"
                )
            else:
                wa_warga_msg = (
                    f"Halo Bapak/Ibu *{pengajuan.warga.get_full_name()}*,\n\n"
                    f"📢 *Update Status Pengajuan SIPANDU (#{pengajuan.id}):*\n"
                    f"Jenis Surat: {pengajuan.jenis_surat.nama}\n"
                    f"Status: *{pengajuan.get_status_display()}*\n"
                    f"{'Catatan: ' + catatan if catatan else ''}\n\n"
                    f"Silakan periksa detailnya melalui portal SIPANDU.\n"
                    f"_Pemerintah Desa Sukamaju_"
                )
            send_whatsapp_to_user(pengajuan.warga, wa_warga_msg)

            send_whatsapp_to_role(
                CustomUser.Role.ADMIN,
                (
                    f"🔔 *UPDATE APPROVAL SIPANDU*\n\n"
                    f"Pengajuan #{pengajuan.id} ({pengajuan.jenis_surat.nama}) "
                    f"milik *{pengajuan.warga.get_full_name()}* diproses oleh "
                    f"*{user.get_role_display()}*.\n"
                    f"Keputusan: *{pengajuan.get_status_display()}*\n"
                    f"{'Catatan: ' + catatan if catatan else ''}"
                )
            )

            # Notifikasi WhatsApp ke Petugas Tingkat Berikutnya jika Disetujui
            if user.is_rt_rw and keputusan == 'SETUJU':
                wa_next = (
                    f"Halo Sekretaris Desa,\n\n"
                    f"📩 Terdapat permohonan surat *{pengajuan.jenis_surat.nama}* (#{pengajuan.id}) dari warga *{pengajuan.warga.get_full_name()}* (RT {pengajuan.wilayah.rt}/RW {pengajuan.wilayah.rw}) yang telah disetujui Ketua RT/RW dan menunggu verifikasi Anda di SIPANDU."
                )
                send_whatsapp_to_role(CustomUser.Role.SEKDES, wa_next)

            elif user.is_sekdes and keputusan == 'SETUJU':
                wa_next = (
                    f"Halo Kepala Desa,\n\n"
                    f"📩 Terdapat permohonan surat *{pengajuan.jenis_surat.nama}* (#{pengajuan.id}) dari warga *{pengajuan.warga.get_full_name()}* yang telah diverifikasi Sekretaris Desa dan menunggu persetujuan akhir Anda di SIPANDU."
                )
                send_whatsapp_to_role(CustomUser.Role.KADES, wa_next)

            elif user.is_kades and keputusan == 'SETUJU':
                wa_selesai = (
                    f"✅ *SURAT RESMI TELAH DITERBITKAN*\n\n"
                    f"Pengajuan #{pengajuan.id} ({pengajuan.jenis_surat.nama}) "
                    f"milik *{pengajuan.warga.get_full_name()}* telah diterbitkan "
                    f"dengan nomor *{surat.nomor_surat}*.\n"
                    f"Informasi ini dikirim sebagai pemberitahuan kepada petugas terkait."
                )
                send_whatsapp_to_role(CustomUser.Role.ADMIN, wa_selesai)
                send_whatsapp_to_role(CustomUser.Role.SEKDES, wa_selesai)
                send_whatsapp_to_role(
                    CustomUser.Role.RT_RW,
                    wa_selesai,
                    wilayah=pengajuan.wilayah
                )

            messages.success(request, f"Keputusan verifikasi ({keputusan}) berhasil disimpan.")
            return redirect('approval:queue')
    else:
        form = ApprovalActionForm()

    return render(request, 'approval/approval_detail.html', {
        'pengajuan': pengajuan,
        'dokumen_list': dokumen_list,
        'history_list': history_list,
        'form': form,
        'can_act': can_act
    })


@admin_required
def mode_b_verification_view(request, pk):
    """
    Mode B — Verifikasi Terwakilkan oleh Admin Desa (§17):
    Admin Desa menginputkan hasil verifikasi RT/RW secara offline.
    POIN AKUNTABILITAS: Wajib melampirkan file bukti komunikasi (screenshot/foto/tanda tangan basah).
    Tanpa bukti ini, verifikasi Mode B tidak dapat disimpan sistem (validasi level aplikasi).
    """
    pengajuan = get_object_or_404(Pengajuan, pk=pk)

    if pengajuan.status != Pengajuan.StatusPengajuan.MENUNGGU_RT_RW:
        messages.error(request, "Pengajuan ini tidak dalam status menunggu verifikasi RT/RW.")
        return redirect('approval:queue')

    if request.method == 'POST':
        form = ModeBApprovalForm(request.POST, request.FILES)
        if form.is_valid():
            keputusan = form.cleaned_data['keputusan']
            catatan = form.cleaned_data['catatan']
            lampiran_bukti = form.cleaned_data['lampiran_bukti']

            status_lama = pengajuan.status

            if keputusan == 'SETUJU':
                status_baru = Pengajuan.StatusPengajuan.MENUNGGU_SEKDES
                action_type = ApprovalHistory.ActionType.VERIFIKASI_MODE_B
                notif_msg = "Verifikasi RT/RW diwakilkan oleh Admin (Mode B) telah disetujui dan diteruskan ke Sekretaris Desa."
            elif keputusan == 'REVISI':
                status_baru = Pengajuan.StatusPengajuan.PERLU_REVISI_RT_RW
                action_type = ApprovalHistory.ActionType.PERLU_REVISI
                notif_msg = f"RT/RW (via Admin Desa) meminta revisi berkas/data: {catatan}"
            else:
                status_baru = Pengajuan.StatusPengajuan.DITOLAK
                action_type = ApprovalHistory.ActionType.MENOLAK
                notif_msg = f"Pengajuan ditolak sesuai konfirmasi RT/RW. Alasan: {catatan}"

            pengajuan.status = status_baru
            pengajuan.catatan_terakhir = f"[Mode B Admin] {catatan}"
            pengajuan.save()

            # Simpan ApprovalHistory dengan lampiran bukti wajib (§17, §21)
            ApprovalHistory.objects.create(
                pengajuan=pengajuan,
                actor=request.user,
                action=action_type,
                status_dari=status_lama,
                status_ke=status_baru,
                catatan=f"[Mode B - Terwakilkan RT/RW] {catatan}",
                lampiran_bukti=lampiran_bukti,
                is_mode_b=True
            )

            # Audit Log
            AuditLog.objects.create(
                actor=request.user,
                action="VERIFIKASI_MODE_B",
                module="approval",
                details=f"Admin mewakili RT {pengajuan.wilayah.rt}/RW {pengajuan.wilayah.rw} untuk pengajuan #{pengajuan.id}. Keputusan: {keputusan}",
                ip_address=request.META.get('REMOTE_ADDR', '')
            )

            Notifikasi.objects.create(
                user=pengajuan.warga,
                judul=f"Update Pengajuan: {pengajuan.jenis_surat.kode}",
                pesan=notif_msg,
                link=f"/pengajuan/detail/{pengajuan.id}/"
            )

            # Notifikasi WhatsApp ke Warga
            wa_warga_mode_b = (
                f"Halo Bapak/Ibu *{pengajuan.warga.get_full_name()}*,\n\n"
                f"📢 *Update Status Pengajuan SIPANDU (#{pengajuan.id}):*\n"
                f"Jenis Surat: {pengajuan.jenis_surat.nama}\n"
                f"Status: *{pengajuan.get_status_display()}*\n"
                f"Catatan RT/RW (via Admin): {catatan}\n\n"
                f"Silakan periksa detailnya melalui portal SIPANDU.\n"
                f"_Pemerintah Desa Sukamaju_"
            )
            send_whatsapp_to_user(pengajuan.warga, wa_warga_mode_b)
            send_whatsapp_to_role(
                CustomUser.Role.ADMIN,
                (
                    f"🔔 *VERIFIKASI MODE B DIPROSES*\n\n"
                    f"Pengajuan #{pengajuan.id} ({pengajuan.jenis_surat.nama}) "
                    f"milik *{pengajuan.warga.get_full_name()}* diproses oleh Admin "
                    f"sebagai perwakilan RT {pengajuan.wilayah.rt}/RW {pengajuan.wilayah.rw}.\n"
                    f"Status: *{pengajuan.get_status_display()}*."
                )
            )

            # Jika Setuju, teruskan ke Sekdes via WhatsApp
            if keputusan == 'SETUJU':
                wa_sekdes = (
                    f"Halo Sekretaris Desa,\n\n"
                    f"📩 Verifikasi Mode B (diwakilkan Admin untuk RT {pengajuan.wilayah.rt}/RW {pengajuan.wilayah.rw}) "
                    f"pada permohonan *{pengajuan.jenis_surat.nama}* (#{pengajuan.id}) pemohon *{pengajuan.warga.get_full_name()}* telah disetujui dan menunggu verifikasi Anda."
                )
                send_whatsapp_to_role(CustomUser.Role.SEKDES, wa_sekdes)

            messages.success(request, f"Verifikasi Mode B berhasil disimpan dengan lampiran bukti akuntabilitas (§17).")
            return redirect('approval:queue')
    else:
        form = ModeBApprovalForm()

    return render(request, 'approval/mode_b_form.html', {
        'pengajuan': pengajuan,
        'form': form
    })
