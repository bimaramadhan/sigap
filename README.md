# SIGAP — Sistem Integrasi Geospasial Aksi Penanggulangan Bencana

> **Flood Response Decision Engine** berbasis Google Cloud
>
> SIGAP bukan sistem prediksi banjir. SIGAP mengambil prediksi yang sudah ada dan menjawab pertanyaan yang belum pernah dijawab: **siapa harus melakukan apa, kapan, dan dalam urutan apa.**

---

## Daftar Isi

- [Latar Belakang](#latar-belakang)
- [Data BMKG — Apa yang Tersedia](#data-bmkg--apa-yang-tersedia)
- [Apa yang Sudah Diimplementasikan](#apa-yang-sudah-diimplementasikan)
- [Status Data Saat Ini](#status-data-saat-ini)
- [Arsitektur Sistem](#arsitektur-sistem)
- [Bagaimana AI Menghasilkan Kesimpulan](#bagaimana-ai-menghasilkan-kesimpulan)
- [Output yang Dihasilkan](#output-yang-dihasilkan)
- [Struktur Project](#struktur-project)
- [Setup & Cara Menjalankan](#setup--cara-menjalankan)
- [Setup Google Cloud](#setup-google-cloud-untuk-data-real)
- [Data Sources](#data-sources)
- [Status Implementasi](#status-implementasi)
- [Tim & Pembagian Kerja](#tim--pembagian-kerja)

---

## Latar Belakang

Indonesia mencatat **3.472 kejadian bencana** pada tahun 2024, dengan 99% di antaranya adalah bencana hidrometeorologis (banjir dan longsor). Sebanyak **5,7 juta jiwa** terdampak banjir di tahun yang sama.

Masalahnya bukan ketiadaan prediksi. BMKG sudah mengeluarkan peringatan dini hingga level kecamatan. Masalahnya adalah **jeda antara "tahu akan banjir" dan "tahu harus berbuat apa"** — dan jeda itu masih diisi oleh telepon manual, keputusan berbasis intuisi, dan resource yang dikirim ke tempat yang salah.

SIGAP hadir untuk mengisi jeda itu.

---

## Data BMKG — Apa yang Tersedia

BMKG menyediakan **Open Data API publik** yang tidak membutuhkan API key, registrasi, atau biaya apapun. Data diperbarui secara real-time setiap saat.

### Endpoint

```
# RSS Feed — daftar semua alert aktif se-Indonesia
GET https://www.bmkg.go.id/alerts/nowcast/id

# CAP Detail — detail per alert termasuk polygon wilayah
GET https://www.bmkg.go.id/alerts/nowcast/id/{kode}_alert.xml

# Versi bahasa Inggris
GET https://www.bmkg.go.id/alerts/nowcast/en
```

Rate limit: 60 request/menit per IP. Wajib mencantumkan BMKG sebagai sumber data.

### Contoh data real yang diterima (24 September 2026, 17 alert aktif)

```
Hujan Lebat disertai Petir di Jawa Barat
  Kecamatan: CARINGIN, CISAAT, KADUDAMPIT
  Mulai: 14:50 WIB → Berakhir: 16:30 WIB

Hujan Lebat disertai Petir di Sumatera Utara
  Kecamatan: AFULU, ALASA, ANGKOLA BARAT, ... (82 kecamatan)
  Mulai: 13:55 WIB → Berakhir: 16:55 WIB

Hujan Lebat disertai Petir di Sumatera Selatan
  Kecamatan: BABAT SUPAT, BANYUASIN II, ... (20 kecamatan)
  Mulai: 14:45 WIB → Berakhir: 16:45 WIB
  ... (14 provinsi lainnya)
```

### Struktur data RSS Feed (Layer 1)

Setiap item alert berisi:

| Field | Contoh | Keterangan |
|---|---|---|
| `title` | "Hujan Lebat disertai Petir di Jawa Barat" | Judul per provinsi |
| `description` | "...di CARINGIN, CISAAT, KADUDAMPIT..." | Kecamatan terdampak |
| `pubDate` | "Thu, 24 Sep 2026 14:40:00 +0700" | Waktu publikasi |
| `link` | `.../CJB20260924001_alert.xml` | URL ke CAP detail |
| `guid` | "2.49.0.1.360.0.2026.09.24..." | ID unik alert |

### Struktur CAP Detail (Layer 2)

Fetch per `link` dari RSS untuk mendapatkan:

| Field | Contoh | Keterangan |
|---|---|---|
| `event` | "Hujan Lebat" | Jenis kejadian |
| `effective` | "2026-09-24T14:50:00+07:00" | Waktu mulai (ISO 8601) |
| `expires` | "2026-09-24T16:30:00+07:00" | Waktu berakhir |
| `severity` | Extreme / Severe / Moderate / Minor | Tingkat keparahan |
| `certainty` | Observed / Likely / Possible | Tingkat kepastian |
| `urgency` | Immediate / Expected / Future | Urgensi |
| `areaDesc` | "CARINGIN, CISAAT, KADUDAMPIT" | Kecamatan terdampak |
| `polygon` | "-6.91,106.78 -6.94,106.82 ..." | **Koordinat wilayah** untuk peta |

### Apa yang TIDAK disediakan BMKG

BMKG hanya memberikan **trigger cuaca** — "di sini akan hujan lebat." Yang tidak ada:

- ❌ Data populasi yang terdampak
- ❌ Data elevasi wilayah
- ❌ Data historis kejadian banjir
- ❌ Estimasi kerentanan penduduk
- ❌ Rekomendasi tindakan

**Ini yang SIGAP tambahkan** — mengolah trigger BMKG menjadi keputusan yang actionable.

---

## Apa yang Sudah Diimplementasikan

### ✅ Pipeline 1 — BMKG Alert Ingestion (`pipeline/bmkg_ingest.py`)

Mengambil dan mengolah peringatan dini cuaca secara real-time.

**Yang dilakukan:**
- Poll RSS feed BMKG, diperbarui setiap saat
- Parse XML format CAP (Common Alerting Protocol) — standar internasional
- Filter alert yang berpotensi banjir berdasarkan kata kunci
- Fetch CAP detail per provinsi: kecamatan terdampak, polygon, severity, timeline
- Cache hasil TTL 30 menit — menghindari rate limit BMKG

**Output JSON:**
```json
{
  "fetched_at": "2026-09-24T07:45:50Z",
  "total": 17,
  "alerts": [
    {
      "province": "Jawa Barat",
      "title": "Hujan Lebat disertai Petir di Jawa Barat",
      "severity": "Severe",
      "kecamatan_list": ["CARINGIN", "CISAAT", "KADUDAMPIT"],
      "effective": "2026-09-24T14:50:00+07:00",
      "expires":   "2026-09-24T16:30:00+07:00",
      "polygons":  ["-6.91,106.78 -6.94,106.82 ..."]
    }
  ]
}
```

---

### ✅ Pipeline 2 — Earth Engine Geospatial Loader (`pipeline/ee_loader.py`)

Mengambil data geospasial dari Google Earth Engine — semua dataset publik dan gratis.

**Yang dilakukan:**
- Load DEM (Digital Elevation Model) dari SRTM 30m → statistik elevasi per kota
- Load Flood Hazard Map dari JRC/Copernicus GloFAS → area berpotensi banjir per return period
- Load Historical Flood Events dari Global Flood Database (2000-2018) → frekuensi kejadian
- Load populasi dari WorldPop 100m grid → total populasi + estimasi kerentanan
- Cache lokal TTL 60 menit — query EE bisa lambat, hindari repeat

**Fallback:** Jika Earth Engine belum authenticated, sistem otomatis pakai **sample data** berdasarkan
data riil Semarang/Bekasi dari publikasi akademik. Pipeline tetap jalan end-to-end.

**Output JSON per kota:**
```json
{
  "dem": {
    "elevation_mean": 18.4,
    "elevation_min": -2.0,
    "elevation_max": 348.0
  },
  "flood_hazard": {
    "10yr": { "flood_ratio": 0.348, "area_km2": { "safe": 142.3, "high": 12.9 } }
  },
  "flood_history": { "historical_events": 14, "avg_per_year": 0.78 },
  "population": {
    "total_population": 1653524,
    "est_vulnerable": 291021,
    "source": "WorldPop 100m grid"
  }
}
```

---

### ✅ Engine 1 — Vulnerability Scorer (`engine/vulnerability.py`)

Menghitung skor kerentanan 0–100 dari kombinasi semua data source.

Penjelasan lengkap di bagian [Bagaimana AI Menghasilkan Kesimpulan](#bagaimana-ai-menghasilkan-kesimpulan).

---

### ✅ Engine 2 — AI Narrator (`engine/narrator.py`)

Mengubah angka dan data teknis menjadi narasi bahasa Indonesia siap baca untuk koordinator BPBD.

**Yang dilakukan:**
- Terima `VulnerabilityResult` dari vulnerability scorer
- Build structured prompt berisi situasi, faktor dominan, rekomendasi sistem
- Kirim ke **Gemini 1.5 Flash** via Vertex AI
- Fallback ke template engine berbasis rules jika Gemini belum tersedia

Penjelasan lengkap di bagian [Bagaimana AI Menghasilkan Kesimpulan](#bagaimana-ai-menghasilkan-kesimpulan).

---

### ✅ Backend API (`api/main.py`)

FastAPI backend dengan 7 endpoints yang melayani frontend dashboard.

| Method | Endpoint | Fungsi |
|---|---|---|
| `GET` | `/` | Health check |
| `GET` | `/cities` | List kota yang didukung |
| `GET` | `/alerts` | BMKG alerts aktif (dengan cache) |
| `GET` | `/features/{city}` | Raw EE geospatial features |
| `GET` | `/vulnerability/{city}` | Vulnerability score + action plan |
| `GET` | `/narasi/{city}` | Narasi AI bahasa Indonesia |
| `GET` | `/analyze/{city}` | Full pipeline: alert + score + narasi |

Dokumentasi interaktif: `http://localhost:8080/docs`

---

### ✅ POC Runner (`run_poc.py`)

Single entry point — jalankan semua pipeline sekaligus, tampilkan di terminal.

```powershell
python run_poc.py semarang
```

Output 4 step: BMKG → Earth Engine → Vulnerability Score → Narasi AI.
Hasil disimpan ke `data/poc_result_{kota}.json`.

---

### ✅ Frontend Dashboard (`frontend/`)

React + Vite dashboard untuk koordinator BPBD.

| Fitur | Detail |
|---|---|
| **Peta Leaflet** | Dark/light tiles (Stadia Maps + OSM), flood zone polygon overlay, fly-to animation, tooltip info zona |
| **Alert Panel** | BMKG alerts real-time, severity badge, collapsible detail, pulse untuk Extreme |
| **Vulnerability Card** | SVG gauge 0–100 dengan animasi, breakdown 5 komponen, stats grid |
| **AI Briefing** | Narasi bahasa Indonesia, action items berwarna, collapsible resource needs |
| **Dark/Light Mode** | Toggle di header, disimpan di localStorage |
| **Auto-refresh** | Data diperbarui setiap 5 menit |
| **Mock/Live toggle** | `VITE_USE_MOCK=true/false` di `.env.development` |

---

## Status Data Saat Ini

Ini penting untuk dipahami — ada perbedaan antara apa yang **terlihat** di dashboard dan apa yang **benar-benar real**.

### Kondisi default (tanpa setup GCP)

| Sumber Data | Status | Keterangan |
|---|---|---|
| **BMKG alerts** | ✅ **Real-time, data asli** | API publik, tidak butuh setup. 17 alert aktif hari ini |
| **Earth Engine** (DEM, flood hazard, populasi) | ⚠️ Sample data | Butuh EE authentication. Angka berdasarkan riset akademik |
| **Vulnerability score** | ⚠️ Dari sample data | Akurat secara formula, inputnya dari sample |
| **Narasi AI** | ⚠️ Template rules | Butuh GCP + Gemini. Sudah fungsional tapi tidak adaptif |
| **Frontend** | ⚠️ Mock hardcoded | `VITE_USE_MOCK=true` — tidak connect ke backend sama sekali |

### Yang perlu dilakukan untuk data real

```
BMKG → sudah real, tidak perlu setup apapun

Earth Engine:
  1. Daftar di https://code.earthengine.google.com/register
  2. Tunggu approval (1-2 hari)
  3. earthengine authenticate
  4. Set GCP_PROJECT_ID di .env + DEMO_MODE=false

Gemini:
  1. Install gcloud CLI
  2. gcloud auth application-default login
  3. Set GCP_PROJECT_ID di .env

Frontend → backend:
  1. Jalankan: uvicorn api.main:app --reload --port 8080
  2. Set VITE_USE_MOCK=false di frontend/.env.development
```

### Cara verifikasi BMKG sudah real

```powershell
cd sigap
.venv\Scripts\activate
python test_bmkg_live.py
# Output: daftar alert aktif hari ini langsung dari server BMKG
```

---

## Arsitektur Sistem

```
┌──────────────────────────────────────────────────────────────────┐
│                          DATA SOURCES                            │
│                                                                  │
│  BMKG Open API ────────────────────┐                             │
│  (✅ real-time, public, no key)    │                             │
│                                    ▼                             │
│  Google Earth Engine ─────────► pipeline/  ──► data/cache/      │
│  (⚠️  butuh auth)                 bmkg_ingest.py                 │
│  • SRTM DEM 30m                   ee_loader.py                   │
│  • JRC GloFAS Flood Hazard                                       │
│  • Global Flood Database 2000-18                                 │
│  • WorldPop 100m                                                 │
└────────────────────────────────────┬─────────────────────────────┘
                                     │
                                     ▼
┌──────────────────────────────────────────────────────────────────┐
│                           AI ENGINE                              │
│                                                                  │
│  BMKG alert + EE features                                        │
│       │                                                          │
│       ▼                                                          │
│  vulnerability.py ─────────────────────────► VulnerabilityResult │
│  Weighted scoring 5 komponen                        │            │
│  → skor 0-100, kategori, action plan                ▼            │
│                                             narrator.py          │
│                                             Gemini 1.5 Flash     │
│                                             (⚠️  butuh GCP auth) │
│                                             → Narasi Indonesia   │
└────────────────────────────────────┬─────────────────────────────┘
                                     │
                                     ▼
┌──────────────────────────────────────────────────────────────────┐
│                         SERVING LAYER                            │
│                                                                  │
│  api/main.py — FastAPI (localhost:8080)                          │
│       │                                                          │
│       ▼                                                          │
│  frontend/ — React + Vite (localhost:3000)                       │
│  • Peta Leaflet + flood zone overlay                             │
│  • Dashboard koordinator BPBD                                    │
│  • Dark/Light mode                                               │
└──────────────────────────────────────────────────────────────────┘
```

---

## Bagaimana AI Menghasilkan Kesimpulan

SIGAP menggunakan **dua lapisan** yang bekerja berurutan.

---

### Lapisan 1 — Vulnerability Scoring (Deterministic)

Bukan neural network. Ini **weighted multi-criteria scoring** — transparan dan dapat dijelaskan ke juri.

#### Formula

```
Vulnerability Score = Σ (komponen_i_normalized × bobot_i) × 100
```

#### 5 Komponen

| # | Komponen | Bobot | Sumber | Yang Diukur |
|---|---|---|---|---|
| 1 | **Flood Hazard** | 30% | JRC GloFAS (EE) | Proporsi area yang berpotensi terendam (10yr return period) |
| 2 | **Population Exposure** | 25% | WorldPop (EE) | Kepadatan penduduk di area banjir |
| 3 | **Vulnerable Population** | 25% | WorldPop + BPS nasional | Estimasi lansia 60+ dan balita 0-4 |
| 4 | **Historical Frequency** | 10% | Global Flood DB (EE) | Frekuensi banjir 2000-2018 |
| 5 | **Low Elevation Risk** | 10% | SRTM DEM (EE) | Proporsi area < 5m elevasi (rentan rob) |

#### Normalisasi ke 0–1

```python
hazard_score   = clamp(flood_ratio  / 0.80)    # 80% area banjir = skor penuh
exposure_score = clamp(density      / 15000)   # 15.000 jiwa/km² = skor penuh
vuln_score     = clamp(vuln_ratio   / 0.25)    # 25% populasi rentan = skor penuh
history_score  = clamp(hist_events  / 20)      # 20 events = skor penuh
elev_score     = clamp(low_elev_r   / 0.50)    # 50% area < 5m = skor penuh
```

#### Interpretasi

| Skor | Kategori | Tindakan |
|---|---|---|
| 0–25 | 🟢 RENDAH | Pantau berkala |
| 25–50 | 🟡 SEDANG | Siapkan kontingensi |
| 50–75 | 🟠 TINGGI | Aktifkan kesiapsiagaan |
| 75–100 | 🔴 KRITIS | Segera evakuasi |

#### Contoh perhitungan — Semarang

```
Flood ratio 34.8%  → hazard   = 0.348/0.80 = 0.435 → +13.1 poin
Density 4,424/km²  → exposure = 4424/15000 = 0.295 → +7.4 poin
Vuln ratio 17.6%   → vuln     = 0.176/0.25 = 0.704 → +17.6 poin
14 hist. events    → history  = 14/20      = 0.700 → +7.0 poin
Low elev ~45%      → elevation= 0.45/0.50  = 0.900 → +9.0 poin
                                            ──────────────────────
                                            TOTAL ≈ 54.1 → 🟠 TINGGI
```

---

### Lapisan 2 — Gemini AI Narasi (Generative)

Scoring menghasilkan angka. Koordinator BPBD butuh **bahasa**, bukan angka.

#### Alur Prompt ke Gemini

```
SYSTEM PROMPT:
  "Kamu adalah SIGAP AI untuk koordinator BPBD Indonesia.
   Fokus: APA yang akan terjadi, SIAPA yang berisiko,
   APA yang harus dilakukan SEKARANG. Maks 300 kata."

USER PROMPT (data aktual dari scoring):
  "Briefing untuk koordinator BPBD Kota Semarang.
   Risiko: 🟠 TINGGI (72.4/100)
   Populasi: 1,653,524 jiwa
   Rentan  : 291,021 jiwa (lansia + balita)
   Flood area: 34.8%
   Historis: 14 events (2000-2018)
   Elevasi min: -2.0m (sebagian di bawah laut)
   Faktor dominan: Flood Hazard +21.8, Pop. Rentan +17.5
   Rekomendasi sistem: [daftar action dari scorer]
   Format: 1 paragraf + 3-5 tindakan + 1 kalimat resource"

GEMINI OUTPUT:
  Narasi bahasa Indonesia, actionable, kontekstual
```

#### Parameter

```python
GenerationConfig(
    temperature=0.4,       # Faktual tapi tetap natural
    max_output_tokens=512  # Cukup untuk briefing ringkas
)
```

#### Fallback Template

Jika Gemini belum aktif, sistem pakai **template rules** deterministik:

```python
if score >= 75:
    intro = f"🚨 SITUASI KRITIS — {city}..."
elif score >= 50:
    intro = f"⚠️  WASPADA — {city}..."
elif score >= 25:
    intro = f"📋 SIAGA — {city}..."
```

Output template sudah informatif dan cukup untuk demo awal.

---

## Output yang Dihasilkan

### 1. Terminal (`run_poc.py`)

```
STEP 1 — BMKG Peringatan Dini Cuaca
  ✅ 17 alert aktif | 17 alert banjir
  Provinsi: Jawa Barat, Sumatera Barat, Kalimantan Barat...

STEP 2 — Earth Engine Geospatial Data
  ⚠️ SAMPLE DATA (EE belum auth)
  Elevasi: -2.0m – 348.0m (avg 18.4m)
  Flood ratio (10yr): 34.8%
  Historis: 14 events
  Populasi: 1,653,524 jiwa | Rentan: 291,021 jiwa

STEP 3 — Vulnerability Score
  ████████████████████░░░░░░░░░░░░  72.4/100
  🟠 TINGGI

STEP 4 — Narasi AI (Template Engine)
  ⚠️ WASPADA — Kota Semarang menunjukkan risiko banjir tinggi...
  TINDAKAN: 1. Aktifkan BPBD... 2. Siapkan evakuasi...
```

### 2. JSON (`data/poc_result_semarang.json`)

File lengkap semua data tiap step — dapat diaudit dan dipakai frontend.

### 3. REST API (`localhost:8080`)

Endpoint `/analyze/semarang` → JSON berisi alerts + score + narasi dalam satu response.

### 4. Dashboard (`localhost:3000`)

Peta interaktif + panel alert + gauge score + narasi AI dalam satu layar.

---

## Struktur Project

```
sigap/
├── pipeline/
│   ├── bmkg_ingest.py        # ✅ BMKG RSS + CAP parser, cache 30 menit
│   └── ee_loader.py          # ✅ Earth Engine: DEM, flood hazard, WorldPop
│
├── engine/
│   ├── vulnerability.py      # ✅ Weighted scoring 5 komponen (0-100)
│   └── narrator.py           # ✅ Gemini narasi + template fallback
│
├── api/
│   └── main.py               # ✅ FastAPI 7 endpoints
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx            # Layout + dark/light mode
│   │   ├── components/
│   │   │   ├── Header.jsx     # City selector + theme toggle
│   │   │   ├── MapView.jsx    # Leaflet + flood zones (Stadia/OSM tiles)
│   │   │   ├── AlertPanel.jsx # BMKG alerts
│   │   │   ├── VulnerabilityCard.jsx
│   │   │   └── NarasiPanel.jsx
│   │   ├── hooks/
│   │   │   └── useAnalysis.js # Fetching + auto-refresh 5 menit
│   │   └── lib/
│   │       ├── api.js         # HTTP calls + mock fallback
│   │       ├── mockData.js    # Hardcoded sample (aktif saat VITE_USE_MOCK=true)
│   │       └── ThemeContext.jsx
│   └── .env.development       # VITE_USE_MOCK=true (default)
│
├── data/
│   ├── cache/                 # Auto-generated: BMKG + EE cache
│   └── poc_result_{kota}.json # Auto-generated: output run_poc.py
│
├── test_bmkg_live.py          # ✅ Quick test BMKG real data
├── run_poc.py                 # ✅ Single entry point semua pipeline
├── requirements.txt
├── .env.example
└── README.md
```

---

## Setup & Cara Menjalankan

### Prasyarat

| Tools | Versi | Keterangan |
|---|---|---|
| Python | 3.10+ | Backend + pipeline |
| Node.js | 18+ | Frontend |
| gcloud CLI | Latest | Untuk Earth Engine + Gemini |

### 1. Setup Python

```powershell
cd d:\DEVelopment\hackathon-google-ai-builder\sigap

python -m venv .venv
.venv\Scripts\activate

pip install -r requirements.txt

Copy-Item .env.example .env
# Untuk awal: biarkan DEMO_MODE=true di .env
```

### 2. Test BMKG real (tidak butuh setup GCP)

```powershell
python test_bmkg_live.py
# Output: list alert aktif hari ini langsung dari BMKG
```

### 3. Jalankan full POC

```powershell
python run_poc.py semarang
# Atau: python run_poc.py bekasi / jakarta
```

### 4. Jalankan backend API

```powershell
uvicorn api.main:app --reload --port 8080
# Buka: http://localhost:8080/docs
```

### 5. Jalankan frontend

```powershell
cd frontend
npm install    # Sekali saja
npm run dev    # http://localhost:3000
```

Default: `VITE_USE_MOCK=true` — tidak butuh backend.

Untuk connect ke backend:
```
# frontend/.env.development
VITE_USE_MOCK=false
```

---

## Setup Google Cloud (untuk data real)

### Step 1 — Install gcloud CLI

Download: https://cloud.google.com/sdk/docs/install-sdk#windows

```powershell
gcloud auth login
gcloud projects create sigap-hackathon-2026
gcloud config set project sigap-hackathon-2026
gcloud services enable earthengine.googleapis.com
gcloud services enable aiplatform.googleapis.com
```

### Step 2 — Daftar Earth Engine (lakukan sekarang, butuh 1-2 hari)

1. Buka: https://code.earthengine.google.com/register
2. Pilih: **Noncommercial → Unpaid usage → sigap-hackathon-2026**
3. Tunggu email approval

Setelah approved:
```powershell
pip install earthengine-api
earthengine authenticate    # Buka browser → login
```

### Step 3 — Aktifkan Gemini

```powershell
gcloud auth application-default login
```

### Step 4 — Update `.env`

```ini
GCP_PROJECT_ID=sigap-hackathon-2026
EE_PROJECT=sigap-hackathon-2026
DEMO_MODE=false
```

Jalankan ulang `python run_poc.py semarang` → data dari Earth Engine + narasi dari Gemini.

---

## Data Sources

Semua data publik dan gratis.

| Data | Sumber | Endpoint / Dataset ID | Status |
|---|---|---|---|
| Peringatan dini cuaca | BMKG Open Data | `bmkg.go.id/alerts/nowcast/id` | ✅ Langsung tersedia |
| DEM (elevasi) | SRTM 30m | `USGS/SRTMGL1_003` (Earth Engine) | ⚠️ Butuh EE auth |
| Flood hazard map | JRC/Copernicus GloFAS | `JRC/CEMS_GLOFAS_FloodHazard_v2_1` | ⚠️ Butuh EE auth |
| Historical floods | Global Flood Database | `GLOBAL_FLOOD_DB/MODIS_EVENTS/V1` | ⚠️ Butuh EE auth |
| Populasi | WorldPop 100m | `WorldPop/GP/100m/pop` | ⚠️ Butuh EE auth |
| Proporsi usia rentan | BPS SP2020 (embedded) | Embedded di kode sebagai konstanta | ✅ Tersedia |

---

## Status Implementasi

| Komponen | Status | Catatan |
|---|---|---|
| BMKG pipeline | ✅ Selesai, data real | Real-time, cache 30 menit, terbukti 17 alert hari ini |
| Earth Engine loader | ✅ Kode selesai | Data pakai sample karena EE auth belum ada |
| Vulnerability scorer | ✅ Selesai | Formula berjalan, input dari sample data |
| Gemini narrator | ✅ Kode selesai | Pakai template fallback, Gemini butuh GCP auth |
| FastAPI backend | ✅ Selesai | 7 endpoints, belum pernah dijalankan live |
| Frontend dashboard | ✅ Selesai | `VITE_USE_MOCK=true` — semua dari mock |
| POC runner | ✅ Selesai | `python run_poc.py semarang` jalan dengan DEMO_MODE=true |
| `.env` dibuat | ❌ Belum | Masih `.env.example`, perlu `Copy-Item .env.example .env` |
| gcloud CLI | ❌ Belum install | Download dari cloud.google.com/sdk |
| GCP Project | ❌ Belum dibuat | Butuh gcloud CLI dulu |
| Earth Engine auth | ❌ Belum | Daftar dulu, tunggu approval 1-2 hari |
| Gemini auth | ❌ Belum | Butuh GCP project + gcloud auth |
| Frontend → Backend | ❌ Belum connect | Ganti `VITE_USE_MOCK=false` + jalankan backend |
| Cloud Run deploy | 🔲 Planned | Post-hackathon |
| Resource optimizer | 🔲 Planned | Algoritma deployment resource |

---

## Tim & Pembagian Kerja

| Role | Tanggung Jawab |
|---|---|
| **Data Scientist** | `pipeline/` — data ingestion. `engine/` — scoring + Gemini prompt. `run_poc.py` |
| **Backend** | `api/main.py` — jalankan FastAPI, integrasi pipeline, deploy Cloud Run |
| **Frontend** | `frontend/` — React dashboard, connect ke backend, polish UI |

---

*Terakhir diupdate: September 2026*
*BMKG data verified live: 17 alert aktif, 24 September 2026*
