# SIGAP — Sistem Integrasi Geospasial Aksi Penanggulangan Bencana

> **AI-powered Flood Response Decision Engine** untuk koordinator BPBD Indonesia
>
> SIGAP bukan sistem prediksi banjir. SIGAP mengambil data dari BMKG dan InaRisk BNPB,
> lalu menjawab pertanyaan yang selama ini tidak terjawab:
> **siapa evakuasi duluan, berapa perahu dibutuhkan, dan apa yang harus dilakukan sekarang.**

---

## Daftar Isi

- [Latar Belakang](#latar-belakang)
- [Cara Kerja](#cara-kerja)
- [Arsitektur](#arsitektur)
- [Data Sources](#data-sources)
- [Vulnerability Score](#vulnerability-score)
- [Setup & Menjalankan](#setup--menjalankan)
- [API Endpoints](#api-endpoints)
- [Struktur Project](#struktur-project)
- [Status Komponen](#status-komponen)

---

## Latar Belakang

Indonesia mencatat **3.472 kejadian bencana** (2024), 99% hidrometeorologis.
**5,7 juta jiwa** terdampak banjir setiap tahun. Budget BNPB turun 97% sejak 2020.

Masalah bukan prediksi — BMKG sudah punya sistem peringatan dini yang baik.
Masalahnya adalah **jeda antara peringatan dan tindakan**. Koordinator BPBD masih
mengkoordinasikan evakuasi lewat telepon manual, mengirim resource berdasarkan intuisi,
dan tidak tahu siapa yang paling rentan di zona banjir.

SIGAP mengisi jeda itu dengan mengintegrasikan tiga sumber data menjadi satu keputusan.

---

## Cara Kerja

```
BMKG Alert Severe masuk
        ↓
Score Semarang: 49 → 64 (SIAGA) — otomatis dalam 30 detik
        ↓
Petugas lapangan submit laporan TMA Banjirkanal: Siaga
        ↓
Score: 64 → 79 (AWAS) — langsung
        ↓
Gemini AI: "Evakuasi 8.500 jiwa dari Tawangmas, deploy 12 perahu ke Semarang Utara"
        ↓
Koordinator BPBD baca, klik, eksekusi.
```

Total waktu dari data masuk ke keputusan: **< 60 detik**.

---

## Arsitektur

```
┌─────────────────────────────────────────────────────────┐
│                     DATA SOURCES                        │
│                                                         │
│  BMKG Nowcast API ────────── ✅ Real-time, no auth      │
│  BMKG Prakiraan Cuaca ──────── ✅ Real-time, no auth    │
│  InaRisk BNPB GIS ─────────── ✅ Live, no auth         │
│    • INDEKS_BAHAYA_BANJIR                               │
│    • layer_risiko_banjir (BNPB final composite)         │
│    • INARISKPOP_2020                                    │
│    • batas_administrasi (polygon kecamatan)             │
│  Kemendagri Wilayah ────────── 📋 90k+ kode wilayah    │
│  Google Earth Engine ────────── ⚠️ Fallback only       │
└──────────────────┬──────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────┐
│                    SIGAP ENGINE                         │
│                                                         │
│  vulnerability.py ── Weighted score 0-100               │
│    base (InaRisk statis)                                │
│    + weather_boost (0-25, BMKG real-time)               │
│    + alert_boost   (0-25, BMKG real-time)               │
│    + field_boost   (0-30, laporan BPBD)                 │
│                                                         │
│  scoring.py ──── Orkestrasi semua komponen              │
│  narrator.py ─── Gemini AI → narasi bahasa Indonesia    │
│  baseline.py ─── InaRisk cache management (7 hari)     │
│  wilayah.py ──── Katalog 90k+ kode wilayah Indonesia   │
└──────────────────┬──────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────┐
│                  SERVING LAYER                          │
│                                                         │
│  FastAPI v0.4.0 — localhost:8080 (16 endpoints)         │
│  React + Vite — localhost:3000                          │
│    • Peta OpenStreetMap + polygon kecamatan InaRisk     │
│    • Vulnerability score per kecamatan (klik polygon)   │
│    • Form laporan lapangan desa/kelurahan               │
│    • Search 514+ kab/kota Indonesia                     │
│                                                         │
│  PostgreSQL 16 (Docker Compose) — port 5432             │
│    • wilayah + wilayah_profil (katalog Kemendagri)      │
│    • flood_reports (laporan lapangan BPBD)              │
│    • inarisk_baselines (cache InaRisk 7 hari)           │
│    • weather_cache (cache BMKG 6 jam)                   │
└─────────────────────────────────────────────────────────┘
```

---

## Data Sources

### Live / Real-time

| Data | Sumber | Endpoint | Cache |
|---|---|---|---|
| Alert cuaca | BMKG Nowcast CAP/XML | `bmkg.go.id/alerts/nowcast/id` | 30 menit |
| Prakiraan cuaca 12 jam | BMKG Prakiraan | `api.bmkg.go.id/publik/prakiraan-cuaca` | 6 jam |
| Indeks Bahaya Banjir | InaRisk BNPB | `gis.bnpb.go.id/server/rest/services/inarisk` | 7 hari (Postgres) |
| Indeks Risiko Banjir | InaRisk BNPB | `layer_risiko_banjir` | 7 hari |
| Polygon kecamatan | InaRisk BNPB | `batas_administrasi/MapServer/3` | 7 hari |
| Narasi AI | Gemini AI Studio (gratis) | Google AI Studio API | Per-request |

### Referensi / Embedded

| Data | Sumber | Keterangan |
|---|---|---|
| 90k+ kode wilayah | Kemendagri | `knowledge/geografi/wilayah.sql` — provinsi, kab/kota, kecamatan, desa |
| Pusat & bbox wilayah | Wilayah Geo | `knowledge/geografi/wilayah_level_1_2.sql` |
| Data populasi | BPS Sensus 2020 | Fallback jika InaRisk INARISKPOP timeout |
| Kejadian historis | BNPB DIBI 2000-2018 | Hardcoded per kota |
| Elevasi | SRTM | Hardcoded per kota |

> **Tidak perlu API key untuk InaRisk atau BMKG.** Semua data publik dari lembaga pemerintah.

---

## Vulnerability Score

Skor 0–100 dihitung dari **5 komponen statis + 3 boost real-time**:

### Komponen Statis (Base Score)

| Komponen | Bobot | Sumber | Normalisasi |
|---|---|---|---|
| Flood Hazard | 30% | InaRisk INDEKS_BAHAYA_BANJIR | 80% area = skor penuh |
| Pop. Exposure | 25% | InaRisk INARISKPOP_2020 | 15.000 jiwa/km² = penuh |
| Pop. Rentan | 25% | BPS: lansia 9.6% + balita 8.0% | 25% rentan = penuh |
| Historis Banjir | 10% | BNPB DIBI 2000-2018 | 20 events = penuh |
| Low Elevation | 10% | SRTM DEM | 50% area < 5m = penuh |

### Boost Real-time

| Boost | Sumber | Max | Trigger |
|---|---|---|---|
| Weather | BMKG prakiraan cuaca | +25 | > 100mm/12jam = +25, > 50mm = +15, > 20mm = +8 |
| Alert | BMKG Nowcast severity | +25 | Extreme = +25, Severe = +15, Moderate = +8 |
| Lapangan | Laporan BPBD (desa) | +30 | TMA Awas = +25, Siaga = +15, Waspada = +8 |

> Total boost maksimum: **+30 poin** (di-cap agar tidak overflow).

### Kategori (Peraturan BNPB No. 2 Tahun 2024)

| Skor | Level | Warna | Tindakan |
|---|---|---|---|
| 0–25 | 🟢 NORMAL | Hijau | Pantau berkala |
| 25–50 | 🟡 WASPADA | Kuning | Siapkan rencana kontingensi |
| 50–75 | 🟠 SIAGA | Oranye | Aktifkan kesiapsiagaan |
| 75–100 | 🔴 AWAS | Merah | Evakuasi segera |

### Vulnerability Map per Kecamatan

`GET /vulnerability-map/{city}` menghitung skor per kecamatan:
- Komponen non-hazard (exposure, vulnerable, history, elevation) = dari city score
- Komponen hazard = nilai InaRisk spesifik kecamatan tersebut
- Boost cuaca + alert = berlaku sama untuk semua kecamatan dalam satu kota

Hasil: setiap kecamatan punya skor unik berdasarkan risiko lokal.
Klik polygon di peta → lihat detail score, populasi estimasi, kategori.

---

## Setup & Menjalankan

### Prasyarat

| Tools | Versi | Install |
|---|---|---|
| Python | 3.10+ | [python.org](https://python.org) atau `brew install python@3.11` |
| Node.js | 18+ | [nodejs.org](https://nodejs.org) atau `brew install node` |
| Docker | any | [docker.com](https://docker.com) — untuk PostgreSQL |

---

### 🍎 Mac / Linux

```bash
# 1. Clone
git clone https://github.com/bimaramadhan/sigap.git
cd sigap

# 2. Python environment
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 3. Konfigurasi
cp .env.example .env
# Edit .env: isi GEMINI_API_KEY dari aistudio.google.com
# .env.example sudah SKIP_DB=true → langsung jalan tanpa database

# 4. Jalankan backend (terminal 1)
uvicorn api.main:app --reload --port 8080

# 5. Jalankan frontend (terminal 2)
cd frontend
npm install
npm run dev
```

> **Tanpa database?** Default `SKIP_DB=true` → backend pakai file cache,
> tidak butuh Docker/Postgres. Cocok untuk demo. Lihat bagian
> [Pilihan Database](#pilihan-database) untuk mengaktifkan Postgres.

> **Apple Silicon (M1/M2/M3)?** Package geospatial sudah punya binary wheel untuk arm64.
> Kalau ada error saat install: `brew install gdal proj geos` lalu ulangi `pip install`.

---

### 🪟 Windows (PowerShell)

```powershell
# 1. Clone
git clone https://github.com/bimaramadhan/sigap.git
cd sigap

# 2. Python environment
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

# 3. Konfigurasi
Copy-Item .env.example .env
notepad .env   # isi GEMINI_API_KEY (SKIP_DB sudah true by default)

# 4. Backend (terminal 1)
uvicorn api.main:app --reload --port 8080

# 5. Frontend (terminal baru)
cd frontend
npm install
npm run dev
```

---

### Setup Gemini API Key (wajib untuk narasi AI)

1. Buka [aistudio.google.com](https://aistudio.google.com) → Login
2. Klik **"Get API Key"** → **"Create API key"**
3. Copy key, paste ke `.env`:
   ```
   GEMINI_API_KEY=AQ...
   GEMINI_MODEL=gemini-3.5-flash
   ```
4. Restart backend — narasi berubah dari *"Template Engine"* ke *"Gemini AI Studio (Free)"*

**Free tier:** 15 req/menit, 1 juta token/hari — lebih dari cukup untuk demo.

---

### Environment Variables (`.env`)

| Variable | Wajib | Default | Keterangan |
|---|---|---|---|
| `GEMINI_API_KEY` | ✅ untuk AI | — | Dari [aistudio.google.com](https://aistudio.google.com) |
| `GEMINI_MODEL` | ✅ untuk AI | `gemini-3.5-flash` | Model Gemini yang digunakan |
| `SKIP_DB` | — | `true` | `true` = file cache (tanpa Postgres); `false` = pakai Postgres |
| `DATABASE_URL` | ⚠️ jika `SKIP_DB=false` | `postgresql://sigap:sigap@localhost:5432/sigap` | Postgres connection string |
| `DEMO_MODE` | — | `false` | `true` = skip Gemini + EE, pakai template |
| `REFRESH_TOKEN` | — | — | Token untuk Cloud Scheduler endpoint |
| `GCP_PROJECT_ID` | — | — | Hanya jika pakai Vertex AI (berbayar) |
| `CACHE_DIR` | — | `data/cache` | Direktori cache file |

---

### Pilihan Database

SIGAP bisa jalan dengan atau tanpa database.

#### Opsi A — Tanpa Database (default, paling mudah)

Set `SKIP_DB=true` di `.env` (sudah default di `.env.example`). Backend pakai
file cache di `data/cache/` dan laporan tersimpan di `data/flood_reports.json`.
**Tidak butuh Docker atau Postgres.** Cocok untuk demo & development.

#### Opsi B — PostgreSQL via Docker

```bash
docker compose up -d        # Postgres 16, kredensial sigap/sigap
# set SKIP_DB=false di .env
uvicorn api.main:app --reload --port 8080
```

#### Opsi C — PostgreSQL install langsung (tanpa Docker)

1. Download [PostgreSQL 16](https://www.enterprisedb.com/downloads/postgres-postgresql-downloads)
2. Saat install: set port `5432`, catat password user `postgres`
3. Buat database & user lewat **SQL Shell (psql)**:
   ```sql
   CREATE USER sigap WITH PASSWORD 'sigap';
   CREATE DATABASE sigap OWNER sigap;
   GRANT ALL PRIVILEGES ON DATABASE sigap TO sigap;
   ```
4. Set `SKIP_DB=false` di `.env`
5. Jalankan backend — tabel + 90k kode wilayah ter-seed otomatis saat pertama

> Beralih antara opsi cukup dengan ubah `SKIP_DB` di `.env` lalu restart backend.
> Data laporan di JSON otomatis diimport ke Postgres saat pertama kali DB tersedia.

---

### Test Pipeline

```bash
# Test BMKG real-time (tidak butuh setup apapun)
python test_bmkg_live.py

# Test InaRisk BNPB
python test_inarisk_integration.py

# Test weather boost
python test_weather_integration.py

# Full POC satu kota
python run_poc.py semarang
```

---

## API Endpoints

Backend berjalan di `http://localhost:8080`. Dokumentasi interaktif di `/docs`.

### System

| Method | Endpoint | Keterangan |
|---|---|---|
| `GET` | `/` | Health check, versi, demo_mode |
| `GET` | `/cities?q={query}` | Semua kab/kota dari katalog Kemendagri |
| `GET` | `/cities/search?q={query}` | Cari kab/kota (min 2 karakter), limit 1-50 |
| `GET` | `/cities/{kode}` | Satu kab/kota + bbox |
| `POST` | `/internal/refresh-baselines` | Refresh InaRisk stale (Cloud Scheduler) |

### Data (real-time)

| Method | Endpoint | Cache | Keterangan |
|---|---|---|---|
| `GET` | `/alerts?city={kode}` | 30 menit | BMKG alert aktif, filter per provinsi kota |
| `GET` | `/weather/{city}` | 6 jam | BMKG prakiraan 12 jam + boost score |
| `GET` | `/features/{city}` | 7 hari (DB) | Raw InaRisk features (fallback EE) |

### Analysis (AI)

| Method | Endpoint | Keterangan |
|---|---|---|
| `GET` | `/vulnerability/{city}` | Score 0-100 + breakdown 7 komponen |
| `GET` | `/narasi/{city}` | Narasi Gemini AI bahasa Indonesia |
| `GET` | `/analyze/{city}` | **Full pipeline** — endpoint utama frontend |

### Field Reports (laporan lapangan BPBD)

| Method | Endpoint | Keterangan |
|---|---|---|
| `POST` | `/flood-report` | Submit laporan per desa, boost score langsung |
| `GET` | `/flood-reports/{city}` | Laporan 12 jam terakhir + boost aktif |
| `GET` | `/flood-villages/{city}` | Desa/kelurahan grouped per kecamatan |
| `DELETE` | `/flood-reports/{city}` | Reset laporan (untuk demo ulang) |

### Map Data

| Method | Endpoint | Cache | Keterangan |
|---|---|---|---|
| `GET` | `/flood-polygons/{city}` | 7 hari | GeoJSON kecamatan + hazard index |
| `GET` | `/vulnerability-map/{city}` | 10 menit | GeoJSON + vuln_score per kecamatan |

---

## Struktur Project

```
sigap/
├── api/
│   └── main.py               # FastAPI v0.4.0, 16 endpoints, lifespan DB init
│
├── engine/
│   ├── vulnerability.py      # Core 0-100 scoring (5 statis + 2 dynamic boost)
│   ├── scoring.py            # Orkestrasi: baseline + weather + alerts + field
│   ├── narrator.py           # Gemini AI narasi (AI Studio → Vertex → template)
│   ├── baseline.py           # InaRisk cache management, 7 hari TTL (Postgres)
│   ├── flood_report.py       # CRUD laporan lapangan, 12 jam window (Postgres)
│   ├── db.py                 # psycopg3 data access, schema init, seeding
│   ├── places.py             # Bbox resolution (wilayah_geo → hardcoded → InaRisk)
│   ├── wilayah.py            # Katalog 90k+ kode wilayah (Kemendagri)
│   └── wilayah_geo.py        # Profil spasial: center, bbox, elevasi per wilayah
│
├── pipeline/
│   ├── bmkg_ingest.py        # BMKG alert CAP/XML, 30 menit cache
│   ├── bmkg_weather.py       # BMKG prakiraan 12 jam per kecamatan, 6 jam cache
│   ├── inarisk_loader.py     # InaRisk geospatial grid sampling, 7 hari cache
│   ├── inarisk_polygon.py    # InaRisk kecamatan polygons + hazard, 7 hari cache
│   ├── city_registry.py      # Legacy utility: InaRisk kab/kota registry
│   └── ee_loader.py          # Google Earth Engine (fallback terakhir)
│
├── frontend/
│   ├── package.json          # React + Vite + Leaflet (Tailwind 3.4.12, Vite 5.4.8)
│   └── src/
│       ├── App.jsx           # Layout utama: sidebar, tabs, city state
│       ├── components/
│       │   ├── Header.jsx           # Search 514 kota, nav tabs, theme toggle
│       │   ├── WeatherBar.jsx       # Strip cuaca + rainfall BMKG
│       │   ├── AlertPanel.jsx       # BMKG alerts dengan severity badge
│       │   ├── VulnerabilityCard.jsx # Arc gauge + breakdown bars
│       │   ├── NarasiPanel.jsx      # AI narasi + priority actions + resources
│       │   ├── MapView.jsx          # Leaflet + InaRisk polygon + KecamatanPanel
│       │   ├── FloodInputPanel.jsx  # Form laporan lapangan per desa
│       │   ├── FloodReportPanel.jsx # Panel laporan + riwayat
│       │   ├── ReportPage.jsx       # Halaman laporan penuh (/report)
│       │   ├── GoogleAuthModal.jsx  # Modal login Google (GSI)
│       │   └── GoogleIcon.jsx       # Ikon Google
│       ├── hooks/
│       │   ├── useAnalysis.js       # Fetch /analyze/{city}, auto-refresh 5 menit
│       │   └── useFloodReports.js
│       └── lib/
│           ├── api.js               # Semua HTTP calls ke backend
│           ├── mockData.js          # Fallback mock data
│           ├── AuthContext.jsx      # State login Google (frontend)
│           └── ThemeContext.jsx     # Dark/light mode
│
├── db/
│   └── schema.sql            # 5 tabel Postgres: wilayah, profil, reports, baselines, weather
│
├── knowledge/
│   ├── geografi/
│   │   ├── wilayah.sql             # 90k+ kode wilayah Kemendagri
│   │   └── wilayah_level_1_2.sql   # Profil spasial prov + kab/kota
│   └── sop/
│       ├── status_keadaan_darurat_bnpb.md   # Pedoman BNPB 2016
│       ├── sistem_peringatan_dini_bnpb_2024.md  # Perka BNPB No.2/2024
│       └── rambu_papan_informasi_bnpb_2025.md   # Perka BNPB No.3/2025
│
├── data/
│   ├── cache/                # File cache: weather_*.json, bmkg_*.json, *.geojson
│   └── flood_reports.json    # Legacy — diimport ke Postgres saat startup pertama
│
├── docker-compose.yml        # PostgreSQL 16, kredensial sigap/sigap, port 5432
├── requirements.txt
├── .env.example
└── run_poc.py
```

---

## Status Komponen

### Backend

| Komponen | File | Status |
|---|---|---|
| API server | `api/main.py` | ✅ v0.4.0, 16 endpoints |
| Vulnerability scorer | `engine/vulnerability.py` | ✅ 5 statis + 2 dynamic |
| Score orchestration | `engine/scoring.py` | ✅ baseline + weather + alerts + field |
| Gemini narrator | `engine/narrator.py` | ✅ AI Studio (free) → Vertex → template |
| InaRisk cache (DB) | `engine/baseline.py` | ✅ Postgres, 7 hari TTL |
| Flood reports (DB) | `engine/flood_report.py` | ✅ Postgres, 12 jam window |
| Database layer | `engine/db.py` | ✅ psycopg3, auto-init + seeding |
| Wilayah catalog | `engine/wilayah.py` | ✅ 90k+ kode Kemendagri |
| Wilayah spatial | `engine/wilayah_geo.py` | ✅ bbox, center, elevasi |
| Bbox resolution | `engine/places.py` | ✅ 3-tier fallback |
| BMKG alerts | `pipeline/bmkg_ingest.py` | ✅ Real-time CAP/XML |
| BMKG weather | `pipeline/bmkg_weather.py` | ✅ Real-time prakiraan 12 jam |
| InaRisk features | `pipeline/inarisk_loader.py` | ✅ Live grid sampling |
| InaRisk polygons | `pipeline/inarisk_polygon.py` | ✅ Kecamatan boundaries |

### Frontend

| Komponen | File | Status |
|---|---|---|
| Layout + routing (Dashboard / Report page) | `App.jsx` | ✅ Dua halaman: `/` dan `/report` |
| City search 514 kab/kota | `Header.jsx` | ✅ Searchable dropdown + nav tabs |
| Weather strip | `WeatherBar.jsx` | ✅ |
| BMKG alerts | `AlertPanel.jsx` | ✅ Per-provinsi filter |
| Score gauge | `VulnerabilityCard.jsx` | ✅ Arc gauge + 7 komponen |
| AI briefing | `NarasiPanel.jsx` | ✅ |
| Peta interaktif | `MapView.jsx` | ✅ Fit-bounds dinamis + klik polygon → KecamatanPanel |
| Laporan lapangan (input) | `FloodInputPanel.jsx` | ✅ Searchable desa/kelurahan |
| Laporan lapangan (panel + riwayat) | `FloodReportPanel.jsx` | ✅ |
| Halaman laporan penuh | `ReportPage.jsx` | ✅ Terpisah dari dashboard |
| Login Google (frontend) | `AuthContext.jsx`, `GoogleAuthModal.jsx` | ⚠️ GSI, belum verifikasi backend |

### Infrastructure

| Komponen | Status |
|---|---|
| PostgreSQL (Docker) | ✅ `docker compose up -d` |
| PostgreSQL (install langsung) | ✅ Alternatif tanpa Docker — lihat Setup |
| Mode tanpa DB (`SKIP_DB=true`) | ✅ File cache, demo tanpa Postgres |
| Google AI Studio (gratis) | ✅ `GEMINI_API_KEY` di `.env` |
| Vertex AI | ⚠️ Opsional, butuh GCP billing |
| Google Earth Engine | ⚠️ Fallback terakhir, butuh GEE auth |
| Auth di API backend | ❌ Belum — semua endpoint terbuka |
| Deploy publik | ❌ Belum — belum ada manifest Vercel/Cloud Run |

---

## Apa yang Sudah vs Belum

**✅ Sudah jalan (inti sistem):**
- Data real-time: BMKG alert + prakiraan cuaca, InaRisk BNPB 6 layer
- Vulnerability score dinamis: base + weather boost + alert boost + field report boost
- Peta polygon kecamatan dengan score per kecamatan (514 kab/kota)
- Narasi AI Gemini (gratis, `gemini-3.5-flash`)
- Form laporan lapangan BPBD → naikkan skor real-time
- Database Postgres + mode fallback tanpa DB

**⚠️ Sebagian:**
- **Knowledge base**: dokumen SOP/kota sudah ditulis di `knowledge/`, TAPI belum
  dibaca Gemini (narasi masih dari angka saja — lihat ROADMAP prioritas #1)
- **Login Google**: hanya di frontend, API backend belum verifikasi token
- **Knowledge kota**: baru Semarang, 3 kota lain belum

**🔲 Belum:**
- Integrasi knowledge base ke prompt Gemini (RAG) — **prioritas tertinggi berikutnya**
- Deploy publik (Vercel + Cloud Run/Railway)
- Kalibrasi threshold dari data historis
- PetaBencana.id crowdsourced, AWLR sensor sungai

> Detail lengkap + urutan prioritas ada di [ROADMAP.md](ROADMAP.md).

---

## Tim

| Role | Tanggung Jawab |
|---|---|
| Data Scientist | Pipeline BMKG/InaRisk, vulnerability scorer, Gemini prompt engineering |
| Backend | FastAPI endpoints, DB schema, wilayah catalog, Docker |
| Frontend | React dashboard, peta Leaflet, UI/UX |

---

*Terakhir diupdate: Oktober 2026 — v0.4.0*

**Data yang terbukti berjalan:**
- BMKG: 17 alert aktif, real-time tanpa setup
- InaRisk Semarang: flood_ratio=46.4%, inarisk_score=0.628
- InaRisk Jakarta: 82 kecamatan polygon, flood_ratio=49.7%
- Gemini AI Studio: narasi bahasa Indonesia dengan `gemini-3.5-flash`
- Postgres: 90k+ kode wilayah Kemendagri, flood reports, baseline cache
