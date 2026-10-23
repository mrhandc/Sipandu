# SIPANDU (Sistem Informasi Pelayanan Administrasi Surat Keterangan Desa)
### Berbasis Web dengan Mekanisme Multi-Level Approval

Website aplikasi pelayanan administrasi surat keterangan desa digital yang dikembangkan berdasarkan **Dokumen PRD SIPANDU (Politeknik Elektronika Negeri Surabaya - Praktikum Pemrograman Framework)**.

---

## 👥 Pengembang & Penyusun
- **Mohammad Shofwan Ainun Na'im** (3125521056)
- **Mohammad Thoriq Abben Al Banie** (3125521060)
- **Dosen Pengampu**: Evianita Dewi Fajrianti, S.Tr.T., M.Tr.T.

---

## 🌟 Fondasi Arsitektur & Fitur Utama Sesuai PRD

1. **Alur Verifikasi Berjenjang (Multi-Level Approval §11 & §12)**
   - Warga (`DIAJUKAN`) &rarr; Validasi Sistem &rarr; Ketua RT/RW (`MENUNGGU_RT_RW`) &rarr; Sekretaris Desa (`MENUNGGU_SEKDES`) &rarr; Kepala Desa (`MENUNGGU_KEPALA_DESA`) &rarr; Penerbitan Resmi (`DITERBITKAN`).
   - Menerapkan *Single Source of Truth* status enum terpusat (`DRAFT`, `DIAJUKAN`, `MENUNGGU_RT_RW`, `PERLU_REVISI_RT_RW`, `MENUNGGU_SEKDES`, `PERLU_REVISI_SEKDES`, `MENUNGGU_KEPALA_DESA`, `PERLU_REVISI_KADES`, `DISETUJUI`, `MENUNGGU_PENERBITAN`, `DITERBITKAN`, `DITOLAK`, `DIBATALKAN`).

2. **Registrasi Akun & Verifikasi Identitas Warga (§10 & §19)**
   - Warga wajib mengunggah foto KTP dan foto selfie wajah saat mendaftar.
   - Status akun awal: `PENDING_VERIFIKASI`.
   - Admin Desa melakukan verifikasi komparasi visual manual KTP vs foto wajah sebelum mengaktifkan akun (`AKTIF`).
   - Akses foto KTP & wajah terisolasi aman hanya untuk Admin Desa demi privasi data warga (*Data Minimization & Access Control*).

3. **Legalitas Dokumen Hybrid: PDF Resmi & QR Code Verifikasi (§14)**
   - Surat resmi di-generate otomatis menjadi dokumen PDF berstandar kop surat dinas desa menggunakan ReportLab.
   - Dilengkapi QR Code dinamis ber-UUID unik yang mengarah ke laman verifikasi publik `/surat/verifikasi/<uuid>/` untuk pembuktian keaslian dokumen.

4. **Penomoran Surat Aman dari Duplikasi (Concurrency-Safe §20)**
   - Menggunakan transaksi database atomik dengan penguncian baris (`select_for_update()`) pada sequence nomor surat sehingga tidak terjadi nomor ganda meskipun dua approval terjadi bersamaan.
   - Format: `[KODE]/[NOMOR_3_DIGIT]/[KODE_DESA]/[BULAN_ROMAWI]/[TAHUN]` (misal: `SKTM/001/DSA/X/2026`).

5. **Masa Berlaku Surat & Pembatasan Pengajuan Ulang (§15)**
   - Konfigurasi masa berlaku surat per jenis surat (SKTM: 6 bulan, SK Domisili: 1 tahun, SKU: 1 tahun).
   - Sistem secara otomatis memblokir warga dari mengajukan surat sejenis jika surat sebelumnya masih berstatus `AKTIF` dan belum kedaluwarsa.
   - **Jalur Pengecualian Admin Desa (§15.4)**: Admin Desa memiliki kewenangan khusus membatalkan surat lama secara manual dengan alasan wajib yang tercatat di audit log (misal karena hilang/rusak).

