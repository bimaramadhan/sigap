# Level Siaga Banjir Indonesia

> Sumber: BMKG, BBWS, SOP BPBD
> Status: TEMPLATE — isi dengan angka TMA spesifik per sungai dari BPBD setempat

---

## Klarifikasi: Dua Sistem yang Berbeda

**Level Siaga Banjir (dokumen ini)** = Level teknis berbasis Tinggi Muka Air (TMA)
sungai. Digunakan oleh petugas lapangan dan BPBD untuk operasional.

**Status Keadaan Darurat BNPB** = Penetapan formal pemerintah (Bupati/Gubernur/Presiden)
yang membuka akses dana darurat dan kewenangan khusus.
→ Lihat: `sop/status_keadaan_darurat_bnpb.md`

Keduanya berjalan paralel. Level TMA memicu tindakan lapangan.
Status BNPB memungkinkan dukungan sumber daya yang lebih besar.

---

## Definisi Level Siaga

### 🟢 SIAGA 4 — Normal

**Kondisi:**
- TMA (Tinggi Muka Air) sungai di bawah batas waspada
- Tidak ada peringatan cuaca ekstrem dari BMKG

**Tindakan:**
- Monitoring rutin harian
- Cek kondisi pintu air dan pompa
- Pastikan jalur evakuasi tidak terhalang

---

### 🟡 SIAGA 3 — Waspada

**Trigger:**
- TMA mendekati batas waspada (isi angka spesifik per sungai)
- BMKG prakiraan hujan lebat 24 jam ke depan
- Curah hujan kumulatif mencapai ... mm/6jam

**Tindakan BPBD:**
- Aktifkan posko pantau 24 jam
- Cek kondisi pintu air, pompa, dan tanggul
- Informasikan ke lurah/camat di zona rawan
- Siapkan daftar kontak koordinator RT/RW zona merah

**Tindakan koordinator lapangan:**
- Pantau kondisi sungai setiap 1 jam
- Laporkan ke posko jika ada perubahan signifikan

---

### 🟠 SIAGA 2 — Siaga

**Trigger:**
- TMA mencapai batas siaga
- Hujan >50mm/3jam ATAU TMA naik >20cm/jam
- BMKG mengeluarkan alert Severe untuk provinsi terkait

**Tindakan BPBD:**
- Aktifkan Tim Reaksi Cepat (TRC)
- Preposisi perahu di titik-titik strategis
- Notifikasi warga zona merah via RT/RW
- Siapkan dan buka tempat pengungsian
- Koordinasikan dengan Dinas Sosial untuk logistik

**Tindakan koordinator lapangan:**
- Mulai evakuasi mandiri kelompok rentan (lansia, balita, disabilitas)
- Pastikan kendaraan evakuasi siap
- Dokumentasi kondisi lapangan (foto/video)

---

### 🔴 SIAGA 1 — Awas (Evakuasi)

**Trigger:**
- TMA melampaui batas bahaya
- Tanggul/pintu air tidak mampu menahan debit
- BMKG mengeluarkan alert Extreme

**Tindakan BPBD:**
- Evakuasi wajib seluruh warga zona merah
- **Prioritas pertama:** lansia, balita, ibu hamil, disabilitas
- Deploy semua unit SAR dan perahu
- Koordinasi dengan TNI/Polri untuk bantuan evakuasi
- Buka dapur umum di titik pengungsian
- Aktifkan Emergency Operation Center (EOC)

**Tindakan koordinator lapangan:**
- Pastikan tidak ada warga tertinggal di zona merah
- Evakuasi harta benda penting (dokumen, obat-obatan)
- Laporkan kondisi real-time setiap 30 menit

---

## Catatan Implementasi SIGAP

Pemetaan dari skor SIGAP ke level siaga:

| Skor SIGAP | Level | Keterangan |
|---|---|---|
| 0–25 | SIAGA 4 | Normal, pantau rutin |
| 25–50 | SIAGA 3 | Waspada, tingkatkan monitoring |
| 50–75 | SIAGA 2 | Siaga, aktifkan kesiapsiagaan |
| 75–100 | SIAGA 1 | Awas, evakuasi segera |

*Catatan: Mapping ini perlu dikalibrasi dengan data historis BNPB.*

---

## TODO untuk Bima

- [ ] Isi angka TMA spesifik untuk Sungai Banjirkanal Barat Semarang
- [ ] Isi angka TMA spesifik untuk Kali Bekasi
- [ ] Tambahkan referensi nomor peraturan yang spesifik
- [ ] Verifikasi dengan SOP BPBD Semarang yang sudah didownload
