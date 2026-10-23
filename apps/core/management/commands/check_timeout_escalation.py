from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.pengajuan.models import Pengajuan
from apps.core.models import SystemConfig, Notifikasi, AuditLog
from apps.accounts.models import CustomUser
from apps.core.services.whatsapp import send_whatsapp_to_user


class Command(BaseCommand):
    help = "Mengecek antrian pengajuan dan mengirim reminder / eskalasi timeout (§18)"

    def handle(self, *args, **options):
        now = timezone.now()
        t1_hours = SystemConfig.get_int('TIMEOUT_T1_HOURS', 24)
        t2_hours = SystemConfig.get_int('TIMEOUT_T2_HOURS', 48)
        t3_hours = SystemConfig.get_int('TIMEOUT_T3_HOURS', 72)

        active_statuses = [
            Pengajuan.StatusPengajuan.MENUNGGU_RT_RW,
            Pengajuan.StatusPengajuan.MENUNGGU_SEKDES,
            Pengajuan.StatusPengajuan.MENUNGGU_KEPALA_DESA,
        ]

        pending_items = Pengajuan.objects.filter(status__in=active_statuses)
        admin_users = CustomUser.objects.filter(role=CustomUser.Role.ADMIN)

        reminder_count = 0
        escalation_count = 0

        for item in pending_items:
            delta = now - item.updated_at
            hours_elapsed = delta.total_seconds() / 3600.0

            # Tentukan target petugas
            target_users = []
            if item.status == Pengajuan.StatusPengajuan.MENUNGGU_RT_RW:
                target_users = CustomUser.objects.filter(role=CustomUser.Role.RT_RW, wilayah=item.wilayah)
                role_label = f"RT {item.wilayah.rt}/RW {item.wilayah.rw}"
            elif item.status == Pengajuan.StatusPengajuan.MENUNGGU_SEKDES:
                target_users = CustomUser.objects.filter(role=CustomUser.Role.SEKDES)
                role_label = "Sekretaris Desa"
            elif item.status == Pengajuan.StatusPengajuan.MENUNGGU_KEPALA_DESA:
                target_users = CustomUser.objects.filter(role=CustomUser.Role.KADES)
                role_label = "Kepala Desa"

            # Level 3: Eskalasi ke Admin Desa (>= T3 jam)
            if hours_elapsed >= t3_hours:
                for admin in admin_users:
                    exists = Notifikasi.objects.filter(
                        user=admin,
                        judul__startswith=f"[ESKALASI TIMEOUT] Pengajuan #{item.id}"
                    ).exists()
                    if not exists:
                        Notifikasi.objects.create(
                            user=admin,
                            judul=f"[ESKALASI TIMEOUT] Pengajuan #{item.id} Tertahan di {role_label}",
                            pesan=f"Pengajuan {item.jenis_surat.kode} milik warga {item.warga.get_full_name()} telah tertahan selama {int(hours_elapsed)} jam tanpa tindakan.",
                            link=f"/approval/detail/{item.id}/"
                        )
                        # WhatsApp Eskalasi ke Admin Desa
                        wa_admin_eskalasi = (
                            f"🚨 *ESKALASI TIMEOUT PELAYANAN (SLA T3 &ge; {t3_hours} Jam)*\n\n"
                            f"Pengajuan: *{item.jenis_surat.nama}* (#{item.id})\n"
                            f"Pemohon: {item.warga.get_full_name()}\n"
                            f"Tertahan di: *{role_label}* selama {int(hours_elapsed)} jam tanpa respons.\n\n"
                            f"Mohon Admin Desa segera melakukan tindak lanjut atau verifikasi terwakilkan (Mode B).\n"
                            f"_Sistem SIPANDU_"
                        )
                        send_whatsapp_to_user(admin, wa_admin_eskalasi)

                        escalation_count += 1
                        AuditLog.objects.create(
                            action="ESKALASI_TIMEOUT",
                            module="approval",
                            details=f"Eskalasi pengajuan #{item.id} ke Admin Desa karena melebihi threshold T3 ({t3_hours} jam)."
                        )

            # Level 2 / Level 1: Reminder ke petugas
            elif hours_elapsed >= t1_hours:
                level_tag = "Kedua" if hours_elapsed >= t2_hours else "Pertama"
                for u in target_users:
                    exists = Notifikasi.objects.filter(
                        user=u,
                        judul__startswith=f"[PENGINGAT {level_tag}] Pengajuan #{item.id}"
                    ).exists()
                    if not exists:
                        Notifikasi.objects.create(
                            user=u,
                            judul=f"[PENGINGAT {level_tag}] Pengajuan #{item.id} Menunggu Tindakan",
                            pesan=f"Pengajuan {item.jenis_surat.nama} oleh {item.warga.get_full_name()} menunggu verifikasi Anda (tertahan {int(hours_elapsed)} jam).",
                            link=f"/approval/detail/{item.id}/"
                        )
                        # WhatsApp Pengingat ke Petugas
                        wa_petugas_reminder = (
                            f"⏰ *PENGINGAT {level_tag.upper()} SLA PELAYANAN DESA*\n\n"
                            f"Halo Bapak/Ibu {u.get_full_name() or u.username},\n"
                            f"Permohonan surat *{item.jenis_surat.nama}* (#{item.id}) milik warga *{item.warga.get_full_name()}* sedang menunggu tindakan verifikasi Anda.\n"
                            f"Durasi antrian: {int(hours_elapsed)} jam.\n\n"
                            f"Silakan buka portal SIPANDU untuk memproses permohonan tersebut."
                        )
                        send_whatsapp_to_user(u, wa_petugas_reminder)
                        reminder_count += 1

        self.stdout.write(self.style.SUCCESS(
            f"Pengecekan timeout selesai: {reminder_count} reminder dikirim, {escalation_count} eskalasi ke Admin Desa."
        ))
