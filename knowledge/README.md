# Knowledge Base SIGAP

Folder ini berisi semua dokumen yang digunakan sebagai konteks
oleh Gemini AI untuk menghasilkan rekomendasi tindakan yang
berbasis prosedur nyata — bukan hasil karang.

---

## Struktur Folder

```
knowledge/
│
├── sop/                    ← Prosedur dan aturan BPBD/BNPB
│   ├── level_siaga_banjir.md
│   ├── tindakan_per_level.md
│   ├── prioritas_evakuasi.md
│   └── kebutuhan_resource.md
│
├── kota/                   ← Karakteristik banjir per kota
│   ├── semarang.md
│   ├── bekasi.md
│   └── jakarta.md
│
├── historis/               ← Dokumentasi kejadian banjir nyata
│   ├── banjir_semarang_2024.md
│   └── template_kejadian.md
│
├── referensi/              ← Istilah, definisi, kontak
│   ├── istilah_dan_definisi.md
│   └── sumber_data.md
│
└── raw/                    ← File asli yang didownload (PDF, Word, dll)
    ├── perka_bnpb_*.pdf
    ├── rencana_kontinjensi_*.pdf
    └── ...
```

---

## Aturan Penting

### File di `raw/` — taruh file asli di sini

Semua file yang didownload dari internet (PDF, DOCX, Excel) masuk ke
folder `raw/`. Folder ini **tidak dibaca langsung oleh AI** — isinya
perlu dipindahkan/disarikan ke file `.md` yang sesuai.

Contoh:
```
raw/perka_bnpb_7_2015.pdf          → ringkasannya → sop/level_siaga_banjir.md
raw/rencana_kontinjensi_semarang.pdf → ringkasannya → kota/semarang.md
raw/sp2020_semarang.xlsx            → datanya      → kota/semarang.md
```

### File `.md` — yang dibaca AI

File Markdown di folder `sop/`, `kota/`, `historis/`, `referensi/`
adalah yang langsung dimasukkan ke konteks Gemini. Tulis dalam
**bahasa Indonesia yang jelas**, gunakan bullet points, hindari
paragraf panjang yang susah di-parse.

### Format yang baik untuk AI

```markdown
## Level Siaga 2

**Trigger:**
- TMA sungai mencapai X cm
- Curah hujan >50mm dalam 3 jam
- BMKG mengeluarkan alert Severe/Extreme

**Tindakan wajib BPBD:**
- Aktifkan Tim Reaksi Cepat (TRC)
- Preposisi perahu di titik A, B, C
- Notifikasi lurah/camat zona merah

**Tindakan wajib koordinator lapangan:**
- ...
```

Hindari format ini (susah di-parse AI):
```
Pada level siaga 2, yang merupakan level dimana tinggi muka air
sungai sudah mencapai batas yang telah ditentukan sebelumnya,
maka pihak BPBD diwajibkan untuk mengambil tindakan-tindakan
yang telah diatur dalam prosedur operasional standar...
```

---

## Status File

| File | Status | Sumber |
|---|---|---|
| `sop/level_siaga_banjir.md` | 🔲 Belum | Perka BNPB, SOP BPBD |
| `sop/tindakan_per_level.md` | 🔲 Belum | SOP BPBD |
| `sop/prioritas_evakuasi.md` | 🔲 Belum | Panduan BNPB |
| `sop/kebutuhan_resource.md` | 🔲 Belum | Sphere Handbook |
| `kota/semarang.md` | 🔲 Belum | BPBD Semarang, InaRisk |
| `kota/bekasi.md` | 🔲 Belum | BPBD Bekasi |
| `kota/jakarta.md` | 🔲 Belum | BPBD DKI |
| `historis/banjir_semarang_2024.md` | 🔲 Belum | Berita, BNPB |

Update status ke ✅ saat file sudah diisi.
