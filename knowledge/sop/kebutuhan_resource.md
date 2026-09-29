# Estimasi Kebutuhan Resource Penanggulangan Banjir

> Sumber: Sphere Handbook, Pedoman BNPB, data lapangan BPBD
> Status: TEMPLATE — verifikasi angka dengan sumber yang didownload

---

## Rumus Estimasi Resource

SIGAP menggunakan formula berikut untuk menghitung kebutuhan:

```
Jiwa terdampak = total_populasi × flood_ratio × 0.4
  (asumsi: 40% dari area banjir akan butuh bantuan aktif)

Perahu minimal = ceil(jiwa_terdampak / 500)
  (1 perahu kapasitas ~10 orang, rotasi ~50 jiwa per hari)

Tim SAR = ceil(perahu × 1.5)
  (1.5 tim per perahu untuk operasi optimal)

Titik pengungsian = ceil(jiwa_terdampak / 200)
  (kapasitas rata-rata 200 jiwa per titik)

Logistik = 3 hari
  (standar minimum untuk respons awal)
```

---

## Tabel Referensi Cepat

| Jiwa Terdampak | Perahu | Tim SAR | Titik Pengungsian |
|---|---|---|---|
| 100–500 | 1–2 | 2–3 | 1 |
| 500–1.000 | 2–3 | 3–5 | 2–3 |
| 1.000–5.000 | 3–10 | 5–15 | 5–10 |
| 5.000–20.000 | 10–40 | 15–60 | 10–25 |
| >20.000 | >40 | >60 | >25 + minta bantuan provinsi |

---

## Kapasitas Resource BPBD Kota

> Isi dengan data aktual dari masing-masing BPBD

### BPBD Kota Semarang (estimasi / isi dari sumber resmi)
- Perahu karet: ... unit
- Perahu fiber: ... unit
- Tim SAR terlatih: ... orang
- Kendaraan evakuasi: ...
- Gudang logistik: Jl. ... (kapasitas ... ton)

### BPBD Kota Bekasi (estimasi / isi dari sumber resmi)
- Perahu karet: ... unit
- Tim SAR terlatih: ... orang

---

## Eskalasi: Kapan Minta Bantuan

### Level kota → minta bantuan provinsi
- Jika >50.000 jiwa terdampak
- Jika resource kota habis dalam 6 jam pertama
- Jika ada korban jiwa >5 orang

### Level provinsi → minta bantuan nasional (BNPB)
- Jika >100.000 jiwa terdampak
- Jika bencana lintas kabupaten/kota
- Jika infrastruktur kritis rusak (jembatan, PDAM, listrik)

---

## TODO untuk Bima

- [ ] Verifikasi kapasitas resource BPBD Semarang dari sumber resmi
- [ ] Cari data kapasitas tempat pengungsian per kecamatan Semarang
- [ ] Tambahkan nomor hotline BPBD, BNPB, PMI, TNI per kota
- [ ] Cek apakah ada database aset BPBD yang bisa diakses
