from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from apps.accounts.models import CustomUser


def role_required(*allowed_roles):
    """
    Decorator untuk membatasi akses view berdasarkan role (§25 RBAC Matrix)
    dan memastikan akun warga sudah berstatus AKTIF (§10.2).
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                messages.warning(request, "Silakan masuk (login) terlebih dahulu.")
                return redirect('accounts:login')

            user = request.user

            # Superuser has full admin access
            if user.is_superuser and CustomUser.Role.ADMIN in allowed_roles:
                return view_func(request, *args, **kwargs)

            # Cek status akun warga (§10.2)
            if user.is_warga and user.status_akun != CustomUser.StatusAkun.AKTIF:
                messages.warning(
                    request,
                    f"Akun Anda berstatus: {user.get_status_akun_display()}. Anda belum dapat mengakses fitur ini."
                )
                return redirect('accounts:status_akun')

            if user.role not in allowed_roles:
                messages.error(request, "Anda tidak memiliki kewenangan untuk mengakses halaman tersebut.")
                return redirect('core:dashboard')

            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator


def warga_required(view_func):
    return role_required(CustomUser.Role.WARGA)(view_func)


def rt_rw_required(view_func):
    return role_required(CustomUser.Role.RT_RW)(view_func)


def sekdes_required(view_func):
    return role_required(CustomUser.Role.SEKDES)(view_func)


def kades_required(view_func):
    return role_required(CustomUser.Role.KADES)(view_func)


def admin_required(view_func):
    return role_required(CustomUser.Role.ADMIN)(view_func)


def petugas_required(view_func):
    return role_required(
        CustomUser.Role.RT_RW,
        CustomUser.Role.SEKDES,
        CustomUser.Role.KADES,
        CustomUser.Role.ADMIN
    )(view_func)