6. **Alur Revisi Terkontrol & Pembatalan Pengajuan (§13 & §16)**
   - Status `PERLU_REVISI_*` tidak membuat record baru; perbaikan dilakukan pada data permohonan yang sama.
   - Catatan alasan wajib diisi saat petugas meminta revisi atau menolak.
   - Batas maksimal revisi (default: 3 kali). Jika melebihi batas maksimal revisi, sistem secara otomatis menolak final (`DITOLAK`).
   - Warga dapat membatalkan pengajuan sendiri selama permohonan belum masuk tahap Kepala Desa.

7. **Akuntabilitas Petugas & Verifikasi Terwakilkan Mode B (§17)**
   - Setiap petugas menggunakan akun personal (bukan akun bersama).
   - **Mode B**: Bagi RT/RW yang belum menggunakan aplikasi secara digital, Admin Desa dapat menginputkan hasil verifikasi offline dengan **kewajiban melampirkan file bukti komunikasi** (screenshot chat / tanda tangan formulir basah) yang divalidasi ketat di level aplikasi.

8. **Audit Trail Lengkap (§21)**
   - Setiap perpindahan status dan keputusan tercatat di tabel `ApprovalHistory` dan `AuditLog` (merekam aktor, waktu, IP address, catatan keputusan, dan bukti lampiran).

9. **Konfigurasi Dinamis (SYSTEM_CONFIG §5.3, §13.2, §18)**
   - Admin dapat mengatur batas revisi, threshold pengingat SLA (T1/T2/T3), nama desa, kepala desa, dsb. secara langsung melalui UI tanpa perlu redeploy kode.

10. **Notifikasi WhatsApp Real-Time via Fonnte (§13, §18)**
    - Seluruh role (Warga, RT/RW, Sekdes, Kades, Admin) menerima notifikasi WhatsApp otomatis pada setiap peristiwa penting:
      - Warga: aktivasi akun, pengajuan diterima, permintaan revisi, pengajuan dibatalkan, persetujuan/penolakan di setiap tahap, penerbitan surat resmi (beserta nomor surat).
      - Petugas (RT/RW, Sekdes, Kades): pemberitahuan ada pengajuan baru yang perlu ditangani.
      - Admin Desa: eskalasi T3 SLA otomatis via management command.
    - **Simulation Mode**: Jika token Fonnte belum dikonfigurasi, sistem mencatat `WHATSAPP_SIMULATED` di Audit Log tanpa error — aman untuk development.
    - Token dapat diatur dari UI SYSTEM_CONFIG tanpa redeploy. Pengujian live tersedia di menu **Kelola Admin → WhatsApp Gateway (Fonnte)**.

### Cakupan Notifikasi WhatsApp

Gateway Fonnte diimplementasikan pada `apps/core/services/whatsapp.py`. Pengiriman menggunakan nomor `no_hp` pengguna yang dinormalisasi ke format internasional Indonesia (`628...`). Kegagalan gateway dicatat pada `AuditLog` dan tidak membatalkan proses pengajuan atau approval utama.

| Peristiwa | Penerima |
|---|---|
| Pendaftaran warga baru | Admin Desa |
| Akun disetujui atau ditolak | Warga |
| Pengajuan surat baru | Warga, RT/RW sesuai wilayah, Admin Desa |
| Persetujuan RT/RW | Warga, Sekretaris Desa, Admin Desa |
| Persetujuan Sekdes | Warga, Kepala Desa, Admin Desa |
| Revisi, penolakan, atau pembatalan | Warga dan Admin Desa; petugas tahap terkait menerima pengajuan revisi |
| Persetujuan akhir dan penerbitan PDF/QR | Warga, Admin Desa, Sekdes, dan RT/RW wilayah pemohon |
| Verifikasi terwakilkan Mode B | Warga, Admin Desa, dan Sekretaris Desa bila diteruskan |
| Pengingat SLA dan eskalasi timeout | Petugas pada tahap terkait dan Admin Desa |

### Konfigurasi Fonnte

