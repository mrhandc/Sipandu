import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sipandu.settings')
django.setup()

from django.core.files.base import ContentFile
from PIL import Image, ImageDraw, ImageFont
import io

from apps.accounts.models import CustomUser, Wilayah, VerifikasiAkun
from apps.surat.models import JenisSurat, Surat
from apps.pengajuan.models import Persyaratan, Pengajuan
from apps.core.models import SystemConfig, AuditLog


def create_dummy_image(text, filename="image.jpg", bg_color=(220, 230, 242), text_color=(30, 50, 90), width=400, height=260):
    img = Image.new('RGB', (width, height), color=bg_color)
    draw = ImageDraw.Draw(img)
    # Simple rectangle and text representation
    draw.rectangle([10, 10, width - 10, height - 10], outline=(100, 120, 150), width=2)
    draw.text((25, 40), text, fill=text_color)
    draw.text((25, 80), "SIPANDU VERIFIKASI DOKUMEN", fill=(120, 140, 160))
    buffer = io.BytesIO()
    img.save(buffer, format='JPEG')
    return ContentFile(buffer.getvalue(), name=filename)



def seed():
    print("Mulai seeding data SIPANDU...")

    # 1. Wilayah (§28)
    w1, _ = Wilayah.objects.get_or_create(
        rt="001", rw="002", dusun="Dusun Krajan",
        defaults={
            'nama_desa': "Desa Sukamaju",
            'kecamatan': "Kecamatan Wonosari",
            'kabupaten': "Kabupaten Malang",
            'provinsi': "Jawa Timur",
            'kode_pos': "65100"
        }
    )
    w2, _ = Wilayah.objects.get_or_create(
        rt="002", rw="002", dusun="Dusun Krajan",
        defaults={
            'nama_desa': "Desa Sukamaju",
            'kecamatan': "Kecamatan Wonosari",
            'kabupaten': "Kabupaten Malang",
            'provinsi': "Jawa Timur",
            'kode_pos': "65100"
        }
    )
    w3, _ = Wilayah.objects.get_or_create(
        rt="001", rw="001", dusun="Dusun Timur",
        defaults={
            'nama_desa': "Desa Sukamaju",
            'kecamatan': "Kecamatan Wonosari",
            'kabupaten': "Kabupaten Malang",
            'provinsi': "Jawa Timur",
            'kode_pos': "65100"
        }
    )
    print("Wilayah RT/RW berhasil disiapkan.")

    # 2. SystemConfig (§5.3, §13.2, §18)
    configs = [
        ('MAX_REVISION_LIMIT', '3', 'Batas maksimal revisi pengajuan sebelum auto tolak (§13.2)'),
        ('TIMEOUT_T1_HOURS', '24', 'Threshold T1: Pengingat pertama ke petugas (jam) (§18)'),
        ('TIMEOUT_T2_HOURS', '48', 'Threshold T2: Pengingat kedua ke petugas (jam) (§18)'),
        ('TIMEOUT_T3_HOURS', '72', 'Threshold T3: Eskalasi otomatis ke Admin Desa (jam) (§18)'),
        ('NAMA_DESA', 'Desa Sukamaju', 'Nama Resmi Desa'),
        ('KECAMATAN', 'Kecamatan Wonosari', 'Nama Kecamatan'),
        ('KODE_DESA', 'DSA', 'Kode singkatan desa untuk format nomor surat (§20)'),
        ('NAMA_KADES', 'H. Moch. Syarifudin, S.Sos.', 'Nama Kepala Desa penandatangan resmi'),
        ('FONNTE_ENABLED', 'True', 'Aktifkan Pengiriman Notifikasi WhatsApp via Fonnte (True/False)'),
        ('FONNTE_TOKEN', '', 'Token API Fonnte.com (didapatkan dari menu Device di fonnte.com)'),
    ]
    for key, val, desc in configs:
        SystemConfig.objects.get_or_create(key=key, defaults={'value': val, 'deskripsi': desc})
    print("SYSTEM_CONFIG berhasil disiapkan.")

    # 3. Jenis Surat MVP (§24) & Masa Berlaku (§15.1)
    sktm, _ = JenisSurat.objects.get_or_create(
        kode="SKTM",
        defaults={
            'nama': "Surat Keterangan Tidak Mampu",
            'deskripsi': "Surat keterangan untuk keringanan biaya pendidikan, kesehatan, dan bantuan sosial.",
            'masa_berlaku_hari': 180,  # 6 bulan (§15.1)
            'is_active': True
        }
    )
    domisili, _ = JenisSurat.objects.get_or_create(
        kode="DOMISILI",
        defaults={
            'nama': "Surat Keterangan Domisili",
            'deskripsi': "Surat keterangan bukti tempat tinggal dan domisili resmi warga.",
            'masa_berlaku_hari': 365,  # 1 tahun (§15.1)
            'is_active': True
        }
    )
    sku, _ = JenisSurat.objects.get_or_create(
        kode="SKU",
        defaults={
            'nama': "Surat Keterangan Usaha",
            'deskripsi': "Surat keterangan kepemilikan dan legalitas operasional usaha mikro/kecil warga.",
            'masa_berlaku_hari': 365,  # 1 tahun (§15.1)
            'is_active': True
        }
    )

    # Persyaratan dokumen per jenis surat (§5.1, §24)
    Persyaratan.objects.get_or_create(jenis_surat=sktm, nama_dokumen="KTP Pemohon", defaults={'is_required': True})
    Persyaratan.objects.get_or_create(jenis_surat=sktm, nama_dokumen="Kartu Keluarga (KK)", defaults={'is_required': True})
    Persyaratan.objects.get_or_create(jenis_surat=sktm, nama_dokumen="Foto Rumah Tampak Depan", defaults={'is_required': False})

    Persyaratan.objects.get_or_create(jenis_surat=domisili, nama_dokumen="KTP Pemohon", defaults={'is_required': True})
    Persyaratan.objects.get_or_create(jenis_surat=domisili, nama_dokumen="Kartu Keluarga (KK)", defaults={'is_required': True})

    Persyaratan.objects.get_or_create(jenis_surat=sku, nama_dokumen="KTP Pemilik Usaha", defaults={'is_required': True})
    Persyaratan.objects.get_or_create(jenis_surat=sku, nama_dokumen="Kartu Keluarga (KK)", defaults={'is_required': True})
    Persyaratan.objects.get_or_create(jenis_surat=sku, nama_dokumen="Foto Lokasi/Tempat Usaha", defaults={'is_required': True})
    print("Master Jenis Surat & Persyaratan berhasil disiapkan.")

    # 4. Pengguna per Role (§9, §25)
    # Admin Desa
    admin_user, created = CustomUser.objects.get_or_create(
        username="admin",
        defaults={
            'first_name': "Admin Desa Sukamaju",
            'email': "admin@sukamaju.desa.id",
            'role': CustomUser.Role.ADMIN,
            'status_akun': CustomUser.StatusAkun.AKTIF,
            'is_staff': True,
            'is_superuser': True,
            'wilayah': w1,
            'no_hp': "081200000001"
        }
    )
    if created:
        admin_user.set_password("admin123")
        admin_user.save()

    # Kepala Desa
    kades_user, created = CustomUser.objects.get_or_create(
        username="kades",
        defaults={
            'first_name': "H. Moch. Syarifudin, S.Sos.",
            'email': "kades@sukamaju.desa.id",
            'role': CustomUser.Role.KADES,
            'status_akun': CustomUser.StatusAkun.AKTIF,
            'is_staff': True,
            'wilayah': w1,
            'no_hp': "081200000002"
        }
    )
    if created:
        kades_user.set_password("kades123")
        kades_user.save()

    # Sekretaris Desa
    sekdes_user, created = CustomUser.objects.get_or_create(
        username="sekdes",
        defaults={
            'first_name': "Bambang Pamungkas, S.IP.",
            'email': "sekdes@sukamaju.desa.id",
            'role': CustomUser.Role.SEKDES,
            'status_akun': CustomUser.StatusAkun.AKTIF,
            'is_staff': True,
            'wilayah': w1,
            'no_hp': "081200000003"
        }
    )
    if created:
        sekdes_user.set_password("sekdes123")
        sekdes_user.save()

    # Ketua RT 01 / RW 02 (Personal account, not shared §17)
    rt_user, created = CustomUser.objects.get_or_create(
        username="rt01",
        defaults={
            'first_name': "Sutrisno (Ketua RT 01)",
            'email': "rt01@sukamaju.desa.id",
            'role': CustomUser.Role.RT_RW,
            'status_akun': CustomUser.StatusAkun.AKTIF,
            'is_staff': False,
            'wilayah': w1,
            'no_hp': "081234567891"
        }
    )
    if created:
        rt_user.set_password("rt123")
        rt_user.save()

    # Warga Budi (Sudah AKTIF / Terverifikasi)
    warga_budi, created = CustomUser.objects.get_or_create(
        username="warga_budi",
        defaults={
            'first_name': "Budi Santoso",
            'nik': "3507123456780001",
            'email': "budi.santoso@gmail.com",
            'no_hp': "081234567890",
            'alamat': "Jl. Mawar No. 12 RT 01 RW 02",
            'role': CustomUser.Role.WARGA,
            'status_akun': CustomUser.StatusAkun.AKTIF,
            'wilayah': w1
        }
    )
    if created:
        warga_budi.set_password("warga123")
        warga_budi.save()
    if not VerifikasiAkun.objects.filter(user=warga_budi).exists():
        VerifikasiAkun.objects.create(
            user=warga_budi,
            foto_ktp=create_dummy_image("DOKUMEN KTP - BUDI SANTOSO\nNIK: 3507123456780001", filename="ktp_budi.jpg"),
            foto_wajah=create_dummy_image("FOTO WAJAH RESMI - BUDI SANTOSO", filename="wajah_budi.jpg"),
            status=CustomUser.StatusAkun.AKTIF,
            verified_by=admin_user
        )

    # Warga Baru (Menunggu verifikasi admin untuk pengujian alur §10)
    warga_baru, created = CustomUser.objects.get_or_create(
        username="warga_baru",
        defaults={
            'first_name': "Siti Aminah",
            'nik': "3507123456780002",
            'email': "siti.aminah@gmail.com",
            'no_hp': "081398765432",
            'alamat': "Jl. Melati No. 05 RT 01 RW 02",
            'role': CustomUser.Role.WARGA,
            'status_akun': CustomUser.StatusAkun.PENDING_VERIFIKASI,
            'wilayah': w1
        }
    )
    if created:
        warga_baru.set_password("warga123")
        warga_baru.save()
    if not VerifikasiAkun.objects.filter(user=warga_baru).exists():
        VerifikasiAkun.objects.create(
            user=warga_baru,
            foto_ktp=create_dummy_image("DOKUMEN KTP - SITI AMINAH\nNIK: 3507123456780002", filename="ktp_siti.jpg"),
            foto_wajah=create_dummy_image("FOTO WAJAH RESMI - SITI AMINAH", filename="wajah_siti.jpg"),
            status=CustomUser.StatusAkun.PENDING_VERIFIKASI
        )


    print("Pengguna Uji Coba Multi-Role berhasil disiapkan:")
    print(" - Admin Desa  : admin / admin123")
    print(" - Kepala Desa : kades / kades123")
    print(" - Sekdes      : sekdes / sekdes123")
    print(" - Ketua RT/RW : rt01 / rt123")
    print(" - Warga Aktif : warga_budi / warga123")
    print(" - Warga Baru  : warga_baru / warga123 (Status: PENDING_VERIFIKASI)")

    AuditLog.objects.create(
        actor=admin_user,
        action="SEED_DATABASE",
        module="core",
        details="Inisialisasi data awal master sistem SIPANDU selesai."
    )
    print("Seeding data selesai dengan sukses!")


if __name__ == '__main__':
    seed()
