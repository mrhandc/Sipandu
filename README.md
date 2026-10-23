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

---

## 🛠️ Tech Stack
- **Bahasa**: Python 3.11+ / 3.12
- **Framework Web**: Django 5.1 (Django ORM, Authentication, Django Admin)
- **Database**: SQLite (default zero-config out of the box) / MySQL support (via PyMySQL)
- **PDF Generation**: ReportLab
- **QR Code**: qrcode + Pillow
- **Frontend**: Django Template + Bootstrap 5 + Bootstrap Icons (Mobile-friendly & responsif)
- **Notifikasi WhatsApp**: Fonnte.com API Gateway (`requests` library)

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

---

## 📱 Notifikasi WhatsApp via Fonnte

SIPANDU mengintegrasikan gateway WhatsApp **[Fonnte.com](https://fonnte.com)** untuk mengirimkan notifikasi otomatis ke seluruh role (Admin, Kepala Desa, Sekdes, RT/RW, Warga).

### Event yang Memicu Notifikasi WhatsApp

| Event | Penerima Notifikasi |
|---|---|
| Pengajuan surat baru oleh Warga | Warga (konfirmasi) + RT/RW wilayah |
| Verifikasi akun AKTIF/DITOLAK | Warga ybs |
| Setiap keputusan approval (Setuju/Tolak/Revisi) | Warga + Admin + Petugas jenjang berikutnya |
| Surat resmi diterbitkan oleh Kepala Desa | Warga + Admin + Sekdes + RT/RW wilayah |
| Warga membatalkan pengajuan | Warga + Admin |
| Permintaan revisi berkas | Warga + Petugas pemroses |
| Verifikasi Mode B oleh Admin | Warga + Sekdes |
| Reminder SLA (T1/T2) | Petugas yang menangani |
| Eskalasi Timeout (T3) | Admin Desa |

### Cara Konfigurasi Token Fonnte

#### 1. Dapatkan Token Fonnte
1. Daftar / Login ke [fonnte.com](https://fonnte.com)
2. Sambungkan perangkat WhatsApp Anda (scan QR Code)
3. Salin **Token** yang tersedia di dashboard Fonnte

#### 2. Set Token via SIPANDU Admin Panel
Login sebagai Admin → **Kelola Admin** → **WhatsApp Gateway (Fonnte)** → masukkan token dan klik **Simpan Token**.

Atau langsung via Django Admin (`/admin/`) → **System Configs** → cari key `FONNTE_TOKEN` → edit value.

#### 3. Konfigurasi via `.env` (Opsional)
```env
FONNTE_ENABLED=True
FONNTE_TOKEN=token_fonnte_anda_disini
```

#### 4. Test Pengiriman
Di halaman **WhatsApp Gateway (Fonnte)**, masukkan nomor tujuan (format `08xxx`) dan pesan, lalu klik **Kirim Tes**.

### Catatan Teknis
- **Mode Simulasi**: Jika token belum diset, sistem **tidak error** — pesan WA dicatat di AuditLog sebagai `WHATSAPP_SIMULATED` dan alur bisnis berjalan normal.
- **Normalisasi Nomor**: Sistem otomatis mengkonversi `08xxx → 628xxx` sesuai format internasional Fonnte.
- **Audit Trail**: Setiap pengiriman WA (sukses/gagal/simulasi) dicatat lengkap di AuditLog dengan target dan response API.
- **Nomor HP Akun Demo**: Sudah diisi nomor dummy untuk setiap akun demo (`admin: 081200000001`, `kades: 081200000002`, `sekdes: 081200000003`, `rt01: 081234567891`, `warga_budi: 081234567890`).