1. Buat atau aktifkan perangkat WhatsApp pada [Fonnte](https://fonnte.com) dan salin token API.
2. Simpan token pada `.env` lokal (file ini tidak boleh di-push):
   ```env
   FONNTE_ENABLED=True
   FONNTE_TOKEN=token_fonnte_anda
   ```
3. Jalankan `python seed_data.py` pada instalasi baru, atau isi `FONNTE_ENABLED` dan `FONNTE_TOKEN` melalui menu **Kelola Admin → SYSTEM_CONFIG**.
4. Uji pengiriman melalui menu **Kelola Admin → WhatsApp Gateway (Fonnte)**.

Jika token belum tersedia, aplikasi berjalan dalam Simulation Mode dan menulis aksi `WHATSAPP_SIMULATED` ke audit log. Pastikan setiap akun penerima memiliki nomor WhatsApp pada field `no_hp`.

---

## 🛠️ Tech Stack
- **Bahasa**: Python 3.11+ / 3.12
- **Framework Web**: Django 5.1 (Django ORM, Authentication, Django Admin)
- **Database**: SQLite (default zero-config out of the box) / MySQL support (via PyMySQL)
- **PDF Generation**: ReportLab
- **QR Code**: qrcode + Pillow
- **WhatsApp Gateway**: [Fonnte.com](https://fonnte.com) API (notifikasi real-time ke semua role)
- **Frontend**: Django Template + Bootstrap 5 + Bootstrap Icons (Mobile-friendly & responsif)

## 🧩 Template Dasar Antarmuka

Seluruh halaman aplikasi menggunakan [`templates/base.html`](templates/base.html) sebagai template induk Django. Halaman lain dapat mewarisinya dengan `{% extends "base.html" %}` dan mengisi blok yang tersedia:

| Blok | Fungsi |
|---|---|
| `title` | Mengubah judul halaman pada tab browser. Nilai default: `SIPANDU - Pelayanan Administrasi Desa Digital`. |
| `extra_css` | Menambahkan CSS khusus pada halaman turunan setelah stylesheet global. |
| `content` | Menempatkan isi utama halaman di dalam container Bootstrap. |
| `extra_js` | Menambahkan JavaScript khusus setelah Bootstrap JS Bundle. |

### Komponen Layout

- **Navbar responsif** dengan branding SIPANDU, nama desa, tombol menu mobile, dan navigasi berdasarkan status login serta role pengguna.
- **Menu warga** untuk dashboard, daftar pengajuan, dan surat yang telah diterbitkan.
- **Menu petugas** untuk antrian verifikasi bagi RT/RW, Sekdes, Kades, dan Admin Desa.
- **Menu laporan** untuk Sekdes, Kades, dan Admin Desa.
- **Dropdown Kelola Admin** khusus Admin Desa yang berisi verifikasi KTP/wajah, pengelolaan surat, konfigurasi sistem, pengujian WhatsApp Fonnte, audit trail, dan Django Admin.
- **Notifikasi** dengan badge jumlah notifikasi yang belum dibaca melalui `unread_notifications_count`.
- **Dropdown profil pengguna** yang menampilkan nama, email, role, status akun warga, tautan status akun/KTP, dan logout.
- **Flash message** Django (`messages`) dengan ikon berbeda untuk pesan `success`, `error`, `warning`, dan informasi.
- **Area konten utama** yang disediakan melalui `{% block content %}`.
- **Footer** yang menampilkan nama desa, kecamatan, tahun, dan deskripsi sistem.

### Konteks Template yang Dibutuhkan

Template mengandalkan objek dan variabel berikut dari Django context processor atau view:

| Variabel / objek | Kegunaan |
|---|---|
| `user` | Menentukan status autentikasi, role, identitas, email, dan status akun. |
| `SYSTEM_NAMA_DESA` | Menampilkan nama desa pada navbar dan footer. |
| `SYSTEM_KECAMATAN` | Menampilkan nama kecamatan pada footer. |
| `unread_notifications_count` | Menampilkan badge jumlah notifikasi yang belum dibaca. |
| `messages` | Menampilkan pesan umpan balik dari Django messages framework. |

Role pengguna dibaca melalui properti `user.is_warga`, `user.is_rt_rw`, `user.is_sekdes`, `user.is_kades`, dan `user.is_admin_desa`. Nama URL menggunakan namespace `core`, `accounts`, `pengajuan`, `surat`, dan `approval`, sehingga URL pattern terkait harus tetap terdaftar pada konfigurasi Django.

### Dependensi Frontend dari CDN

`base.html` memuat dependensi berikut secara langsung dari CDN:

- Bootstrap `5.3.3` untuk grid, navbar, dropdown, alert, tombol, dan komponen responsif.
- Bootstrap Icons `1.11.3` untuk ikon navigasi dan status.
- Google Fonts **Plus Jakarta Sans** dengan bobot 400, 500, 600, 700, dan 800.
- Bootstrap JS Bundle `5.3.3` untuk navbar mobile, dropdown, alert dismiss, dan interaksi komponen.

Koneksi internet diperlukan ketika halaman pertama kali mengambil aset tersebut dari CDN. Untuk deployment tanpa akses CDN, aset sebaiknya disalin ke direktori `static/` dan diubah menjadi aset statis lokal.

### Gaya Visual Global

Template menetapkan warna utama biru `#1e40af`, warna hover `#1d4ed8`, serta navy `#0f172a` untuk navbar. Konten menggunakan latar `#f8fafc`, kartu dengan sudut membulat dan bayangan ringan, tombol utama biru, serta footer putih yang tetap berada di bagian bawah halaman.

---

## 🚀 Panduan Menjalankan Sistem

### 1. Masuk ke Virtual Environment & Persiapan
```powershell
# Buka PowerShell pada direktori proyek
.\venv\Scripts\activate
```

### 2. Jalankan Migrasi Database (Jika Diperlukan)
```powershell
python manage.py migrate
```

### 3. Jalankan Pengisian Data Demo (Seeding)
```powershell
python seed_data.py
```

### 4. Jalankan Development Server
```powershell
python manage.py runserver
```
Aplikasi dapat dibuka pada peramban melalui alamat: **`http://127.0.0.1:8000/`**

---

## 🔑 Akun Uji Coba Multi-Role (PRD §25)

Telah disediakan akun pra-konfigurasi untuk menguji seluruh alur proses bisnis:

| Role | Username | Password | Deskripsi Kewenangan |
|---|---|---|---|
| **Admin Desa** | `admin` | `admin123` | Verifikasi KTP warga, Mode B, SYSTEM_CONFIG, Audit Log, Pengecualian surat |
| **Kepala Desa** | `kades` | `kades123` | Persetujuan akhir, penerbitan surat resmi PDF + QR code |
| **Sekretaris Desa** | `sekdes` | `sekdes123` | Verifikasi administrasi lanjutan, laporan |
| **Ketua RT 01 / RW 02** | `rt01` | `rt123` | Verifikasi pengajuan warga wilayah RT 01 / RW 02 |
| **Warga (Aktif)** | `warga_budi` | `warga123` | Mengajukan surat, tracking progress bar, revisi, unduh PDF |
| **Warga Baru (Pending)** | `warga_baru` | `warga123` | Akun baru menunggu verifikasi KTP oleh Admin |

---

## ⚙️ Beralih ke Database MySQL (XAMPP / Server)
Jika ingin menggunakan database MySQL:
1. Pastikan layanan MySQL di XAMPP / MariaDB telah aktif di port `3306`.
2. Buat database baru bernama `sipandu_db`.
3. Buka file `.env` dan ubah:
   ```env
   DB_ENGINE=mysql
   DB_NAME=sipandu_db
   DB_USER=root
   DB_PASSWORD=
   DB_HOST=127.0.0.1
   DB_PORT=3306
   ```
4. Jalankan `python manage.py migrate` dan `python seed_data.py`.

---

## 🧪 Menjalankan Automated Unit & Integration Tests
Untuk menguji logika bisnis sesuai kriteria penerimaan PRD (§5.2 & §5.3):
```powershell
python manage.py test
```

## ⏰ Pengecekan Timeout & Eskalasi SLA (§18)
Untuk mensimulasikan reminder dan eskalasi otomatis tugas tertahan:
```powershell
python manage.py check_timeout_escalation
```
