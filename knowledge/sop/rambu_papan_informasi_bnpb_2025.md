# Rambu dan Papan Informasi Bencana — Peraturan BNPB No. 3 Tahun 2025

> Sumber: Peraturan Badan Nasional Penanggulangan Bencana Nomor 3 Tahun 2025
> Tentang: Rambu dan Papan Informasi Bencana
> Menggantikan: Peraturan Kepala BNPB Nomor 7 Tahun 2015
> Ditandatangani: Suharyanto (Kepala BNPB), Jakarta 8 Mei 2025
> Masa transisi: Rambu lama masih berlaku max 5 tahun sejak peraturan ini berlaku

---

## KRITIS untuk SIGAP: Kode Warna Resmi Bencana (Pasal 14–21, Lampiran II)

Peraturan ini menetapkan **standar warna nasional** untuk rambu bencana di Indonesia.
SIGAP harus menggunakan warna yang konsisten dengan standar ini agar dapat
diintegrasikan ke sistem BPBD.

### Kode Warna Rambu per Fungsi

| Jenis Rambu | Warna Dasar | Garis Tepi | Piktogram/Huruf | Fungsi |
|---|---|---|---|---|
| **Rambu Peringatan** | 🟡 **Kuning** | Hitam | Hitam | Area/kawasan rawan bencana |
| **Rambu Larangan** | ⬜ Putih | 🔴 Merah | Hitam | Aktivitas yang dilarang di zona bencana |
| **Rambu Petunjuk** | 🟢 **Hijau** | Putih | Putih | Arah evakuasi + lokasi aman |
| **Rambu Sementara** | 🟠 **Jingga** | Hitam | Hitam | Informasi saat darurat aktif |

### Mapping ke SIGAP — Konsistensi dengan BNPB No. 2 Tahun 2024

Kedua peraturan BNPB 2024 dan 2025 **konsisten satu sama lain**:

| Level (Peraturan BNPB No.2/2024) | Warna Resmi | Rambu Terkait (No.3/2025) |
|---|---|---|
| NORMAL | 🟢 Hijau | Rambu Petunjuk (lokasi aman, jalur evakuasi) |
| WASPADA | 🟡 Kuning | Rambu Peringatan (kawasan rawan) |
| SIAGA | 🟠 Oranye/Jingga | Rambu Sementara (situasi darurat aktif) |
| AWAS | 🔴 Merah | Rambu Larangan (zona berbahaya, jangan masuk) |

**Implikasi untuk peta SIGAP:**
- Flood zone overlay warna **kuning** = kawasan rawan (sesuai rambu peringatan)
- Jalur evakuasi warna **hijau** = sesuai rambu petunjuk arah evakuasi
- Area aktif darurat warna **jingga/oranye** = sesuai rambu sementara
- Zona terlarang warna **merah** = sesuai rambu larangan

---

## 8 Jenis Bencana yang Tercakup (Pasal 2)

Rambu dan papan informasi minimal harus mencakup:
1. **Gempa bumi**
2. **Tsunami**
3. **Erupsi gunung api**
4. **Longsor**
5. **Banjir** ← paling relevan untuk SIGAP
6. **Banjir bandang**
7. **Kebakaran hutan dan lahan**
8. **Gagal teknologi**

---

## Isi Wajib Papan Informasi Bencana (Pasal 26)

Setiap Papan Informasi Bencana harus memuat:

a. **Peta bahaya/rawan Bencana** ← SIGAP sudah punya
b. **Sejarah kejadian Bencana** ← perlu data historis
c. **Rencana dan peta evakuasi Bencana** ← SIGAP perlu tambahkan
d. **Informasi kawasan rawan Bencana**
e. **Informasi potensi bahaya/ancaman** ← SIGAP sudah punya
f. **Langkah penyelamatan diri**
g. **Kontak darurat** ← SIGAP perlu tambahkan
h. Informasi lainnya terkait penanggulangan Bencana

**Ini adalah checklist konten untuk dashboard SIGAP** — setiap item di atas
harus ada di output SIGAP sesuai peraturan.

---

## 3 Jenis Rambu yang Relevan untuk SIGAP

### 1. Rambu Peringatan (Kuning) — Kawasan Rawan Banjir

Contoh piktogram yang tersedia (dari Lampiran II):
- Peringatan kawasan rawan banjir
- Peringatan kawasan rawan banjir bandang

**Untuk SIGAP:** Flood zone overlay di peta sebaiknya menggunakan warna kuning
untuk zona waspada, konsisten dengan rambu fisik di lapangan.

### 2. Rambu Petunjuk (Hijau) — Evakuasi dan Titik Aman

Dua jenis rambu petunjuk:
- **Rambu petunjuk lokasi evakuasi** — gedung/fasilitas tempat berkumpul
- **Rambu petunjuk lokasi pengungsian** — tempat menginap jangka pendek

**Untuk SIGAP:** Titik evakuasi di peta harus ditandai warna hijau.
Jalur evakuasi di peta juga hijau.

### 3. Rambu Sementara (Jingga) — Saat Darurat Aktif

Digunakan **khusus saat status keadaan darurat bencana** aktif.
Bersifat tidak permanen, dapat dipindahkan.

Konten rambu sementara:
- Informasi kejadian bencana yang sedang terjadi
- Peringatan ancaman dan/atau dampak bencana susulan

