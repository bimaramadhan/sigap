# SIGAP — Geospatial Integration System for Disaster Response Action

> **AI-powered Flood Response Decision Engine** for Indonesian BPBD coordinators
>
> SIGAP is not a flood prediction system. SIGAP fetches data from BMKG and InaRisk BNPB,
> and then answers the questions that have gone unanswered until now:
> **who to evacuate first, how many boats are needed, and what needs to be done right now.**

---

## Table of Contents

- [Background](#background)
- [How It Works](#how-it-works)
- [Architecture](#architecture)
- [Data Sources](#data-sources)
- [Vulnerability Score](#vulnerability-score)
- [Setup & Running](#setup--running)
- [Deployment to Google Cloud (Cloud Run)](DEPLOYMENT.md)
- [API Endpoints](#api-endpoints)
- [Project Structure](#project-structure)
- [Component Status](#component-status)

---

## Background

Indonesia recorded **3,472 disaster events** (2024), 99% of which were hydrometeorological.
**5.7 million people** are affected by floods every year. The BNPB budget has decreased by 97% since 2020.

The problem is not prediction — BMKG already has a reliable early warning system.
The problem is the **gap between warning and action**. BPBD coordinators are still
coordinating evacuations via manual phone calls, dispatching resources based on intuition,
and do not know who is most vulnerable within flood zones.

SIGAP fills that gap by integrating three data sources into a single decision engine.

---

## How It Works

```
BMKG Severe Alert received
        ↓
Semarang Score: 49 → 64 (ADVISORY) — automatic within 30 seconds
        ↓
Field officer submits TMA Banjirkanal report: Advisory
        ↓
Score: 64 → 79 (WARNING) — instantaneous
        ↓
Gemini AI: "Evacuate 8,500 people from Tawangmas, deploy 12 boats to North Semarang"
        ↓
BPBD Coordinator reads, clicks, executes.
```

Total time from data intake to decision: **< 60 seconds**.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     DATA SOURCES                        │
│                                                         │
│  BMKG Nowcast API ────────── ✅ Real-time, no auth      │
│  BMKG Weather Forecast ───── ✅ Real-time, no auth      │
│  InaRisk BNPB GIS ─────────── ✅ Live, no auth          │
│    • INDEKS_BAHAYA_BANJIR                               │
│    • layer_risiko_banjir (BNPB final composite)         │
│    • INARISKPOP_2020                                    │
│    • batas_administrasi (subdistrict polygon)           │
│  Kemendagri Region Catalog ── 📋 90k+ region codes      │
│  Google Earth Engine ────────── ⚠️ Fallback only        │
└──────────────────┬──────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────┐
│                     SIGAP ENGINE                        │
│                                                         │
│  risk_model.py ── 3-layer risk model (0-100)            │
│    L1 Structural: Hazard×Vuln÷Capacity (UNDRR/InaRisk)  │
│    L2 Trigger   : weather+alert+field report multiplier │
│    L3 Momentum  : Δscore/hr from history (trend)        │
│                                                         │
│  vulnerability.py ── Score components + BMKG boost      │
│  scoring.py ──── 3-layer orchestration + field report   │
│  score_history.py ─ Score history for momentum          │
│  narrator.py ─── Gemini AI → narrative (profile + SOP)  │
│  baseline.py ─── InaRisk cache management (7 days)      │
│  wilayah.py ──── Catalog of 90k+ region codes           │
└──────────────────┬──────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────┐
│                     SERVING LAYER                       │
│                                                         │
│  FastAPI v0.4.0 — localhost:8080 (16 endpoints)         │
│  React + Vite — localhost:3000                          │
│    • OpenStreetMap + InaRisk subdistrict polygon        │
│    • Vulnerability score per subdistrict (click polygon)│
│    • Village field report submission form               │
│    • Search 514+ regencies/cities in Indonesia          │
│                                                         │
│  PostgreSQL 16 (Docker Compose) — port 5432             │
│    • region + region_profile (Kemendagri catalog)       │
│    • flood_reports (BPBD field reports)                 │
│    • inarisk_baselines (7-day InaRisk cache)            │
│    • weather_cache (6-hour BMKG cache)                  │
└─────────────────────────────────────────────────────────┘
```

---

## Data Sources

### Live / Real-time

| Data | Source | Endpoint | Cache |
|---|---|---|---|
| Weather alert | BMKG Nowcast CAP/XML | `bmkg.go.id/alerts/nowcast/id` | 30 minutes |
| 12-hour weather forecast | BMKG Forecast | `api.bmkg.go.id/publik/prakiraan-cuaca` | 6 hours |
| Flood Hazard Index | InaRisk BNPB | `gis.bnpb.go.id/server/rest/services/inarisk` | 7 days (Postgres) |
| Flood Risk Index | InaRisk BNPB | `layer_risiko_banjir` | 7 days |
| Subdistrict polygon | InaRisk BNPB | `batas_administrasi/MapServer/3` | 7 days |
| AI Narrative | Gemini AI Studio (free) | Google AI Studio API | Per-request |

### Reference / Embedded

| Data | Source | Notes |
|---|---|---|
| 90k+ region codes | Kemendagri | `knowledge/geografi/wilayah.sql` — province, regency/city, subdistrict, village |
| Region center & bbox | Geo Region | `knowledge/geografi/wilayah_level_1_2.sql` |
| Population data | BPS 2020 Census | Fallback if InaRisk INARISKPOP times out |
| Historical events | BNPB DIBI 2000-2018 | Hardcoded per city |
| Elevation | SRTM | Hardcoded per city |

> **No API key needed for InaRisk or BMKG.** All data is publicly accessible from government institutions.

---

## Vulnerability Score

SIGAP utilizes a **3-layer risk model** anchored in the disaster risk framework of the
**UNDRR** (United Nations Office for Disaster Risk Reduction) — the same framework utilized by InaRisk BNPB. The weights are internationally recognized standard values.

```
SCORE = Structural Risk (Layer 1)  ×  Trigger Multiplier (Layer 2)
                                  +  Momentum Context (Layer 3)
```

Implementation: `engine/risk_model.py` + `engine/score_history.py`.

---

### Layer 1 — Structural Risk (fundamental regional vulnerability)

Official UNDRR formula:

```
Risk = (Hazard × Vulnerability) / Capacity
```

| Factor | Composition | Source |
|---|---|---|
| **Hazard** | 55% flood hazard + 30% population exposure + 15% low elevation | InaRisk INDEKS_BAHAYA_BANJIR, INARISKPOP, SRTM |
| **Vulnerability** | 70% vulnerable population (elderly+toddlers) + 30% historical record | InaRisk + BPS + BNPB DIBI |
| **Capacity** | Regional response & mitigation capability (acts as **divisor**) | InaRisk INDEKS_KAPASITAS_2021 |

**Why Capacity as a divisor?** Two cities facing identical hazards but differing in BPBD capacity or infrastructure will bear different risks. A city with robust capacity will see its score **decreased**. This is an insight that standard additive models fail to capture.

Results are normalized to 0–100 (using a root curve for fair distribution, preventing artificial clustering at the lower end).

---

### Layer 2 — Dynamic Trigger (how active the threat is TODAY)

Three real-time triggers are combined into **a single multiplier (1.0–1.6)** via a saturation curve (tanh), which then **multiplies** Structural Risk — rather than adding to it.

| Trigger | Source | Contribution |
|---|---|---|
| Weather | BMKG 12-hour forecast | Rainfall → trigger pressure |
| Alert | BMKG Nowcast severity | Extreme/Severe/Moderate/Minor |
| Field | BPBD field report per village | Water level (TMA) Warning/Advisory/Watch |

**Why multiplicative + saturation instead of additive?**
Traditional additive models (`base + boost`) suffer from a flaw: persistent rain forces the score to **cap out at 100** unrealistically. With a saturation multiplier, extreme triggers *approach* a maximum limit while leveling off gracefully:

| Condition | Multiplier | Score (Semarang example, structural 45) |
|---|---|---|
| Clear | ×1.00 | 45.0 |
| Heavy rain | ×1.22 | 54.7 |
| Extreme (rain+alert+WARNING report) | ×1.57 | 70.7 |
| Double extreme (absurd scenario) | ×1.60 | 72.0 — **remains plateaued, does not explode** |

---

### Layer 3 — Momentum (where the situation is heading)

Scores are stored periodically (`engine/score_history.py`, max 24 points/city, lightweight JSON), and the system calculates **Δscore per hour**. This distinguishes between two scenarios with identical scores:

```
City A: score 60, RISING +12/hr  → "⬆ Risk rising rapidly" → high priority
City B: score 60, STABLE         → "→ Risk stable"         → under control
```

When momentum escalates rapidly (≥3/hr), the system adds priority actions:
*"⚡ Anticipate escalation in the next 1-2 hours"* — true decision support, rather than a static snapshot of current conditions.

---

### Categories (BNPB Regulation No. 2 of 2024)

| Score | Level | Color | Action |
|---|---|---|---|
| 0–25 | 🟢 NORMAL | Green | Monitor periodically |
| 25–50 | 🟡 WASPADA (WATCH) | Yellow | Prepare contingency plans |
| 50–75 | 🟠 SIAGA (ADVISORY) | Orange | Activate readiness measures |
| 75–100 | 🔴 AWAS (WARNING) | Red | Evacuate immediately |

---

### Vulnerability Map per Subdistrict

`GET /vulnerability-map/{city}` calculates the score per subdistrict:
- Non-hazard components (exposure, vulnerable, history, elevation) = derived from city score
- Hazard component = specific InaRisk value for that subdistrict
- Weather + alert boost = applied uniformly across all subdistricts within the city

Result: each subdistrict receives a unique score tailored to its local risk profile.
Clicking a polygon on the map displays score details, estimated population, and risk category.

### Relevant `/vulnerability/{city}` response fields

| Field | Meaning |
|---|---|
| `score` | Final score 0–100 (all 3 layers combined) |
| `structural_score` | Layer 1 — UNDRR structural risk (base) |
| `trigger_multiplier` | Layer 2 — trigger multiplier (1.0–1.6) |
| `momentum_rate` | Layer 3 — Δscore/hr (+ rising, − falling) |
| `momentum_label` | Ready-to-display trend text |
| `risk_method` | Method name for transparency |

---

## Setup & Running

### Prerequisites

| Tools | Version | Installation |
|---|---|---|
| Python | 3.10+ | [python.org](https://python.org) or `brew install python@3.11` |
| Node.js | 18+ | [nodejs.org](https://nodejs.org) or `brew install node` |
| Docker | any | [docker.com](https://docker.com) — for PostgreSQL |

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

# 3. Configuration
cp .env.example .env
# Edit .env: set GEMINI_API_KEY obtained from aistudio.google.com
# .env.example defaults to SKIP_DB=true → runs out of the box without database

# 4. Run backend (terminal 1)
uvicorn api.main:app --reload --port 8080

# 5. Run frontend (terminal 2)
cd frontend
npm install
npm run dev
```

> **Without a database?** By default `SKIP_DB=true` → backend uses file cache,
> eliminating the need for Docker/Postgres. Ideal for demonstrations. See the
> [Database Options](#database-options) section to enable Postgres.

> **Apple Silicon (M1/M2/M3)?** Geospatial packages include pre-built binary wheels for arm64.
> If installation errors occur: run `brew install gdal proj geos` and re-run `pip install`.

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

# 3. Configuration
Copy-Item .env.example .env
notepad .env   # set GEMINI_API_KEY (SKIP_DB is true by default)

# 4. Backend (terminal 1)
uvicorn api.main:app --reload --port 8080

# 5. Frontend (new terminal)
cd frontend
npm install
npm run dev
```

---

### Setup Gemini API Key (required for AI narrative)

1. Open [aistudio.google.com](https://aistudio.google.com) → Login
2. Click **"Get API Key"** → **"Create API key"**
3. Copy key and paste into `.env`:
   ```
   GEMINI_API_KEY=AQ...
   GEMINI_MODEL=gemini-3.5-flash
   ```
4. Restart backend — narrative source changes from *"Template Engine"* to *"Gemini AI Studio (Free)"*

**Free tier limits:** 15 req/min, 1 million tokens/day — more than sufficient for demonstration purposes.

---

### Environment Variables (`.env`)

| Variable | Required | Default | Description |
|---|---|---|---|
| `GEMINI_API_KEY` | ✅ for AI | — | From [aistudio.google.com](https://aistudio.google.com) |
| `GEMINI_MODEL` | ✅ for AI | `gemini-3.5-flash` | Gemini model targeted |
| `SKIP_DB` | — | `true` | `true` = file cache (no Postgres); `false` = use Postgres |
| `DATABASE_URL` | ⚠️ if `SKIP_DB=false` | `postgresql://sigap:sigap@localhost:5432/sigap` | Postgres connection string |
| `DEMO_MODE` | — | `false` | `true` = skip Gemini + EE, use fallback template |
| `REFRESH_TOKEN` | — | — | Token for Cloud Scheduler endpoint |
| `GCP_PROJECT_ID` | — | — | Only if using Vertex AI (paid) |
| `CACHE_DIR` | — | `data/cache` | Cache directory path |

---

### Database Options

SIGAP can run with or without a database.

#### Option A — Without Database (default, easiest)

Set `SKIP_DB=true` in `.env` (configured as default in `.env.example`). Backend relies on
file-based caching under `data/cache/` and reports are saved to `data/flood_reports.json`.
**No Docker or Postgres required.** Best suited for demos & development.

#### Option B — PostgreSQL via Docker

```bash
docker compose up -d        # Postgres 16, credentials sigap/sigap
# set SKIP_DB=false in .env
uvicorn api.main:app --reload --port 8080
```

> 💡 **Running Full-Stack via Docker (PostgreSQL + Backend + Frontend):**
> Execute `docker compose up --build`. The complete application will run at `http://localhost:3000`.
> For GCP production deployment instructions, refer to [DEPLOYMENT.md](DEPLOYMENT.md).

#### Option C — Direct PostgreSQL Installation (without Docker)

1. Download [PostgreSQL 16](https://www.enterprisedb.com/downloads/postgres-postgresql-downloads)
2. During setup: set port to `5432`, record password for user `postgres`
3. Create database & user via **SQL Shell (psql)**:
   ```sql
   CREATE USER sigap WITH PASSWORD 'sigap';
   CREATE DATABASE sigap OWNER sigap;
   GRANT ALL PRIVILEGES ON DATABASE sigap TO sigap;
   ```
4. Set `SKIP_DB=false` in `.env`
5. Run backend — tables + 90k region codes are automatically seeded on initial run

> Toggle between options simply by modifying `SKIP_DB` in `.env` and restarting the backend server.
> Report data stored in JSON is automatically imported into Postgres the first time the database becomes available.

---

### Test Pipeline

```bash
# Test BMKG real-time (no external setup required)
python test_bmkg_live.py

# Test InaRisk BNPB
python test_inarisk_integration.py

# Test weather boost
python test_weather_integration.py

# Full POC single city
python run_poc.py semarang
```

---

## API Endpoints

Backend service runs at `http://localhost:8080`. Interactive documentation available at `/docs`.

### System

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Health check, version, demo_mode status |
| `GET` | `/cities?q={query}` | All regencies/cities from Kemendagri catalog |
| `GET` | `/cities/search?q={query}` | Search regencies/cities (min 2 chars), limit 1-50 |
| `GET` | `/cities/{kode}` | Single regency/city + bbox details |
| `POST` | `/internal/refresh-baselines` | Refresh stale InaRisk baselines (Cloud Scheduler) |

### Data (real-time)

| Method | Endpoint | Cache | Description |
|---|---|---|---|
| `GET` | `/alerts?city={kode}` | 30 mins | Active BMKG alerts, filtered by city province |
| `GET` | `/weather/{city}` | 6 hours | BMKG 12-hour forecast + score boost |
| `GET` | `/features/{city}` | 7 days (DB) | Raw InaRisk features (EE fallback) |

### Analysis (AI)

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/vulnerability/{city}` | Score 0-100 + 7-component breakdown |
| `GET` | `/narasi/{city}` | Gemini AI narrative in Indonesian |
| `GET` | `/analyze/{city}` | **Full pipeline** — primary endpoint for frontend |

### Field Reports (BPBD field reports)

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/flood-report` | Submit report per village, boosts score instantly |
| `GET` | `/flood-reports/{city}` | Last 12 hours reports + active boost status |
| `GET` | `/flood-villages/{city}` | Villages/kelurahan grouped by subdistrict |
| `DELETE` | `/flood-reports/{city}` | Reset field reports (for re-demo) |

### Map Data

| Method | Endpoint | Cache | Description |
|---|---|---|---|
| `GET` | `/flood-polygons/{city}` | 7 days | GeoJSON subdistricts + hazard index |
| `GET` | `/vulnerability-map/{city}` | 10 mins | GeoJSON + vuln_score per subdistrict |

---

## Project Structure

```
sigap/
├── api/
│   └── main.py               # FastAPI v0.4.0, 16 endpoints, lifespan DB init
│
├── engine/
│   ├── risk_model.py         # 3-layer risk model: UNDRR + saturation + momentum
│   ├── score_history.py      # Score history tracking for momentum (Δscore/hr)
│   ├── vulnerability.py      # Score components + BMKG boost (used by Layer 1-2)
│   ├── scoring.py            # 3-layer orchestration + field reports
│   ├── city_profile.py       # Auto-generated city profiles for Gemini prompts
│   ├── narrator.py           # Gemini AI narrative (AI Studio → Vertex → template)
│   ├── baseline.py           # InaRisk cache management, 7-day TTL (Postgres)
│   ├── flood_report.py       # Field report CRUD, 12-hour window (Postgres)
│   ├── db.py                 # psycopg3 data access, schema init, seeding
│   ├── places.py             # Bbox resolution (wilayah_geo → hardcoded → InaRisk)
│   ├── wilayah.py            # Catalog of 90k+ region codes (Kemendagri)
│   └── wilayah_geo.py        # Spatial profiles: center, bbox, elevation per region
│
├── pipeline/
│   ├── bmkg_ingest.py        # BMKG CAP/XML alerts, 30-minute cache
│   ├── bmkg_weather.py       # BMKG 12-hour subdistrict forecasts, 6-hour cache
│   ├── inarisk_loader.py     # InaRisk geospatial grid sampling, 7-day cache
│   ├── inarisk_polygon.py    # InaRisk subdistrict polygons + hazard, 7-day cache
│   ├── city_registry.py      # Legacy utility: InaRisk regency/city registry
│   └── ee_loader.py          # Google Earth Engine (final fallback)
│
├── frontend/
│   ├── package.json          # React + Vite + Leaflet (Tailwind 3.4.12, Vite 5.4.8)
│   └── src/
│       ├── App.jsx           # Main layout: sidebar, tabs, city state
│       ├── components/
│       │   ├── Header.jsx           # 514 city search, nav tabs, theme toggle
│       │   ├── WeatherBar.jsx       # Weather strip + BMKG rainfall stats
│       │   ├── AlertPanel.jsx       # BMKG alerts with severity badge
│       │   ├── VulnerabilityCard.jsx # Arc gauge + breakdown bars
│       │   ├── NarasiPanel.jsx      # AI narrative + priority actions + resources
│       │   ├── MapView.jsx          # Leaflet + InaRisk polygon + KecamatanPanel
│       │   ├── FloodInputPanel.jsx  # Village-level field report input form
│       │   ├── FloodReportPanel.jsx # Field reports panel + history
│       │   ├── ReportPage.jsx       # Dedicated full report page (/report)
│       │   ├── GoogleAuthModal.jsx  # Google Sign-In modal (GSI)
│       │   └── GoogleIcon.jsx       # Google icon component
│       ├── hooks/
│       │   ├── useAnalysis.js       # Fetch /analyze/{city}, 5-minute auto-refresh
│       │   └── useFloodReports.js
│       └── lib/
│           ├── api.js               # All HTTP client requests to backend
│           ├── mockData.js          # Fallback mock data
│           ├── AuthContext.jsx      # Google login state management (frontend)
│           └── ThemeContext.jsx     # Dark/light mode context
│
├── db/
│   └── schema.sql            # 5 Postgres tables: regions, profiles, reports, baselines, weather
│
├── knowledge/
│   ├── geografi/
│   │   ├── wilayah.sql             # 90k+ Kemendagri region codes
│   │   └── wilayah_level_1_2.sql   # Spatial profiles for prov + regency/city
│   └── sop/
│       ├── status_keadaan_darurat_bnpb.md   # BNPB 2016 Guidelines
│       ├── sistem_peringatan_dini_bnpb_2024.md  # BNPB Regulation No.2/2024
│       └── rambu_papan_informasi_bnpb_2025.md   # BNPB Regulation No.3/2025
│
├── data/
│   ├── cache/                # Cache directory: weather_*.json, bmkg_*.json, *.geojson
│   └── flood_reports.json    # Legacy — imported to Postgres on initial startup
│
├── docker-compose.yml        # PostgreSQL 16, credentials sigap/sigap, port 5432
├── requirements.txt
├── .env.example
└── run_poc.py
```

---

## Component Status

### Backend

| Component | File | Status |
|---|---|---|
| API server | `api/main.py` | ✅ v0.4.0, 16 endpoints |
| Vulnerability scorer | `engine/vulnerability.py` | ✅ 5 static + 2 dynamic components |
| Score orchestration | `engine/scoring.py` | ✅ baseline + weather + alerts + field |
| Gemini narrator | `engine/narrator.py` | ✅ AI Studio (free) → Vertex → template |
| InaRisk cache (DB) | `engine/baseline.py` | ✅ Postgres, 7-day TTL |
| Flood reports (DB) | `engine/flood_report.py` | ✅ Postgres, 12-hour window |
| Database layer | `engine/db.py` | ✅ psycopg3, auto-init + seeding |
| Region catalog | `engine/wilayah.py` | ✅ 90k+ Kemendagri codes |
| Spatial region | `engine/wilayah_geo.py` | ✅ bbox, center, elevation |
| Bbox resolution | `engine/places.py` | ✅ 3-tier fallback |
| BMKG alerts | `pipeline/bmkg_ingest.py` | ✅ Real-time CAP/XML |
| BMKG weather | `pipeline/bmkg_weather.py` | ✅ Real-time 12-hour forecast |
| InaRisk features | `pipeline/inarisk_loader.py` | ✅ Live grid sampling |
| InaRisk polygons | `pipeline/inarisk_polygon.py` | ✅ Subdistrict boundaries |

### Frontend

| Component | File | Status |
|---|---|---|
| Layout + routing (Dashboard / Report page) | `App.jsx` | ✅ Two pages: `/` and `/report` |
| City search 514 regencies/cities | `Header.jsx` | ✅ Searchable dropdown + nav tabs |
| Weather strip | `WeatherBar.jsx` | ✅ |
| BMKG alerts | `AlertPanel.jsx` | ✅ Per-province filter |
| Score gauge | `VulnerabilityCard.jsx` | ✅ Arc gauge + 7 components |
| AI briefing | `NarasiPanel.jsx` | ✅ |
| Interactive map | `MapView.jsx` | ✅ Dynamic fit-bounds + polygon click → KecamatanPanel |
| Field report (input) | `FloodInputPanel.jsx` | ✅ Searchable village/kelurahan |
| Field report (panel + history) | `FloodReportPanel.jsx` | ✅ |
| Dedicated report page | `ReportPage.jsx` | ✅ Separate from main dashboard |
| Google Login (frontend) | `AuthContext.jsx`, `GoogleAuthModal.jsx` | ⚠️ GSI integrated, backend token verification pending |

### Infrastructure

| Component | Status |
|---|---|
| PostgreSQL (Docker) | ✅ `docker compose up -d` |
| PostgreSQL (direct install) | ✅ Alternative without Docker — see Setup |
| No-DB mode (`SKIP_DB=true`) | ✅ File cache fallback, demo without Postgres |
| Google AI Studio (free) | ✅ `GEMINI_API_KEY` in `.env` |
| Vertex AI | ⚠️ Optional, requires GCP billing setup |
| Google Earth Engine | ⚠️ Final fallback option, requires GEE auth |
| API backend Auth | ❌ Pending — endpoints are currently public |
| Public deployment | ❌ Pending — Vercel/Cloud Run manifests not yet configured |

---

## What is Done vs Pending

**✅ Operational (Core Engine):**
- Real-time data integration: BMKG alerts + weather forecast, InaRisk BNPB 6 layers
- Dynamic vulnerability scoring: base + weather boost + alert boost + field report boost
- Subdistrict polygon mapping with localized scores (514 regencies/cities)
- Gemini AI narratives (free tier, `gemini-3.5-flash`)
- BPBD field report submission → real-time risk score escalation
- Postgres database support with seamless no-DB fallback mode

**⚠️ In Progress:**
- **Knowledge base**: SOP and city documents are drafted in `knowledge/`, BUT not yet read into Gemini prompts (narratives are driven solely by metrics — see ROADMAP priority #1)
- **Google Authentication**: implemented on frontend, backend API token verification pending
- **City knowledge coverage**: currently Semarang only; 3 additional cities pending

**🔲 Pending:**
- Knowledge base integration into Gemini prompts (RAG) — **highest priority next step**
- Production deployment setup (Vercel + Cloud Run/Railway)
- Threshold calibration based on historical disaster data
- Integration with PetaBencana.id crowdsourced data & river sensor (AWLR) feeds

> Detailed tasks + priority roadmap available in [ROADMAP.md](ROADMAP.md).

---

## Team

| Role | Responsibilities |
|---|---|
| Data Scientist | BMKG/InaRisk data pipelines, vulnerability scorer, Gemini prompt engineering |
| Backend | FastAPI endpoints, DB schema, region catalog, Docker configuration |
| Frontend | React dashboard, Leaflet mapping, UI/UX design |

---

*Last updated: October 2026 — v0.4.0*

**Verified operational data:**
- BMKG: 17 active alerts, real-time with zero setup required
- InaRisk Semarang: flood_ratio=46.4%, inarisk_score=0.628
- InaRisk Jakarta: 82 subdistrict polygons, flood_ratio=49.7%
- Gemini AI Studio: Indonesian narratives using `gemini-3.5-flash`
- Postgres: 90k+ Kemendagri region codes, flood reports, baseline cache