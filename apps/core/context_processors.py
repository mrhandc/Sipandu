from apps.core.models import SystemConfig, Notifikasi


def system_context(request):
    unread_count = 0
    recent_notifications = []
    if request.user.is_authenticated:
        unread_count = Notifikasi.objects.filter(user=request.user, is_read=False).count()
        recent_notifications = Notifikasi.objects.filter(user=request.user)[:5]

    return {
        'SYSTEM_NAMA_DESA': SystemConfig.get_value('NAMA_DESA', 'Desa Sukamaju'),
        'SYSTEM_KECAMATAN': SystemConfig.get_value('KECAMATAN', 'Kecamatan Wonosari'),
        'SYSTEM_KABUPATEN': SystemConfig.get_value('KABUPATEN', 'Kabupaten Malang'),
        'unread_notifications_count': unread_count,
        'recent_notifications': recent_notifications,
    }
