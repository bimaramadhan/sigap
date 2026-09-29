# Folder `raw/` — File Asli

Taruh semua file yang didownload dari internet di sini.

## File yang sudah ada (isi sesuai yang didownload)

Contoh:
- `perka_bnpb_7_2015.pdf`
- `rencana_kontinjensi_banjir_semarang.pdf`
- `panduan_evakuasi_bnpb.pdf`
- `sp2020_kota_semarang.xlsx`
- dll.

## Cara menggunakannya

File-file ini **tidak langsung dibaca AI**. Setelah download:

1. Buka file PDF/Word
2. Cari bagian yang relevan (level siaga, prosedur, data)
3. Salin informasi penting ke file `.md` yang sesuai:
   - Prosedur → `../sop/`
   - Info kota → `../kota/`
   - Kejadian historis → `../historis/`

## Jangan commit file besar ke git

Tambahkan ke `.gitignore` jika file > 10MB:
```
knowledge/raw/*.pdf
knowledge/raw/*.xlsx
knowledge/raw/*.docx
```
