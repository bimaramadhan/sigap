# SIGAP — Roadmap Menuju Solusi Utuh

> Dokumen ini menjelaskan langkah-langkah konkret yang perlu dilakukan
> untuk mengubah SIGAP dari POC/demo menjadi sistem yang benar-benar
> bisa digunakan oleh koordinator BPBD di lapangan.
>
> Dibagi per area kerja dan per orang sesuai pembagian tim.

---

## Daftar Isi

- [Gambaran Besar](#gambaran-besar)
- [Pilar 1 — Data Real-time](#pilar-1--data-real-time)
- [Pilar 2 — Knowledge Base untuk LLM](#pilar-2--knowledge-base-untuk-llm)
- [Pilar 3 — InaRisk & Risiko Wilayah](#pilar-3--inarisk--risiko-wilayah)
- [Pilar 4 — Banjir Log & Feedback Loop](#pilar-4--banjir-log--feedback-loop)
- [Pilar 5 — AI Decision Engine](#pilar-5--ai-decision-engine)
- [Pilar 6 — Infrastructure & Deploy](#pilar-6--infrastructure--deploy)
- [Urutan Prioritas untuk Hackathon](#urutan-prioritas-untuk-hackathon)
- [Checklist Status](#checklist-status)

---

## Gambaran Besar

SIGAP saat ini sudah punya **kerangka** yang berfungsi. Yang belum ada adalah
**isinya** — data yang akurat, knowledge yang tepat, dan loop pembelajaran
dari kejadian nyata.

Analogi yang tepat:

```
Sekarang:
  Sistem ada, tapi seperti dokter yang belum punya buku kedokteran.
  Dia bisa bicara, tapi rekomendasinya belum bisa dipercaya.

Target:
  Sistem yang punya SOP lengkap, data historis, dan terus belajar
  dari setiap kejadian banjir yang terjadi.
```

Untuk menjadi solusi utuh, ada **6 pilar** yang harus diselesaikan:

```
┌─────────────────────────────────────────────────────────────┐
│                    SOLUSI UTUH SIGAP                        │
│                                                             │
│  Pilar 1          Pilar 2          Pilar 3                  │
│  Data Real-time   Knowledge Base   InaRisk Data             │
│  (trigger)        (LLM context)    (risiko wilayah)         │
│       │                │                │                   │
│       └────────────────┴────────────────┘                   │
│                         │                                   │
│                         ▼                                   │
│              Pilar 5 — AI Decision Engine                   │
│              (gabungkan semua, hasilkan keputusan)          │
│                         │                                   │
│                         ▼                                   │
│              Pilar 4 — Banjir Log                           │
│              (catat kejadian nyata)                         │
│                         │                                   │
│                         ▼                                   │
│              Pilar 4b — Re-train & Kalibrasi                │
│              (sistem makin akurat tiap siklus)              │
│                                                             │
│              Pilar 6 — Deploy & Akses                       │
│              (bisa diakses siapa saja, kapan saja)          │
└─────────────────────────────────────────────────────────────┘
```

---

## Pilar 1 — Data Real-time

> **PIC: Dhana + Data Scientist**
> Tujuan: SIGAP punya input data yang berubah setiap jam,
> bukan hanya baseline statis.

### Masalah sekarang

Vulnerability score saat ini dihitung dari data yang tidak berubah —
DEM elevasi, flood hazard historis, populasi 2020. Skor Semarang
akan tetap 72.4 baik di hari cerah maupun saat banjir sedang terjadi.
Ini tidak berguna untuk decision support.

### Yang perlu ditambahkan

#### 1.1 Curah Hujan Aktual BMKG

BMKG menyediakan data prakiraan cuaca per kecamatan dalam format JSON.

```
Endpoint: https://api.bmkg.go.id/publik/prakiraan-cuaca?adm4={kode_wilayah}
Dokumentasi: https://data.bmkg.go.id/prakiraan-cuaca
Format: JSON, update 2x sehari

Data yang didapat:
- Cuaca (cerah/hujan/hujan lebat/badai petir)
- Suhu min/max
- Kelembaban
- Kecepatan & arah angin
- Per 3 jam untuk 3 hari ke depan
```

**Langkah yang perlu dilakukan:**
- [ ] Fetch kode wilayah (adm4) untuk Semarang, Bekasi, Jakarta dari BPS
- [ ] Buat `pipeline/bmkg_weather.py` — fetch prakiraan cuaca per kecamatan
- [ ] Integrasikan ke vulnerability scorer: curah hujan tinggi = boost skor hazard
- [ ] Test: bandingkan skor saat cuaca cerah vs. saat ada prakiraan hujan lebat

#### 1.2 Level Sungai (AWLR) — Target jangka menengah

AWLR (Automatic Water Level Recorder) adalah sensor ketinggian sungai yang dipasang BMKG/BBWS.
Ini data paling langsung untuk prediksi banjir — kalau sungai naik 20cm/jam, banjir dalam 2-3 jam.

```
Status: Belum ada public API yang stabil
Alternatif:
  - Coba akses: https://afis.bmkg.go.id (Analisa Frekuensi & Iklim Sungai)
  - Atau: scraping dari siswaskeun.go.id (Sistem Informasi Sumber Daya Air)
  - Untuk demo: buat slider manual "tinggi sungai saat ini" di dashboard
```

**Langkah yang perlu dilakukan:**
- [ ] Explore apakah AFIS BMKG bisa diakses programmatically
- [ ] Jika tidak: buat input manual "Update Level Sungai" di dashboard
- [ ] Definisikan trigger: level berapa = siaga berapa

#### 1.3 PetaBencana.id — Laporan Crowdsourced

Platform open source yang mengumpulkan laporan banjir real-time dari
masyarakat via Twitter/X, Telegram, dan WhatsApp.

```
API: https://api.petabencana.id/floods?city=jbd (Jakarta Barat-Timur)
     https://api.petabencana.id/floods?city=smr (Semarang)
Format: GeoJSON
Update: Real-time

Data yang didapat:
- Titik lokasi banjir yang dilaporkan warga
- Tinggi genangan (dari laporan)
- Waktu laporan
- Link foto (kalau ada)
```

**Langkah yang perlu dilakukan:**
- [ ] Test endpoint PetaBencana untuk Semarang dan Jakarta
- [ ] Buat `pipeline/petabencana_ingest.py`
- [ ] Overlay titik laporan di peta Leaflet (dot merah = laporan aktif)
- [ ] Gunakan sebagai signal tambahan: banyak laporan = konfirmasi banjir aktual

---

## Pilar 2 — Knowledge Base untuk LLM

> **PIC: Bima**
> Tujuan: LLM punya pengetahuan yang valid tentang prosedur BPBD,
> karakteristik banjir per kota, dan cara menghitung kebutuhan resource.
> Tanpa ini, LLM hanya mengarang.

### Masalah sekarang

Gemini menghasilkan narasi dari angka vulnerability scorer. Tapi dia
tidak tahu SOP BPBD, tidak tahu karakteristik banjir Semarang,
tidak tahu berapa perahu yang dibutuhkan untuk 500 jiwa.
Hasilnya terdengar generic dan tidak bisa dipercaya untuk keputusan nyata.

### Struktur folder yang perlu dibuat

```
sigap/knowledge/
├── sop/
│   ├── level_siaga_banjir.md
│   ├── tindakan_per_level.md
│   ├── prioritas_evakuasi.md
│   └── kebutuhan_resource.md
│
├── kota/
│   ├── semarang.md
│   ├── bekasi.md
│   └── jakarta.md
│
├── historis/
│   ├── banjir_semarang_2024.md
│   ├── banjir_jakarta_2020.md
│   └── template_kejadian.md
│
└── referensi/
    ├── istilah_dan_definisi.md
    └── sumber_data.md
```

### Konten per file — panduan untuk Bima

#### `sop/level_siaga_banjir.md`

Isi yang dibutuhkan:
- Definisi Siaga 1, 2, 3, 4 dalam konteks BPBD Indonesia
- Trigger masing-masing level (TMA berapa cm, curah hujan berapa mm)
- Tindakan wajib per level
- Pihak yang harus dihubungi di tiap level

Sumber:
```
1. Perka BNPB No. 7 Tahun 2015 — Rambu dan Papan Informasi Bencana
   → https://bnpb.go.id/peraturan

2. SOP Siaga Bencana BPBD DKI Jakarta
   → https://bpbd.jakarta.go.id/sop

3. Panduan Umum Kesiapsiagaan BNPB
   → https://bnpb.go.id/buku-panduan-kesiapsiagaan
```

#### `sop/kebutuhan_resource.md`

Isi yang dibutuhkan:
- Berapa perahu untuk X jiwa terdampak
- Berapa tim SAR untuk area Y km²
- Kapasitas tempat pengungsian
- Estimasi logistik (makanan, air, obat) per 100 jiwa per hari

Sumber:
```
Sphere Handbook (standar internasional humanitarian response)
→ https://spherestandards.org/handbook/
→ Bab: Tempat Pengungsian, Air & Sanitasi, Pangan

BNPB — Pedoman Penanggulangan Bencana
→ https://bnpb.go.id/pedoman
```

#### `kota/semarang.md`

Isi yang dibutuhkan:
- Area yang paling sering banjir (nama kelurahan/kecamatan spesifik)
- Penyebab utama (rob, luapan sungai, drainase)
- Pola waktu: bulan apa paling rawan, jam berapa biasanya puncak
- Nama sungai kritis dan level TMA bahayanya
- Titik evakuasi yang sudah ada
- Nomor kontak BPBD Semarang

Sumber:
```
1. Website BPBD Kota Semarang: https://bpbd.semarangkota.go.id
2. Rencana Kontinjensi Banjir Kota Semarang (minta ke BPBD atau cari di Google)
3. Berita banjir Semarang 2022, 2023, 2024 (untuk pola dan area rawan)
4. InaRisk Semarang: https://inarisk.bnpb.go.id
```

#### `historis/template_kejadian.md`

Template untuk setiap kejadian banjir yang didokumentasikan:

```markdown
# Banjir [Kota] — [Tanggal]

## Kronologi
- [Jam] : ...
- [Jam] : ...

## Area Terdampak
- Kelurahan/RW yang terendam
- Tinggi genangan tertinggi

## Data Dampak
- Jiwa terdampak: ...
- Pengungsi: ...
- Korban jiwa: ...
- Rumah terendam: ...

## Penyebab
...

## Resource yang Digunakan
- Perahu: ... unit
- Tim SAR: ... orang
- Titik pengungsian: ...

## Lessons Learned
- Apa yang berhasil
- Apa yang terlambat atau salah
- Rekomendasi untuk kejadian berikutnya
```

### Cara mengintegrasikan ke LLM

Setelah dokumen-dokumen ini selesai, cara paling sederhana untuk
POC hackathon adalah **memasukkan langsung ke system prompt Gemini**:

```python
# Di narrator.py — tambahkan knowledge ke system prompt

def _load_knowledge(city: str) -> str:
    """Load relevant knowledge files untuk kota tertentu."""
    knowledge_dir = Path("knowledge")
    files_to_load = [
        knowledge_dir / "sop" / "level_siaga_banjir.md",
        knowledge_dir / "sop" / "prioritas_evakuasi.md",
        knowledge_dir / "sop" / "kebutuhan_resource.md",
        knowledge_dir / "kota" / f"{city}.md",
    ]
    content = []
    for f in files_to_load:
        if f.exists():
            content.append(f.read_text(encoding="utf-8"))
    return "\n\n---\n\n".join(content)

SYSTEM_PROMPT = """
Kamu adalah SIGAP AI untuk koordinator BPBD Indonesia.

KNOWLEDGE BASE:
{knowledge}

Gunakan knowledge di atas sebagai referensi utama.
Jangan membuat rekomendasi yang bertentangan dengan SOP di atas.
...
"""
```

Untuk implementasi yang lebih sophisticated (RAG proper):
menggunakan **Vertex AI Search** atau **Vector Store** — tapi ini
bisa dikerjakan setelah knowledge content-nya ada.

---

## Pilar 3 — InaRisk & Risiko Wilayah

> **PIC: Dhana**
> Tujuan: Mendapatkan data risiko banjir per kecamatan dari BNPB
> yang lebih akurat dari JRC GloFAS.

### Mengapa InaRisk penting

JRC GloFAS adalah dataset global. InaRisk adalah dataset yang dibuat
khusus untuk Indonesia oleh BNPB — lebih detail, lebih relevan konteks lokal,
dan sudah memperhitungkan kondisi spesifik Indonesia seperti rob, drainase kota, dll.

### Cara mengakses InaRisk

#### Opsi A — Portal Web (manual)

```
1. Buka: https://inarisk.bnpb.go.id
2. Login (perlu registrasi akun)
3. Pilih layer "Risiko Banjir"
4. Export per kabupaten/kota
5. Format: shapefile atau GeoJSON
```

#### Opsi B — GIS Service (programmatic)

```
Endpoint GIS:
http://service1.inarisk.bnpb.go.id:6080/arcgis/rest/services/

Cara akses:
import requests

url = "http://service1.inarisk.bnpb.go.id:6080/arcgis/rest/services/"
resp = requests.get(url + "?f=json")

Kalau berhasil: akan return list layer yang tersedia
Kalau timeout: server mungkin tidak publik, lanjut ke Opsi C
```

#### Opsi C — CKAN API data.bnpb.go.id

```python
import requests

# Search dataset risiko banjir
url = "https://data.bnpb.go.id/api/3/action/package_search"
params = {
    "q": "risiko banjir",
    "rows": 10
}
resp = requests.get(url, params=params)
datasets = resp.json()["result"]["results"]

# Download resource dari dataset yang ditemukan
for ds in datasets:
    for resource in ds["resources"]:
        print(resource["name"], resource["url"])
```

#### Opsi D — Email langsung ke BNPB

Kalau semua opsi di atas tidak berhasil:

```
Email: pemetaan.bnpb@gmail.com
Subject: Permintaan Data InaRisk untuk Riset/Hackathon
Isi: Jelaskan keperluan, minta data risiko banjir
     per kecamatan untuk Semarang/Bekasi/Jakarta
     dalam format GeoJSON atau shapefile
```

### Yang perlu Dhana lakukan

- [ ] Coba Opsi B terlebih dahulu (paling cepat)
- [ ] Jika gagal, coba Opsi C
- [ ] Jika gagal, email ke BNPB (Opsi D)
- [ ] Setelah data didapat: simpan di `sigap/data/sample/inarisk_semarang.geojson`
- [ ] Buat script `pipeline/inarisk_loader.py` untuk load dan parse data
- [ ] Integrasikan ke vulnerability scorer sebagai pengganti/pelengkap JRC GloFAS

### Data yang diharapkan dari InaRisk

```json
{
  "kecamatan": "Semarang Utara",
  "kabupaten": "Kota Semarang",
  "risiko_banjir": "Tinggi",
  "indeks_bahaya": 0.78,
  "indeks_kerentanan": 0.65,
  "indeks_kapasitas": 0.42,
  "indeks_risiko": 0.71
}
```

---

## Pilar 4 — Banjir Log & Feedback Loop

> **PIC: Backend Developer + Data Scientist**
> Tujuan: Setiap kejadian banjir yang terjadi dicatat,
> dan catatan itu digunakan untuk membuat sistem makin akurat.

### Konsep

```
Siklus pembelajaran SIGAP:

BPBD input laporan           SIGAP belajar dari data
kejadian nyata              kejadian nyata
      │                              ▲
      ▼                              │
┌─────────────────┐    ┌─────────────────────────┐
│  Banjir Log DB  │───►│  Evaluasi & Kalibrasi   │
│                 │    │                         │
│  - Tanggal      │    │  - Prediksi vs. Aktual  │
│  - Lokasi       │    │  - Adjust bobot skor    │
│  - Tinggi air   │    │  - Update knowledge     │
│  - Area dampak  │    │  - Retrain jika perlu   │
│  - Jumlah jiwa  │    └─────────────────────────┘
│  - Resource     │
│  - Foto         │
└─────────────────┘
```

### 4.1 Database Schema Banjir Log

```sql
CREATE TABLE flood_events (
    id              SERIAL PRIMARY KEY,
    reported_at     TIMESTAMP NOT NULL,
    city            VARCHAR(100),
    kecamatan       VARCHAR(100),
    kelurahan       VARCHAR(100),
    rw              VARCHAR(20),

    -- Kondisi saat kejadian
    water_level_cm  INTEGER,        -- Tinggi genangan
    duration_hours  FLOAT,          -- Durasi genangan

    -- Dampak
    households_affected  INTEGER,
    people_affected      INTEGER,
    evacuees             INTEGER,
    casualties           INTEGER DEFAULT 0,

    -- Catatan
    cause           TEXT,           -- Penyebab (rob/luapan/drainase)
    notes           TEXT,
    photo_urls      TEXT[],         -- Array URL foto

    -- SIGAP prediction saat itu
    sigap_score_at_event   FLOAT,   -- Skor SIGAP ketika kejadian terjadi
    sigap_category         VARCHAR(20),

    -- Metadata
    reported_by     VARCHAR(100),   -- Nama petugas
    verified        BOOLEAN DEFAULT FALSE
);
```

### 4.2 Form Input di Frontend

Tambahkan halaman "Laporan Kejadian" di dashboard:

```
┌─────────────────────────────────────────────────┐
│          LAPORAN KEJADIAN BANJIR                │
├─────────────────────────────────────────────────┤
│ Kota/Kecamatan: [Semarang Utara        ▼]       │
│ Tanggal & Jam : [24/09/2026  15:30    ]          │
│ Tinggi Genangan: [  80  ] cm                    │
│ Jiwa Terdampak : [ 2300 ] jiwa                  │
│ Pengungsi      : [  450 ] jiwa                  │
│                                                 │
│ Penyebab:                                       │
│ ○ Rob (pasang laut)                             │
│ ● Luapan sungai                                 │
│ ○ Drainase tersumbat                            │
│                                                 │
│ Catatan: [                              ]       │
│                                                 │
│ Upload Foto: [📎 Pilih file]                    │
│                                                 │
│            [  KIRIM LAPORAN  ]                  │
└─────────────────────────────────────────────────┘
```

### 4.3 Re-train & Kalibrasi (Iterasi ke-2)

Setelah ada cukup data log (minimal 20-30 kejadian), lakukan:

**Evaluasi prediksi:**
```python
def evaluate_predictions(db):
    """
    Bandingkan: skor SIGAP saat kejadian vs. severity aktual.
    Kalau skor 60 tapi actual damage besar → threshold perlu disesuaikan.
    Kalau skor 80 tapi tidak ada banjir → bobot perlu dikurangi.
    """
    events = db.query("SELECT sigap_score_at_event, people_affected FROM flood_events")

    # Plot: skor vs. dampak nyata
    # Dari sini ketahuan: threshold mana yang perlu di-adjust
```

**Kalibrasi threshold:**
```python
# Sebelum kalibrasi (arbitrary)
SCORE_CATEGORIES = {
    (0,  25): "RENDAH",
    (25, 50): "SEDANG",
    (50, 75): "TINGGI",
    (75, 100): "KRITIS"
}

# Setelah kalibrasi (berbasis data historis Indonesia)
# Contoh hasil: ternyata "KRITIS" sebaiknya mulai dari 65, bukan 75
# karena di Indonesia, dampak besar sudah mulai di skor 65
SCORE_CATEGORIES_CALIBRATED = {
    (0,  20): "RENDAH",
    (20, 45): "SEDANG",
    (45, 65): "TINGGI",
    (65, 100): "KRITIS"
}
```

---

## Pilar 5 — AI Decision Engine

> **PIC: Data Scientist (Anda)**
> Tujuan: AI tidak hanya menghasilkan narasi, tapi
> keputusan yang spesifik, terukur, dan sesuai konteks Indonesia.

### Gap sekarang vs. target

```
SEKARANG:
  Input  → [Vulnerability Scorer] → Skor 72.4
  Skor   → [Gemini + template]    → "Risiko tinggi, siapkan evakuasi"

TARGET:
  Input  → [Vulnerability Scorer] → Skor 72.4
  Skor   → [Knowledge Retrieval]  → Ambil SOP level Siaga 2
  Skor + → [Gemini + RAG]         → "Berdasarkan SOP BPBD, kondisi ini
  SOP  +                             setara Siaga 2. Dalam 2 jam ke depan:
  Historis                           1. Preposisi 3 perahu di titik A, B, C
                                     2. Notifikasi 847 KK di zona merah
                                     3. Buka shelter SDN 04 (kapasitas 200)"
```

### 5.1 Integrasikan BMKG Alert ke Scoring

Langkah paling cepat yang mengubah sistem dari statis ke dinamis.

```python
# Di engine/vulnerability.py — tambahkan fungsi ini

def apply_bmkg_boost(base_score: float, alerts: list) -> tuple[float, str]:
    """
    Adjust skor berdasarkan alert BMKG aktif untuk provinsi terkait.

    Returns:
        (adjusted_score, reason)
    """
    SEVERITY_BOOST = {
        "Extreme":  25,
        "Severe":   15,
        "Moderate":  8,
        "Minor":     3,
    }

    if not alerts:
        return base_score, "Tidak ada alert aktif"

    # Ambil severity tertinggi dari alert yang relevan
    max_severity = max(
        SEVERITY_BOOST.get(a.get("severity", "Minor"), 3)
        for a in alerts
    )

    adjusted = min(100, base_score + max_severity)
    reason   = f"BMKG alert aktif → +{max_severity} poin"

    return round(adjusted, 1), reason
```

### 5.2 Tambah Komponen Data Real-time ke Scoring

Setelah data curah hujan (Pilar 1) tersedia:

```python
# Komponen ke-6: Real-time Weather (dinamis)
def get_weather_score(rainfall_mm_6h: float) -> float:
    """
    Normalisasi curah hujan 6 jam ke skor 0-1.
    Referensi BMKG: >50mm/6jam = hujan lebat, >100mm = sangat lebat
    """
    RAINFALL_MAX = 150  # mm/6jam = skor penuh
    return min(1.0, rainfall_mm_6h / RAINFALL_MAX)

# Update WEIGHTS — tambahkan weather, kurangi bobot lain sedikit
WEIGHTS = {
    "hazard":      0.25,  # turun dari 0.30
    "exposure":    0.20,  # turun dari 0.25
    "vulnerable":  0.20,  # turun dari 0.25
    "history":     0.10,
    "elevation":   0.10,
    "weather":     0.15,  # BARU — curah hujan real-time
}
```

### 5.3 RAG untuk Knowledge-based Decision

Implementasi bertahap:

**Fase 1 — Simple context injection (bisa dikerjakan sekarang):**
```python
# Load semua file knowledge dan masukkan ke prompt Gemini
# Cocok untuk POC — simple tapi cukup efektif
knowledge_text = load_all_knowledge_files("knowledge/")
prompt = f"KNOWLEDGE BASE:\n{knowledge_text}\n\nSITUASI:\n{situation}"
```

**Fase 2 — Vertex AI Search (setelah hackathon):**
```
1. Upload dokumen knowledge ke Cloud Storage
2. Buat data store di Vertex AI Search
3. Query: "SOP evakuasi untuk siaga 2 dengan 3000 jiwa terdampak"
4. Hasil: dokumen paling relevan → masukkan ke Gemini prompt
```

---

## Pilar 6 — Infrastructure & Deploy

> **PIC: Backend Developer**
> Tujuan: Sistem bisa diakses dari internet, stabil,
> dan tidak mati saat sedang demo.

### 6.1 Opsi Deploy (urut dari paling cepat)

#### Untuk Hackathon Demo

```
Frontend → Vercel (gratis, deploy dari git)
Backend  → Railway atau Render (gratis tier, auto-deploy)
Database → Supabase (PostgreSQL gratis, untuk banjir log)

Setup time: ~2 jam
```

#### Untuk Produk Nyata

```
Frontend → Firebase Hosting atau Cloud CDN
Backend  → Google Cloud Run (serverless, auto-scale)
Database → Cloud SQL (PostgreSQL managed)
Storage  → Cloud Storage (foto, dokumen)
AI       → Vertex AI (Gemini, Search)

Setup time: ~1-2 hari
```

### 6.2 Environment yang Dibutuhkan

```
Production .env:
  GCP_PROJECT_ID=sigap-prod
  DEMO_MODE=false
  DATABASE_URL=postgresql://...
  REDIS_URL=redis://...      # Untuk caching (opsional)
  ALLOWED_ORIGINS=https://sigap.id
```

### 6.3 Basic Auth untuk Dashboard

Saat live, dashboard tidak boleh terbuka untuk umum tanpa autentikasi.
Minimal: username/password sederhana untuk BPBD.

```python
# Di api/main.py — tambahkan basic auth
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

security = HTTPBasic()

def verify_credentials(credentials: HTTPBasicCredentials = Depends(security)):
    correct_user = secrets.compare_digest(credentials.username, "bpbd_semarang")
    correct_pass = secrets.compare_digest(credentials.password, os.getenv("DASHBOARD_PASSWORD"))
    if not (correct_user and correct_pass):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
```

---

## Urutan Prioritas untuk Hackathon

Tidak semua bisa dikerjakan sebelum Oktober. Ini urutan yang disarankan:

### Minggu 1 — Foundation (sekarang)

```
✅ Sudah ada:
   - Frontend dashboard (dark/light mode, peta, alerts, score, narasi)
   - BMKG alert pipeline (data real)
   - Vulnerability scorer (formula 5 komponen)
   - Gemini narrator (+ fallback template)
   - FastAPI backend

Fokus minggu ini:
   [ ] Bima: Mulai buat knowledge/sop/level_siaga_banjir.md
   [ ] Dhana: Explore InaRisk API dan data.bnpb.go.id
   [ ] DS: Integrasikan BMKG alert ke vulnerability scoring
   [ ] BE: Setup .env, jalankan backend live, connect frontend
```

### Minggu 2 — Data Real

```
   [ ] Bima: Selesaikan 5 dokumen knowledge base
   [ ] Dhana: Load data InaRisk ke pipeline
   [ ] DS: Integrasikan curah hujan BMKG ke scoring
   [ ] DS: Integrasikan knowledge base ke Gemini prompt
   [ ] BE: Setup database untuk banjir log
   [ ] FE: Tambah form input laporan kejadian
```

### Minggu 3 — Polish & Demo

```
   [ ] End-to-end test: dari BMKG alert masuk → skor update → narasi keluar
   [ ] Siapkan skenario demo historis (banjir Semarang 2024)
   [ ] Deploy ke platform yang bisa diakses internet
   [ ] Latihan demo 3 menit
   [ ] Siapkan jawaban untuk Q&A juri
```

---

## Checklist Status

Gunakan tabel ini untuk tracking progress tim.

### Data & Pipeline

| Task | PIC | Status | Catatan |
|---|---|---|---|
| BMKG nowcast alerts | DS | ✅ Selesai | Real-time, 17 alert hari ini |
| BMKG prakiraan cuaca per kecamatan | DS | 🔲 Belum | API tersedia di data.bmkg.go.id |
| Level sungai AWLR | Dhana | 🔲 Belum | Cari akses AFIS BMKG |
| PetaBencana.id laporan crowdsourced | Dhana | 🔲 Belum | API publik tersedia |
| InaRisk risiko per kecamatan | Dhana | 🔲 Belum | Explore inarisk.bnpb.go.id |
| Data BPS populasi per kelurahan | DS | ⚠️ Parsial | Pakai WorldPop, BPS lebih detail |
| Data OSM jaringan jalan | DS | 🔲 Belum | Butuh untuk rute evakuasi |

### Knowledge Base

| Task | PIC | Status | Catatan |
|---|---|---|---|
| `sop/level_siaga_banjir.md` | Bima | 🔲 Belum | Prioritas #1 |
| `sop/tindakan_per_level.md` | Bima | 🔲 Belum | |
| `sop/prioritas_evakuasi.md` | Bima | 🔲 Belum | |
| `sop/kebutuhan_resource.md` | Bima | 🔲 Belum | |
| `kota/semarang.md` | Bima | 🔲 Belum | Area rawan, pola banjir |
| `kota/bekasi.md` | Bima | 🔲 Belum | |
| `historis/banjir_semarang_2024.md` | Bima | 🔲 Belum | |

### AI Engine

| Task | PIC | Status | Catatan |
|---|---|---|---|
| Integrasikan BMKG alert ke skor | DS | 🔲 Belum | +25 untuk Extreme, dll |
| Integrasikan curah hujan ke skor | DS | 🔲 Belum | Butuh data Pilar 1 |
| Integrasikan knowledge base ke Gemini | DS | 🔲 Belum | Butuh Pilar 2 selesai |
| Kalibrasi threshold dengan data BNPB | DS | 🔲 Belum | Iterasi ke-2 |

### Infrastructure

| Task | PIC | Status | Catatan |
|---|---|---|---|
| Setup GCP Project | Semua | ❌ Belum | Critical blocker |
| Earth Engine auth | DS | ❌ Belum | Butuh GCP |
| Gemini auth | DS | ❌ Belum | Butuh GCP |
| Deploy backend publik | BE | 🔲 Belum | Railway/Cloud Run |
| Deploy frontend publik | FE | 🔲 Belum | Vercel |
| Database banjir log | BE | 🔲 Belum | Supabase/Cloud SQL |
| Form input laporan kejadian | FE | 🔲 Belum | |

---

## Definisi "Solusi Utuh"

SIGAP dianggap sebagai solusi utuh ketika:

```
1. Data masuk otomatis dari BMKG (✅ sebagian sudah)
2. Skor berubah ketika kondisi berubah (🔲 belum)
3. Narasi berbasis SOP yang valid (🔲 butuh knowledge base)
4. Laporan kejadian nyata bisa diinput (🔲 belum)
5. Sistem belajar dari kejadian yang sudah terjadi (🔲 belum)
6. Bisa diakses dari internet oleh BPBD (🔲 belum)
7. Ada autentikasi basic (🔲 belum)
```

Untuk hackathon, **minimal nomor 1-3 harus terpenuhi** untuk
mendapatkan demo yang credible dan defensible saat Q&A juri.

---

*Dokumen ini adalah living document — update setiap ada progress.*
*Terakhir diupdate: September 2026*
