import re
import os
import requests
import logging
from django.db import models
from apps.core.models import SystemConfig, AuditLog
from apps.accounts.models import CustomUser

logger = logging.getLogger(__name__)

FONNTE_ENDPOINT = "https://api.fonnte.com/send"


def normalize_phone_number(phone_raw: str) -> str:
    """
    Normalisasi nomor telepon Indonesia ke format standar:
    08123456789 -> 628123456789
    +628123456789 -> 628123456789
    """
    if not phone_raw:
        return ""
    # Hapus spasi, strip, tanda kurung, dan plus
    cleaned = re.sub(r'[\s\-\(\)\+]', '', str(phone_raw))
    if cleaned.startswith('0'):
        cleaned = '62' + cleaned[1:]
    elif cleaned.startswith('8'):
        cleaned = '62' + cleaned
    return cleaned


def get_fonnte_token() -> str:
    """Ambil token Fonnte dari SYSTEM_CONFIG atau .env"""
    token = SystemConfig.get_value('FONNTE_TOKEN', '').strip()
    if not token:
        token = os.getenv('FONNTE_TOKEN', '').strip()
    return token


def is_fonnte_enabled() -> bool:
    """Cek apakah integrasi WhatsApp Fonnte diaktifkan"""
    val = SystemConfig.get_value('FONNTE_ENABLED', '').strip()
    if not val:
        val = os.getenv('FONNTE_ENABLED', 'True').strip()
    return val.lower() in ['1', 'true', 'yes', 'on']


def send_whatsapp_message(target_phone: str, message: str, user=None) -> tuple[bool, str]:
    """
    Kirim pesan WhatsApp menggunakan API Fonnte.com.
    Returns: (is_success, detail_response)
    """
    if not is_fonnte_enabled():
        logger.info(f"[WA DISABLED] Pesan ke {target_phone}: {message[:60]}...")
        return False, "Notifikasi WhatsApp nonaktif (FONNTE_ENABLED=False)"

    token = get_fonnte_token()
    normalized_phone = normalize_phone_number(target_phone)

    if not normalized_phone:
        return False, "Nomor telepon target kosong atau tidak valid."

    # Jika token belum disetel di SYSTEM_CONFIG / .env
    if not token or token == "YOUR_FONNTE_TOKEN_HERE":
        log_msg = f"[SIMULASI WA FONNTE] Token belum disetel. Pesan ke {normalized_phone}: {message[:120]}..."
        logger.warning(log_msg)
        AuditLog.objects.create(
            actor=user,
            action="WHATSAPP_SIMULATED",
            module="notification",
            details=f"Nomor: {normalized_phone} | Token Fonnte belum disetel di SYSTEM_CONFIG | Pesan: {message[:100]}..."
        )
        return False, "Token Fonnte belum dikonfigurasi di SYSTEM_CONFIG."

    # Kirim HTTP Request ke Fonnte
    try:
        headers = {
            'Authorization': token
        }
        payload = {
            'target': normalized_phone,
            'message': message,
            'countryCode': '62'
        }
        response = requests.post(
            FONNTE_ENDPOINT,
            data=payload,
            headers=headers,
            timeout=8
        )
        try:
            resp_json = response.json()
        except ValueError:
            resp_json = {}
        if not isinstance(resp_json, dict):
            resp_json = {'response': str(resp_json)}
        
        # Fonnte response biasanya: {"status": true, "target": [...], ...}
        fonnte_status = resp_json.get('status', False)
        is_ok = response.status_code == 200 and (
            fonnte_status is True or str(fonnte_status).lower() == 'true'
        )

        AuditLog.objects.create(
            actor=user,
            action="WHATSAPP_SENT" if is_ok else "WHATSAPP_FAILED",
            module="notification",
            details=f"Target: {normalized_phone} | HTTP {response.status_code} | Respon: {str(resp_json)[:150]}"
        )

        if is_ok:
            return True, "Pesan WhatsApp berhasil dikirim via Fonnte."
        else:
            reason = resp_json.get('reason', str(resp_json))
            return False, f"Fonnte Error: {reason}"

    except requests.exceptions.RequestException as e:
        logger.error(f"Gagal mengirim WhatsApp via Fonnte: {e}")
        AuditLog.objects.create(
            actor=user,
            action="WHATSAPP_ERROR",
            module="notification",
            details=f"Target: {normalized_phone} | Exception: {str(e)[:150]}"
        )
        return False, f"Koneksi Fonnte timeout/gagal: {str(e)}"


def send_whatsapp_to_user(user: CustomUser, message: str) -> tuple[bool, str]:
    """Helper untuk kirim WA langsung ke objek User jika nomor HP tersedia"""
    if not user or not user.no_hp:
        return False, "Pengguna tidak memiliki nomor HP/WhatsApp."
    return send_whatsapp_message(user.no_hp, message, user=user)


def send_whatsapp_to_role(role_name: str, message: str, wilayah=None) -> int:
    """
    Helper untuk broadcast pesan WhatsApp ke seluruh petugas dengan role tertentu
    (misal: semua Sekdes, Kades, Admin, atau RT/RW di wilayah terkait).
    Returns: jumlah penerima yang dikirimi pesan.
    """
    qs = CustomUser.objects.filter(
        role=role_name,
        is_active=True,
    ).exclude(no_hp__isnull=True).exclude(no_hp='')
    if wilayah and role_name == CustomUser.Role.RT_RW:
        qs = qs.filter(wilayah=wilayah)

    sent_count = 0
    for petugas in qs:
        success, _ = send_whatsapp_to_user(petugas, message)
        if success:
            sent_count += 1
    return sent_count


def send_whatsapp_to_roles(role_names, message: str, wilayah=None) -> int:
    """Broadcast satu pesan ke beberapa role tanpa mengirim dua kali ke user yang sama."""
    qs = CustomUser.objects.filter(
        role__in=role_names,
        is_active=True,
    ).exclude(no_hp__isnull=True).exclude(no_hp='')
    if wilayah:
        qs = qs.filter(
            models.Q(role=CustomUser.Role.RT_RW, wilayah=wilayah)
            | ~models.Q(role=CustomUser.Role.RT_RW)
        )

    sent_count = 0
    for user in qs.distinct():
        success, _ = send_whatsapp_to_user(user, message)
        if success:
            sent_count += 1
    return sent_count
