# SIGAP — Sistem Integrasi Geospasial Aksi Penanggulangan Bencana

> **Flood Response Decision Engine** — AI-powered disaster coordination for Indonesia
>
> SIGAP bukan sistem prediksi banjir. SIGAP mengambil prediksi yang sudah ada
> dan menjawab pertanyaan yang belum pernah dijawab:
> **siapa harus melakukan apa, kapan, dan dalam urutan apa.**

---

## Daftar Isi

- [Latar Belakang](#latar-belakang)
- [Arsitektur Sistem](#arsitektur-sistem)
- [Data Sources](#data-sources)
- [Bagaimana AI Bekerja](#bagaimana-ai-bekerja)
- [Status Komponen](#status-komponen)
- [Struktur Project](#struktur-project)
- [Setup & Cara Menjalankan](#setup--cara-menjalankan)
- [API Endpoints](#api-endpoints)
- [Kota yang Didukung](#kota-yang-didukung)
- [Knowledge Base](#knowledge-base)
- [Roadmap](#roadmap)
- [Tim](#tim)

---

## Latar Belakang

Indonesia mencatat **3.472 kejadian bencana** (2024), 99% hidrometeorologis.
**5,7 juta jiwa** terdampak banjir. Budget BNPB turun 97% sejak 2020.

Masalah bukan prediksi — BMKG sudah punya sistem peringatan dini yang baik.
Masalahnya adalah **jeda antara peringatan dan tindakan**. Koordinator BPBD masih
mengkoordinasikan evakuasi lewat telepon manual, mengirim resource berdasarkan
intuisi, dan tidak tahu siapa yang paling rentan di zona banjir.

SIGAP mengisi jeda itu.

---

## Arsitektur Sistem

```
┌─────────────────────────────────────────────────────────────────────┐
│                         DATA SOURCES                                │
│                                                                     │
│  BMKG Nowcast API ──────────────────────┐  ✅ Real-time, no auth   │
│  BMKG Prakiraan Cuaca API ──────────────┤  ✅ Real-time, no auth   │
│  InaRisk BNPB GIS ─────────────────────┘  ✅ Live, no auth         │
│    • INDEKS_BAHAYA_BANJIR (100m raster)                             │
│    • INDEKS_KAPASITAS_2021                                          │
│    • INARISKPOP_2020                                                │
│    • batas_administrasi (kecamatan polygons)                        │
│                                                                     │
│  Google Earth Engine ──────────────── ⚠️  Fallback, butuh auth     │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                          AI ENGINE                                  │
│                                                                     │
│  vulnerability.py ── Weighted scoring 5 komponen (0-100)           │
│  + weather_boost    ── BMKG curah hujan 12 jam (0-25 poin)         │
│  + alert_boost      ── BMKG alert severity (0-25 poin)             │
│  + field_report_boost ── Laporan BPBD lapangan (0-30 poin)         │
│       │                                                             │
│       ▼                                                             │
│  narrator.py ── Gemini 1.5 Flash + RAG knowledge base              │
│               → Narasi bahasa Indonesia, actionable                 │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        SERVING LAYER                                │
│                                                                     │
│  FastAPI (api/main.py) — localhost:8080                             │
│  React + Vite (frontend/) — localhost:3000                          │
│    • Peta Leaflet dengan polygon kecamatan dari InaRisk BNPB        │
│    • Dashboard koordinator BPBD                                     │
│    • Form laporan lapangan (input TMA sungai, area genangan)        │
│    • Dark/Light mode                                                │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Data Sources

### Tersedia Sekarang (Tanpa Setup Apapun)

| Data | Sumber | Endpoint | Status |
|---|---|---|---|
| **Peringatan dini cuaca** | BMKG Nowcast | `bmkg.go.id/alerts/nowcast/id` | ✅ Real-time |
| **Prakiraan cuaca per kecamatan** | BMKG Prakiraan | `api.bmkg.go.id/publik/prakiraan-cuaca?adm4=...` | ✅ Update 2x/hari |
| **Indeks Bahaya Banjir** | InaRisk BNPB | `gis.bnpb.go.id/server/rest/services/inarisk/INDEKS_BAHAYA_BANJIR` | ✅ Resolusi 100m |
| **Indeks Kapasitas Daerah** | InaRisk BNPB | `...INDEKS_KAPASITAS_2021` | ✅ |
| **Populasi 2020** | InaRisk BNPB | `...INARISKPOP_2020` | ✅ Jiwa per 100m² |
| **Polygon kecamatan** | InaRisk BNPB | `...batas_administrasi/MapServer/3` | ✅ Seluruh Indonesia |

### Membutuhkan Setup

| Data | Sumber | Status |
|---|---|---|
| DEM Elevasi | Google Earth Engine (SRTM) | ⚠️ Fallback dari static data |
| Historical floods | Google Earth Engine (GFD) | ⚠️ Fallback dari static data |
| **Narasi AI adaptif** | Gemini 1.5 Flash via Vertex AI | ⚠️ Butuh GCP + gcloud auth |

> **Catatan:** InaRisk BNPB menggantikan Google Earth Engine sebagai primary source.
> Tidak butuh registrasi, API key, atau setup apapun. Lebih relevan untuk Indonesia.

---

## Bagaimana AI Bekerja

### Vulnerability Score — Formula Deterministik

Skor 0–100 dihitung dari **5 komponen statis** + **3 boost dinamis**:

```
Final Score = base_score + weather_boost + alert_boost + field_report_boost
            = min(100, weighted_sum(5 komponen) × 100 + boosts)
```

#### Komponen Statis (sumber: InaRisk BNPB)

| Komponen | Bobot | Sumber Data | Yang Diukur |
|---|---|---|---|
| Flood Hazard | 30% | INDEKS_BAHAYA_BANJIR | Proporsi area dengan indeks ≥ 0.6 |
| Population Exposure | 25% | INARISKPOP_2020 | Kepadatan penduduk |
| Vulnerable Population | 25% | InaRisk + BPS nasional | Estimasi lansia + balita |
| Historical Frequency | 10% | BNPB DIBI (static) | Frekuensi banjir 2000-2018 |
| Low Elevation Risk | 10% | SRTM DEM (static) | Area di bawah 5m elevasi |

#### Boost Dinamis (membuat skor responsif terhadap kondisi real-time)

| Boost | Sumber | Max Poin | Trigger |
|---|---|---|---|
| **Weather** | BMKG prakiraan cuaca | +25 | Rainfall > 100mm/12jam |
| **Alert** | BMKG nowcast severity | +25 | Alert EXTREME/SEVERE |
| **Field Report** | Input manual BPBD | +30 | TMA sungai SIAGA/AWAS |
| **Total boost cap** | — | +30 | Agar tidak overflow |

**Contoh skenario Semarang:**
```
Baseline (InaRisk live):     49.8   → 🟡 WASPADA
+ Alert BMKG Severe:        +15.0   → 🟠 SIAGA (64.8)
+ TMA Banjirkanal SIAGA:    +15.0   → 🔴 AWAS (79.8)
```

#### Level Resmi (sesuai Peraturan BNPB No.2/2024)

| Skor | Level | Simbol |
|---|---|---|
| 0–25 | NORMAL | 🟢 Hijau |
| 25–50 | WASPADA | 🟡 Kuning |
| 50–75 | SIAGA | 🟠 Oranye |
| 75–100 | AWAS | 🔴 Merah |

### Narasi AI — Gemini dengan RAG

Vulnerability score (angka) → Gemini 1.5 Flash → narasi bahasa Indonesia:

```
Input ke Gemini:
  • Skor 79.8/100 (AWAS)
  • Populasi 1,653,524 jiwa | 291,021 rentan
  • Flood area: 46.4% (InaRisk live)
  • BMKG alert Severe aktif
  • TMA Banjirkanal Barat: 285cm (SIAGA)
  • Knowledge base: SOP BPBD, karakteristik kota, regulasi BNPB

Output Gemini (max 300 kata, bahasa Indonesia):
  "SITUASI AWAS — Kota Semarang menghadapi ancaman banjir serius.
   Kombinasi hujan lebat dan TMA sungai mendekati batas bahaya...
   TINDAKAN PRIORITAS:
   1. Aktifkan Posko Darurat...
   2. Preposisi 3 perahu ke titik A, B, C..."
```

**Fallback:** Template rules deterministik jika Gemini tidak tersedia.

---

## Status Komponen

### Backend / Pipeline

| Komponen | File | Status | Data Source |
|---|---|---|---|
| BMKG alerts | `pipeline/bmkg_ingest.py` | ✅ Real-time | BMKG Nowcast API |
| BMKG weather | `pipeline/bmkg_weather.py` | ✅ Live | BMKG Prakiraan Cuaca API |
| InaRisk features | `pipeline/inarisk_loader.py` | ✅ Live | InaRisk BNPB GIS |
| InaRisk polygons | `pipeline/inarisk_polygon.py` | ✅ On-demand | InaRisk batas_administrasi |
| EE loader | `pipeline/ee_loader.py` | ✅ Fallback only | Google Earth Engine |
| Vulnerability scorer | `engine/vulnerability.py` | ✅ Aktif | InaRisk (primary) |
| Flood report store | `engine/flood_report.py` | ✅ Aktif | Input manual BPBD |
| Gemini narrator | `engine/narrator.py` | ✅ Fallback mode | Butuh GCP auth untuk live |
| FastAPI | `api/main.py` | ✅ 12 endpoints | — |
| POC runner | `run_poc.py` | ✅ Aktif | — |

### Frontend

| Komponen | File | Status | Keterangan |
|---|---|---|---|
| Dashboard layout | `App.jsx` | ✅ | Dark/light mode, 5 tabs |
| Peta Leaflet | `MapView.jsx` | ✅ | Dual-mode: InaRisk polygon / mock fallback |
| Weather bar | `WeatherBar.jsx` | ✅ | Strip kondisi cuaca real-time |
| Alert panel | `AlertPanel.jsx` | ✅ | BMKG alerts dengan severity badge |
| Vulnerability card | `VulnerabilityCard.jsx` | ✅ | Gauge + breakdown 7 komponen |
| AI Briefing | `NarasiPanel.jsx` | ✅ | Narasi + action items + resources |
| Flood input form | `FloodInputPanel.jsx` | ✅ | Input TMA sungai + area genangan |

### Setup yang Belum Selesai

| Task | Prioritas | Dampak jika belum |
|---|---|---|
| `.env` dibuat dari `.env.example` | 🔴 Wajib | Backend tidak bisa jalan |
| Install gcloud CLI | 🟡 Untuk Gemini | Narasi pakai template (masih OK) |
| GCP Project + Gemini auth | 🟡 Untuk Gemini | Narasi pakai template |
| `VITE_USE_MOCK=false` | 🟡 Untuk live frontend | Frontend pakai mock data |

---

## Struktur Project

```
sigap/
│
├── pipeline/                      # Data ingestion
│   ├── bmkg_ingest.py             # ✅ BMKG alert real-time (nowcast + CAP)
│   ├── bmkg_weather.py            # ✅ BMKG prakiraan cuaca per kecamatan
│   ├── inarisk_loader.py          # ✅ InaRisk BNPB: hazard, capacity, population
│   ├── inarisk_polygon.py         # ✅ InaRisk polygon kecamatan + hazard value
│   └── ee_loader.py               # ✅ Earth Engine (fallback)
│
├── engine/                        # Core AI logic
│   ├── vulnerability.py           # ✅ Scoring 5 komponen + 3 dynamic boosts
│   ├── narrator.py                # ✅ Gemini narasi + template fallback
│   └── flood_report.py            # ✅ In-memory store laporan lapangan BPBD
│
├── api/
│   └── main.py                    # ✅ FastAPI 12 endpoints (v0.3.0)
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx                # Layout utama + dark/light + toast
│   │   ├── components/
│   │   │   ├── Header.jsx         # City selector + theme toggle
│   │   │   ├── WeatherBar.jsx     # Strip cuaca real-time BMKG
│   │   │   ├── MapView.jsx        # Leaflet + InaRisk polygon overlay
│   │   │   ├── AlertPanel.jsx     # BMKG alerts
│   │   │   ├── VulnerabilityCard.jsx
│   │   │   ├── NarasiPanel.jsx
│   │   │   └── FloodInputPanel.jsx # Form laporan lapangan BPBD
│   │   ├── hooks/
│   │   │   ├── useAnalysis.js
│   │   │   ├── useFloodReports.js
│   │   │   └── useFloodPolygons.js
│   │   └── lib/
│   │       ├── api.js
│   │       ├── mockData.js
│   │       └── ThemeContext.jsx
│   └── .env.development           # VITE_USE_MOCK=true (default)
│
├── knowledge/                     # Knowledge base untuk Gemini RAG
│   ├── sop/
│   │   ├── level_siaga_banjir.md
│   │   ├── status_keadaan_darurat_bnpb.md  # Pedoman BNPB 2016
│   │   ├── sistem_peringatan_dini_bnpb_2024.md  # Peraturan BNPB No.2/2024
│   │   ├── rambu_papan_informasi_bnpb_2025.md   # Peraturan BNPB No.3/2025
│   │   ├── prioritas_evakuasi.md
│   │   └── kebutuhan_resource.md
│   ├── kota/
│   │   └── semarang.md
│   └── historis/
│       └── template_kejadian.md
│
├── data/
│   └── cache/                     # Auto-generated (gitignored)
│
├── run_poc.py                     # Single entry point
├── test_bmkg_live.py
├── test_weather_integration.py
├── test_inarisk_integration.py
├── extract_pdf.py                 # Utility: ekstrak teks dari PDF
├── requirements.txt
├── .env.example
├── ROADMAP.md                     # Rencana pengembangan lanjutan
└── README.md
```

---

## Setup & Cara Menjalankan

### Prasyarat

| Tools | Versi |
|---|---|
| Python | 3.10+ |
| Node.js | 18+ |

### 1. Setup Python

```powershell
cd sigap
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
Copy-Item .env.example .env
```

### 2. Jalankan backend

```powershell
uvicorn api.main:app --reload --port 8080
# API docs: http://localhost:8080/docs
```

### 3. Jalankan frontend

```powershell
cd frontend
npm install   # sekali saja
npm run dev   # http://localhost:3000
```

Untuk connect frontend ke backend real:
```
# frontend/.env.development
VITE_USE_MOCK=false
```

### 4. Test data pipeline

```powershell
# Test BMKG real-time (tidak butuh setup)
python test_bmkg_live.py

# Test InaRisk integration
python test_inarisk_integration.py

# Test weather boost ke vulnerability
python test_weather_integration.py

# Jalankan full POC (semua pipeline sekaligus)
python run_poc.py semarang
```

### 5. Setup Gemini (opsional, untuk narasi AI adaptif)

```powershell
# 1. Install gcloud CLI: https://cloud.google.com/sdk/docs/install
gcloud auth login
gcloud projects create sigap-hackathon-2026
gcloud config set project sigap-hackathon-2026
gcloud services enable aiplatform.googleapis.com

# 2. Authenticate untuk Gemini
gcloud auth application-default login

# 3. Update .env
# GCP_PROJECT_ID=sigap-hackathon-2026
# DEMO_MODE=false
```

---

## API Endpoints

Backend berjalan di `http://localhost:8080`. Dokumentasi interaktif di `/docs`.

### System

| Method | Endpoint | Fungsi |
|---|---|---|
| `GET` | `/` | Health check + version |
| `GET` | `/cities` | List kota yang didukung |

### Data (real-time)

| Method | Endpoint | Sumber | Cache |
|---|---|---|---|
| `GET` | `/alerts` | BMKG Nowcast | 30 menit |
| `GET` | `/weather/{city}` | BMKG Prakiraan Cuaca | 60 menit |
| `GET` | `/features/{city}` | InaRisk BNPB | 24 jam |
| `GET` | `/flood-polygons/{city}` | InaRisk batas_administrasi | 7 hari |
| `GET` | `/flood-rivers/{city}` | Static data | — |

### Analysis (AI)

| Method | Endpoint | Keterangan |
|---|---|---|
| `GET` | `/vulnerability/{city}` | Skor 0-100 + breakdown + boosts |
| `GET` | `/narasi/{city}` | Narasi bahasa Indonesia |
| `GET` | `/analyze/{city}` | Full pipeline dalam satu request |

### Field Reports (laporan lapangan BPBD)

| Method | Endpoint | Keterangan |
|---|---|---|
| `POST` | `/flood-report` | Submit laporan TMA + area genangan |
| `GET` | `/flood-reports/{city}` | Laporan terbaru (12 jam terakhir) |
| `DELETE` | `/flood-reports/{city}` | Hapus laporan (reset demo) |

---

## Kota yang Didukung

| Kota | Province | Karakteristik Risiko |
|---|---|---|
| **Semarang** | Jawa Tengah | Rob (elevasi -2m), banjir bandang dari hulu |
| **Bekasi** | Jawa Barat | Bantaran Kali Bekasi, kepadatan tinggi |
| **Jakarta** | DKI Jakarta | Pesisir (-3.5m), 48% area berpotensi banjir |
| **Surabaya** | Jawa Timur | Pesisir utara (Kenjeran, Semampir), Kali Mas |

> **Menambah kota baru:** Saat ini perlu update manual di 8+ file.
> Lihat [ROADMAP.md](ROADMAP.md) untuk rencana `city_registry.py` yang
> akan memungkinkan kota apapun di Indonesia tanpa perubahan kode.

---

## Knowledge Base

Folder `knowledge/` berisi dokumen yang digunakan Gemini sebagai referensi
untuk menghasilkan rekomendasi yang sesuai SOP — bukan hasil karang.

### Regulasi yang sudah dimasukkan

| Dokumen | File | Konten Kritis |
|---|---|---|
| Pedoman BNPB 2016 | `sop/status_keadaan_darurat_bnpb.md` | 3 status darurat (Siaga/Tanggap/Transisi), prosedur penetapan |
| Peraturan BNPB No.2/2024 | `sop/sistem_peringatan_dini_bnpb_2024.md` | **4 level resmi: NORMAL/WASPADA/SIAGA/AWAS** + warna standar |
| Peraturan BNPB No.3/2025 | `sop/rambu_papan_informasi_bnpb_2025.md` | Kode warna rambu (kuning/hijau/oranye/merah) — dasar warna peta |

> Level NORMAL/WASPADA/SIAGA/AWAS yang dipakai SIGAP mengikuti
> **Peraturan BNPB No.2 Tahun 2024** — regulasi terbaru dan mengikat.

### Konten yang perlu dilengkapi (Bima)

- `knowledge/sop/level_siaga_banjir.md` — angka TMA spesifik per sungai
- `knowledge/sop/prioritas_evakuasi.md` — SOP evakuasi BPBD
- `knowledge/sop/kebutuhan_resource.md` — kalkulasi perahu/SAR/shelter
- `knowledge/kota/semarang.md` — karakteristik banjir lokal Semarang
- `knowledge/historis/banjir_semarang_2024.md` — kronologi kejadian nyata

---

## Roadmap

Lihat [ROADMAP.md](ROADMAP.md) untuk detail lengkap.

### Jangka Pendek (sebelum Oktober)

- [ ] Lengkapi knowledge base (Bima)
- [ ] Integrasikan knowledge base ke Gemini prompt
- [ ] InaRisk data untuk Bekasi, Jakarta, Surabaya (polygon on-demand)
- [ ] Connect frontend ke backend live

### Jangka Menengah (pasca-hackathon)

- [ ] `city_registry.py` — support semua 514 kabupaten/kota Indonesia
- [ ] Search/autocomplete kota di frontend
- [ ] Banjir Log database (PostgreSQL/Supabase)
- [ ] Re-train threshold dari data historis BNPB
- [ ] Deploy ke Cloud Run

### Direncanakan

- [ ] Level sungai real-time (AWLR BMKG — belum ada public API stabil)
- [ ] Notifikasi push ke WhatsApp koordinator
- [ ] Mobile view yang dioptimasi

---

## Tim

| Role | Tanggung Jawab Utama |
|---|---|
| **Data Scientist** | Pipeline (BMKG, InaRisk), vulnerability scorer, Gemini prompt engineering |
| **Backend** | FastAPI endpoints, integrasi semua komponen, deploy |
| **Frontend** | React dashboard, peta Leaflet, UI/UX |

---

*Terakhir diupdate: September 2026*

**Data real yang sudah terbukti berjalan:**
- BMKG: 17 alert aktif (24 Sep 2026), real-time tanpa setup
- InaRisk Semarang: flood_ratio=46.4%, score=49.8 (live dari BNPB)
- Prakiraan cuaca: Semarang Cerah Berawan 0mm/12jam (29 Sep 2026)
- Polygon kecamatan: 22 kecamatan Semarang dengan nilai bahaya riil
  (Semarang Barat: 0.975 = SANGAT TINGGI)