**Untuk SIGAP:** Ketika status SIAGA atau AWAS aktif, tampilkan overlay
oranye/jingga sebagai penanda darurat aktif (bukan hanya zone warna statis).

---

## Penyelenggara Rambu (Pasal 3-4)

Rambu diselenggarakan oleh **Pemerintah Daerah kabupaten/kota** dengan dukungan:
- BNPB
- Kementerian/lembaga terkait
- Pemerintah Daerah provinsi
- Masyarakat, lembaga usaha, akademisi

Koordinasi melalui **BPBD Kabupaten/Kota**.

**Implikasi:** BPBD adalah pengelola rambu fisik. SIGAP sebagai sistem digital
harus konsisten dengan rambu fisik yang sudah dipasang BPBD di lapangan —
koordinator lapangan akan menghubungkan informasi digital dengan rambu fisik
yang mereka lihat.

---

## Isi Laporan Survei Lapangan (Pasal 8 Ayat 3)

Survei untuk penempatan rambu harus memuat:
1. Jenis Rambu dan Papan Informasi
2. Jumlah Rambu dan Papan Informasi
3. **Lokasi dan titik koordinat** penempatan dan pemasangan ← sangat relevan
4. Rekomendasi

**Untuk SIGAP:** Data titik koordinat rambu dari BPBD bisa diintegrasikan
ke peta SIGAP sebagai layer "Infrastruktur Kesiapsiagaan" yang menunjukkan
di mana rambu sudah terpasang dan di mana belum.

---

## Evaluasi Tahunan (Pasal 12)

Evaluasi dilaksanakan paling sedikit **1 kali dalam setahun**, mempertimbangkan:
- Perubahan informasi risiko bencana

Laporan evaluasi memuat:
1. Analisis
2. Kesimpulan
3. Rekomendasi

**Implikasi:** SIGAP dapat membantu BPBD mempersiapkan data untuk evaluasi
tahunan ini dengan menyediakan laporan historis dan perubahan risiko berbasis data.

---

## Konten Papan Informasi Evakuasi Banjir (Lampiran II)

Dari contoh di Lampiran II, papan informasi evakuasi banjir yang baik memuat:

**Legenda peta (standar):**
- 🟢 Area terbuka (outdoor refuge area)
- 🟢 Tempat perlindungan (protection shelter)
- 🟢 Jalur evakuasi (evacuation route)
- 🟢 Rute yang dapat diakses (accessible route)
- 🔴 Zona bahaya banjir (flood hazard zone)
- 🔴 Tanah longsor (steep slope failure, landslide)
- 📍 Stasiun kereta, Rumah Sakit, Kantor Pos, Taman, Hotel

**Informasi konteks:**
- Jika tanggul hancur, area ini berisiko banjir dengan kedalaman lebih dari X meter
- Evakuasi area ini dengan cepat dan berlindung di luar ruangan

**Kontak darurat yang harus ada:**
- Nomor BPBD setempat
- Nomor ambulans
- Nomor pemadam kebakaran
- Nomor polisi

---

## Spesifikasi Teknis Piktogram Bencana (Lampiran II)

Piktogram standar yang tersedia untuk peta digital SIGAP:

| Bencana | Piktogram |
|---|---|
| Tsunami | 🌊 |
| Angin Puting Beliung | 🌪️ |
| Erupsi Gunung Api | 🌋 |
| Longsor | 🏔️ |
| Banjir Bandang | 💧 |
| **Banjir** | 💧 |
| Kebakaran Hutan | 🔥 |
| Gedung Evakuasi Tsunami | 🏢 |
| Area Evakuasi Tsunami | 📍 |
| Lokasi Evakuasi | 📍 |
| Lokasi Pengungsian | 🏕️ |

---

## Update Peta SIGAP Berdasarkan Peraturan Ini

### Sebelum vs. Sesudah (Rekomendasi)

| Elemen Peta | Sebelum | Sesuai BNPB No.3/2025 |
|---|---|---|
| Zona rawan banjir | Warna merah/oranye/kuning (arbitrary) | Kuning = peringatan, Merah = bahaya aktif |
| Jalur evakuasi | Belum ada | Hijau dengan panah arah |
| Titik pengungsian | Belum ada | Hijau dengan piktogram lokasi pengungsian |
| Status darurat aktif | Tidak ada marker khusus | Oranye/Jingga overlay |
| Kontak darurat | Tidak ada | Wajib ada di info panel |

---

## Hubungan dengan Regulasi Lain

| Peraturan | Isi | Relevansi SIGAP |
|---|---|---|
| BNPB No. 3/2025 (ini) | Standar rambu dan warna | Warna peta, isi papan informasi |
| BNPB No. 2/2024 | Sistem peringatan dini | Level NORMAL/WASPADA/SIAGA/AWAS |
| Pedoman BNPB 2016 | Penetapan status darurat | Prosedur dan timeline tindakan |

Ketiga dokumen ini **saling melengkapi** dan semuanya harus dijadikan referensi SIGAP.

---

*Sumber: Peraturan BNPB No. 3 Tahun 2025 tentang Rambu dan Papan Informasi Bencana*
*Menggantikan: Peraturan Kepala BNPB No. 7 Tahun 2015*
*Kepala BNPB: Suharyanto, Jakarta 8 Mei 2025*
