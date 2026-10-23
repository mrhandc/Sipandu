import os
import io
import qrcode
from datetime import timedelta
from django.conf import settings
from django.utils import timezone
from django.urls import reverse
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from apps.core.models import SystemConfig
from apps.surat.models import Surat, LetterNumberSequence


def generate_qr_code_image(verify_url: str) -> io.BytesIO:
    """Menghasilkan buffer gambar QR Code untuk URL verifikasi (§14)"""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=4,
        border=1,
    )
    qr.add_data(verify_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    return buffer


def terbitkan_surat_digital(pengajuan, request_host="127.0.0.1:8000") -> Surat:
    """
    Menerbitkan Surat Resmi:
    1. Penomoran concurrency-safe (§20)
    2. Perhitungan masa berlaku (§15.2)
    3. Generate PDF + QR Code verifikasi (§14)
    """
    jenis_surat = pengajuan.jenis_surat
    warga = pengajuan.warga
    desa = SystemConfig.get_value('NAMA_DESA', 'Desa Sukamaju')
    kecamatan = SystemConfig.get_value('KECAMATAN', 'Kecamatan Wonosari')
    kabupaten = SystemConfig.get_value('KABUPATEN', 'Kabupaten Malang')
    kode_desa = SystemConfig.get_value('KODE_DESA', 'DSA')
    nama_kades = SystemConfig.get_value('NAMA_KADES', 'H. Moch. Syarifudin, S.Sos.')

    # 1. Nomor surat concurrency safe (§20)
    nomor_surat = LetterNumberSequence.generate_next_number(jenis_surat, kode_desa=kode_desa)

    # 2. Tanggal terbit & kadaluarsa (§15)
    tgl_terbit = timezone.now().date()
    tgl_kadaluarsa = tgl_terbit + timedelta(days=jenis_surat.masa_berlaku_hari)

    # Buat record Surat
    surat = Surat.objects.create(
        nomor_surat=nomor_surat,
        pengajuan=pengajuan,
        jenis_surat=jenis_surat,
        warga=warga,
        tanggal_terbit=tgl_terbit,
        tanggal_kadaluarsa=tgl_kadaluarsa,
        status_surat=Surat.StatusSurat.AKTIF
    )

    # 3. Buat URL Verifikasi
    verify_path = reverse('surat:verifikasi_publik', kwargs={'uuid': str(surat.kode_verifikasi)})
    scheme = "http"
    verify_url = f"{scheme}://{request_host}{verify_path}"

    # 4. Generate PDF menggunakan ReportLab
    pdf_filename = f"surat_{pengajuan.id}_{surat.kode_verifikasi.hex[:8]}.pdf"
    pdf_dir = os.path.join(settings.MEDIA_ROOT, 'surat_pdf')
    os.makedirs(pdf_dir, exist_ok=True)
    pdf_filepath = os.path.join(pdf_dir, pdf_filename)

    doc = SimpleDocTemplate(
        pdf_filepath,
        pagesize=A4,
        rightMargin=2.0 * cm,
        leftMargin=2.0 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm
    )

    styles = getSampleStyleSheet()
    
    # Custom styles
    style_kop_kab = ParagraphStyle('KopKab', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=12, leading=15, alignment=1)
    style_kop_desa = ParagraphStyle('KopDesa', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=14, leading=17, alignment=1)
    style_kop_sub = ParagraphStyle('KopSub', parent=styles['Normal'], fontName='Helvetica', fontSize=9, leading=12, alignment=1)
    style_title = ParagraphStyle('Title', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=12, leading=14, alignment=1)
    style_subtitle = ParagraphStyle('SubTitle', parent=styles['Normal'], fontName='Helvetica', fontSize=10, leading=12, alignment=1)
    style_body = ParagraphStyle('Body', parent=styles['Normal'], fontName='Helvetica', fontSize=10, leading=14, alignment=4)
    style_label = ParagraphStyle('Label', parent=styles['Normal'], fontName='Helvetica', fontSize=10, leading=14)
    style_val = ParagraphStyle('Val', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=10, leading=14)
    style_qr_note = ParagraphStyle('QRNote', parent=styles['Normal'], fontName='Helvetica', fontSize=7, leading=9, alignment=1)
    style_ttd = ParagraphStyle('TTD', parent=styles['Normal'], fontName='Helvetica', fontSize=10, leading=14, alignment=1)

    elements = []

    # Kop Surat
    elements.append(Paragraph(f"PEMERINTAH {kabupaten.upper()}", style_kop_kab))
    elements.append(Paragraph(f"KECAMATAN {kecamatan.upper()}", style_kop_kab))
    elements.append(Paragraph(f"KANTOR KEPALA {desa.upper()}", style_kop_desa))
    elements.append(Paragraph(f"Alamat: Jl. Raya Desa No. 01 {desa}, Kode Pos 65100", style_kop_sub))
    elements.append(Spacer(1, 4))
    elements.append(HRFlowable(width="100%", thickness=2, color=colors.black, spaceBefore=1, spaceAfter=1))
    elements.append(HRFlowable(width="100%", thickness=0.8, color=colors.black, spaceBefore=0, spaceAfter=14))

    # Judul Surat
    elements.append(Paragraph(f"<u>{jenis_surat.nama.upper()}</u>", style_title))
    elements.append(Paragraph(f"Nomor: {nomor_surat}", style_subtitle))
    elements.append(Spacer(1, 14))

    # Paragraf Pembuka
    pembuka = (
        f"Yang bertanda tangan di bawah ini Kepala {desa}, {kecamatan}, {kabupaten}, "
        f"dengan ini menerangkan bahwa:"
    )
    elements.append(Paragraph(pembuka, style_body))
    elements.append(Spacer(1, 8))

    # Tabel Data Pemohon
    wilayah_str = str(warga.wilayah) if warga.wilayah else "-"
    data_pemohon = [
        [Paragraph("Nama Lengkap", style_label), Paragraph(":", style_label), Paragraph(warga.get_full_name() or warga.username, style_val)],
        [Paragraph("NIK", style_label), Paragraph(":", style_label), Paragraph(warga.nik or "-", style_val)],
        [Paragraph("Nomor Telepon", style_label), Paragraph(":", style_label), Paragraph(warga.no_hp or "-", style_label)],
        [Paragraph("Alamat / Domisili", style_label), Paragraph(":", style_label), Paragraph(f"{warga.alamat} ({wilayah_str})", style_label)],
        [Paragraph("Keperluan", style_label), Paragraph(":", style_label), Paragraph(pengajuan.keperluan, style_label)],
    ]

    # Data Tambahan spesifik surat
    if pengajuan.data_tambahan:
        for k, v in pengajuan.data_tambahan.items():
            label = k.replace('_', ' ').capitalize()
            data_pemohon.append([
                Paragraph(label, style_label),
                Paragraph(":", style_label),
                Paragraph(str(v), style_label)
            ])

    t_pemohon = Table(data_pemohon, colWidths=[4.2 * cm, 0.6 * cm, 11.5 * cm])
    t_pemohon.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
    ]))
    elements.append(t_pemohon)
    elements.append(Spacer(1, 10))

    # Keterangan Substantif
    isi_keterangan = (
        f"Berdasarkan data kependudukan dan hasil verifikasi berjenjang RT/RW, yang bersangkutan "
        f"benar-benar merupakan warga {desa} dan memenuhi seluruh kriteria administrasi untuk "
        f"diberikan <b>{jenis_surat.nama}</b>."
    )
    elements.append(Paragraph(isi_keterangan, style_body))
    elements.append(Spacer(1, 6))

    penutup = (
        f"Demikian surat keterangan ini dibuat dengan sebenarnya agar dapat dipergunakan sebagaimana mestinya. "
        f"Surat ini berlaku mulai tanggal <b>{tgl_terbit.strftime('%d-%m-%Y')}</b> sampai dengan <b>{tgl_kadaluarsa.strftime('%d-%m-%Y')}</b>."
    )
    elements.append(Paragraph(penutup, style_body))
    elements.append(Spacer(1, 20))

    # Tanda Tangan & QR Code Verifikasi (§14 Legalitas Hybrid)
    qr_img_buffer = generate_qr_code_image(verify_url)
    qr_flowable = RLImage(qr_img_buffer, width=2.4 * cm, height=2.4 * cm)

    qr_cell = [
        qr_flowable,
        Spacer(1, 2),
        Paragraph("<b>Pindai untuk Verifikasi Keaslian</b>", style_qr_note),
        Paragraph(f"UUID: {str(surat.kode_verifikasi)[:13]}...", style_qr_note)
    ]

    ttd_cell = [
        Paragraph(f"{desa}, {tgl_terbit.strftime('%d %B %Y')}", style_ttd),
        Paragraph("<b>Kepala Desa Sukamaju</b>", style_ttd),
        Spacer(1, 38),
        Paragraph(f"<b><u>{nama_kades}</u></b>", style_ttd),
        Paragraph("NIP. 19780512 200501 1 008", style_ttd),
    ]

    t_footer = Table([[qr_cell, "", ttd_cell]], colWidths=[6 * cm, 3 * cm, 7 * cm])
    t_footer.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (0, 0), (0, 0), 'CENTER'),
        ('ALIGN', (2, 0), (2, 0), 'CENTER'),
    ]))
    elements.append(t_footer)

    doc.build(elements)

    surat.file_pdf = f"surat_pdf/{pdf_filename}"
    surat.save(update_fields=['file_pdf'])

    return surat
