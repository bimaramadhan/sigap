"""
api/main.py
───────────
FastAPI backend untuk SIGAP POC.

Endpoints:
  GET  /                          Health check
  GET  /cities                    List kota yang didukung
  GET  /alerts                    BMKG alerts aktif (flood-relevant)
  GET  /weather/{city}            Prakiraan cuaca + rainfall 12 jam
  GET  /features/{city}           Raw EE geospatial features
  GET  /vulnerability/{city}      Vulnerability score + semua boost
  GET  /narasi/{city}             Narasi bahasa Indonesia
  GET  /analyze/{city}            Full pipeline
  POST /flood-report              Submit laporan lapangan dari BPBD [BARU]
  GET  /flood-reports/{city}      Ambil laporan lapangan terbaru [BARU]
  GET  /flood-villages/{city}     Desa/kelurahan per kecamatan [BARU]
  DELETE /flood-reports/{city}    Hapus semua laporan (reset demo) [BARU]

Jalankan:
  uvicorn api.main:app --reload --port 8080
  Buka: http://localhost:8080/docs
"""

import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from loguru import logger

load_dotenv()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    try:
        from engine.db import init_db
        init_db()
        logger.success("Database PostgreSQL terhubung")
    except Exception as e:
        logger.warning(
            f"Database tidak tersedia ({type(e).__name__}: {e}). "
            "Backend tetap jalan dengan file-based cache. "
            "Jalankan 'docker compose up -d' untuk full persistence."
        )
    yield


app = FastAPI(
    title       = "SIGAP API",
    description = "Sistem Integrasi Geospasial Aksi Penanggulangan Bencana",
    version     = "0.4.0",
    docs_url    = "/docs",
    redoc_url   = "/redoc",
    lifespan    = lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Response Models ───────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status:    str
    timestamp: str
    version:   str
    demo_mode: bool


class AlertSummary(BaseModel):
    id:              str
    province:        str
    title:           str
    severity:        str
    kecamatan_count: int
    effective:       str
    expires:         str
    is_flood:        bool


class AlertsResponse(BaseModel):
    fetched_at:   str
    total_alerts: int
    flood_alerts: int
    alerts:       list[AlertSummary]


class WeatherKecamatanDetail(BaseModel):
    kecamatan:    str
    area:         str
    rainfall_12h: float
    max_tp_3h:    float
    worst_weather:str


class WeatherResponse(BaseModel):
    """Ringkasan cuaca 12 jam ke depan dari BMKG Prakiraan Cuaca API."""
    city:                str
    fetched_at:          str
    rainfall_12h_mm:     float   # Curah hujan tertinggi antar kecamatan (mm)
    worst_weather_code:  int
    worst_weather_desc:  str
    worst_weather_emoji: str
    weather_risk:        str     # none / low / medium / high / extreme
    boost_score:         float   # Poin tambahan ke vulnerability score (0-25)
    boost_reason:        str
    is_rainy_season:     bool
    kecamatan_count:     int
    kecamatan_data:      list[WeatherKecamatanDetail]
    source:              str


class VulnerabilityResponse(BaseModel):
    city:             str
    city_label:       str
    score:            float
    base_score:       float     # Skor sebelum weather/alert boost [BARU]
    category:         str
    category_message: str
    is_sample_data:   bool
    score_breakdown:  dict
    # Weather & alert boost [BARU]
    weather_boost:    float
    weather_desc:     str
    weather_risk:     str
    alert_boost:      float
    alert_reason:     str
    # Raw stats
    flood_ratio_10yr: float
    total_population: int
    est_vulnerable:   int
    density_per_km2:  float
    historical_events:int
    elevation_mean:   float
    elevation_min:    float
    priority_actions: list[str]
    resource_needs:   dict
    baseline_fetched_at: str = ""
    baseline_age_hours:  float = 0


class NarasiResponse(BaseModel):
    city:         str
    score:        float
    category:     str
    narasi:       str
    source:       str
    model:        str
    generated_at: str


class FullAnalysisResponse(BaseModel):
    city:           str
    analyzed_at:    str
    active_alerts:  list[AlertSummary]
    weather:        WeatherResponse
    vulnerability:  VulnerabilityResponse
    narasi:         NarasiResponse
    is_sample_data: bool


# ── Flood Report Models ───────────────────────────────────────────────────────

class FloodReportRequest(BaseModel):
    city:        str
    reporter:    str = "Koordinator BPBD"
    desa_kode:   str
    flood_level: str          # normal / waspada / siaga / awas
    notes:       str = ""


class FloodReportResponse(BaseModel):
    id:                 str
    city:               str
    reported_at:        str
    reporter:           str
    desa_kode:          str
    desa_name:          str
    kecamatan:          str
    kecamatan_kode:     str
    flood_level:        str
    flood_level_label:  str
    notes:              str
    boost_score:        float
    boost_breakdown:    dict


class KecamatanBoost(BaseModel):
    boost_score: float
    flood_level: str
    desa_name:   str
    reason:      str


class FloodReportsListResponse(BaseModel):
    city:              str
    report_count:      int
    latest_boost:      float
    boost_reason:      str
    reports:           list[FloodReportResponse]
    kecamatan_boosts:  dict[str, KecamatanBoost] = {}


class VillageItem(BaseModel):
    kode: str
    nama: str


class VillageGroup(BaseModel):
    kecamatan:         str
    kecamatan_kode:    str
    kota_administrasi: str = ""
    villages:          list[VillageItem]


class FloodVillagesResponse(BaseModel):
    city:   str
    groups: list[VillageGroup]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _validate_city(city: str) -> str:
    from engine.wilayah import canonical_kab
    kab = canonical_kab(city)
    if not kab:
        raise HTTPException(
            status_code=400,
            detail=f"Kab/kota '{city}' tidak ada di katalog wilayah",
        )
    return kab


def _weather_to_response(w: dict) -> WeatherResponse:
    kec_details = [
        WeatherKecamatanDetail(
            kecamatan    = k.get("kecamatan", ""),
            area         = k.get("area", ""),
            rainfall_12h = k.get("rainfall_12h", 0),
            max_tp_3h    = k.get("max_tp_3h", 0),
            worst_weather= k.get("worst_weather", ""),
        )
        for k in w.get("kecamatan_data", [])
    ]
    return WeatherResponse(
        city                = w.get("city", ""),
        fetched_at          = w.get("fetched_at", ""),
        rainfall_12h_mm     = w.get("rainfall_12h_mm", 0),
        worst_weather_code  = w.get("worst_weather_code", 0),
        worst_weather_desc  = w.get("worst_weather_desc", ""),
        worst_weather_emoji = w.get("worst_weather_emoji", "☀️"),
        weather_risk        = w.get("weather_risk", "none"),
        boost_score         = w.get("boost_score", 0),
        boost_reason        = w.get("boost_reason", ""),
        is_rainy_season     = w.get("is_rainy_season", False),
        kecamatan_count     = w.get("kecamatan_count", 0),
        kecamatan_data      = kec_details,
        source              = w.get("_source", "BMKG"),
    )


def _vuln_to_response(result) -> VulnerabilityResponse:
    bd = result.score_breakdown()
    # Hitung base_score dari breakdown (tanpa weather+alert boost)
    base = round(sum(v for k, v in bd.items() if k not in ("weather", "alert")), 1)
    return VulnerabilityResponse(
        city             = result.city,
        city_label       = result.city_label,
        score            = result.score,
        base_score       = base,
        category         = result.category,
        category_message = result.category_message,
        is_sample_data   = result.is_sample_data,
        score_breakdown  = bd,
        weather_boost    = result.weather_boost,
        weather_desc     = result.weather_desc,
        weather_risk     = result.weather_risk,
        alert_boost      = result.alert_boost,
        alert_reason     = result.alert_reason,
        flood_ratio_10yr = result.flood_ratio_10yr,
        total_population = result.total_population,
        est_vulnerable   = result.est_vulnerable,
        density_per_km2  = result.density_per_km2,
        historical_events= result.historical_events,
        elevation_mean   = result.elevation_mean,
        elevation_min    = result.elevation_min,
        priority_actions = result.priority_actions,
        resource_needs   = result.resource_needs,
        baseline_fetched_at = result.baseline_fetched_at,
        baseline_age_hours  = result.baseline_age_hours,
    )


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/", response_model=HealthResponse, tags=["System"])
def health_check():
    """Health check."""
    return HealthResponse(
        status    = "ok",
        timestamp = datetime.now(timezone.utc).isoformat(),
        version   = "0.4.0",
        demo_mode = os.getenv("DEMO_MODE", "false").lower() == "true",
    )


@app.get("/cities", tags=["System"])
def list_cities(q: str = Query("", description="Saring nama, provinsi, atau kode")):
    """Semua kabupaten/kota dari katalog wilayah Kemendagri."""
    from engine.wilayah import list_kabupaten
    rows = list_kabupaten(q)
    return {"count": len(rows), "cities": rows}


@app.get("/cities/search", tags=["System"])
def search_cities(
    q:     str = Query(..., min_length=2, description="Nama kota atau provinsi"),
    limit: int = Query(10, ge=1, le=50, description="Jumlah hasil maksimum"),
):
    """Cari kab/kota di katalog wilayah. Id hasil adalah kode Kemendagri."""
    from engine.wilayah import list_kabupaten
    rows = list_kabupaten(q)
    return {
        "query":        q,
        "count":        min(len(rows), limit),
        "total_cities": len(list_kabupaten()),
        "results":      rows[:limit],
    }


@app.get("/cities/{kode}", tags=["System"])
def get_city(kode: str):
    """Satu kab/kota beserta bbox. Bbox di luar daftar demo diambil dari InaRisk."""
    from engine.places import resolve_bbox
    from engine.wilayah import lookup_kab
    kab = lookup_kab(kode)
    if not kab:
        raise HTTPException(status_code=404, detail="Kab/kota tidak ditemukan")
    bbox = kab.get("bbox") or resolve_bbox(kab["kode"]) or None
    return {**kab, "bbox": bbox}


@app.get("/alerts", response_model=AlertsResponse, tags=["Data"])
def get_alerts(
    flood_only: bool = Query(True,  description="Hanya alert berpotensi banjir"),
    city:       str  = Query(None,  description="Filter per kode kab/kota, misalnya 33.74"),
):
    """
    Peringatan dini cuaca aktif dari BMKG (cache 30 menit).

    Jika `city` diisi, hanya return alert untuk provinsi kota tersebut.
    Contoh: /alerts?city=semarang → hanya alert Jawa Tengah.
    """
    try:
        from pipeline.bmkg_ingest import fetch_active_alerts
        from engine.wilayah import province_matches, province_of
        all_raw    = fetch_active_alerts(flood_only=False)
        flood_raw  = [a for a in all_raw if a.is_flood] if flood_only else all_raw

        if city:
            city_prov = province_of(city)
            if city_prov:
                flood_raw = [
                    a for a in flood_raw
                    if province_matches(a.province, city_prov)
                ]
                all_raw = [
                    a for a in all_raw
                    if province_matches(a.province, city_prov)
                ]

        summaries = [
            AlertSummary(
                id              = a.id,
                province        = a.province,
                title           = a.title,
                severity        = a.severity or "Unknown",
                kecamatan_count = len(a.kecamatan_list),
                effective       = a.effective or a.pub_date,
                expires         = a.expires or "",
                is_flood        = a.is_flood,
            )
            for a in flood_raw
        ]
        return AlertsResponse(
            fetched_at   = datetime.now(timezone.utc).isoformat(),
            total_alerts = len(all_raw),
            flood_alerts = len([a for a in all_raw if a.is_flood]),
            alerts       = summaries,
        )
    except Exception as e:
        logger.error(f"Error fetching alerts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/weather/{city}", response_model=WeatherResponse, tags=["Data"])
def get_weather(city: str):
    """
    Prakiraan cuaca 12 jam ke depan dari BMKG per kecamatan kota.

    Menghitung:
    - rainfall_12h_mm   : total curah hujan kumulatif 12 jam (mm)
    - weather_risk      : none / low / medium / high / extreme
    - boost_score       : poin tambahan ke vulnerability score (0-25)

    Data real-time dari BMKG Prakiraan Cuaca API.
    Cache 6 jam.
    """
    city = _validate_city(city)
    try:
        from pipeline.bmkg_weather import get_weather_summary
        weather = get_weather_summary(city)
        return _weather_to_response(weather)
    except Exception as e:
        logger.error(f"Error fetching weather: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/features/{city}", tags=["Data"])
def get_features(city: str):
    """
    Raw geospatial features untuk satu kota.
    Primary source: InaRisk BNPB (tidak butuh auth).
    Fallback: Earth Engine (butuh GEE auth).
    """
    city = _validate_city(city)
    try:
        from engine.baseline import ensure_baseline
        return ensure_baseline(city)["features"]
    except Exception as exc:
        logger.error(f"Baseline fitur gagal: {exc}")
        raise HTTPException(status_code=503, detail=str(exc))


@app.get("/vulnerability/{city}", response_model=VulnerabilityResponse, tags=["Analysis"])
def get_vulnerability(
    city:            str,
    with_weather:    bool = Query(True,  description="Sertakan boost dari cuaca BMKG"),
    with_alerts:     bool = Query(True,  description="Sertakan boost dari alert BMKG"),
    with_field:      bool = Query(True,  description="Sertakan boost dari laporan lapangan BPBD"),
):
    """
    Vulnerability score 0-100 dengan breakdown lengkap.

    Score = base (statis) + weather_boost + alert_boost + field_report_boost

    Skor berubah secara real-time ketika:
    - Kondisi cuaca berubah (update tiap 60 menit)
    - Alert BMKG baru masuk (update tiap 30 menit)
    - Koordinator BPBD submit laporan lapangan (langsung)
    """
    city = _validate_city(city)
    try:
        from engine.scoring import score_city
        result, _, _ = score_city(
            city,
            include_weather = with_weather,
            include_alerts  = with_alerts,
            include_field   = with_field,
        )
        return _vuln_to_response(result)
    except Exception as e:
        logger.error(f"Error calculating vulnerability: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/narasi/{city}", response_model=NarasiResponse, tags=["Analysis"])
def get_narasi(
    city:       str,
    use_gemini: bool = Query(True, description="Pakai Gemini AI (fallback ke template)"),
):
    """Narasi bahasa Indonesia dari hasil analisis."""
    city = _validate_city(city)
    try:
        from engine.narrator import generate_narasi
        from engine.scoring import score_city

        result, _, _ = score_city(city)
        output = generate_narasi(result, use_gemini=use_gemini)

        return NarasiResponse(
            city         = city,
            score        = result.score,
            category     = result.category,
            narasi       = output["narasi"],
            source       = output["source"],
            model        = output["model"],
            generated_at = datetime.now(timezone.utc).isoformat(),
        )
    except Exception as e:
        logger.error(f"Error generating narasi: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/analyze/{city}", response_model=FullAnalysisResponse, tags=["Analysis"])
def full_analysis(
    city:       str,
    use_gemini: bool = Query(True),
    flood_only: bool = Query(True),
):
    """
    Full pipeline dalam satu request:
      BMKG alerts → weather forecast → vulnerability score → narasi AI

    Ini endpoint utama yang dikonsumsi frontend dashboard.
    """
    city = _validate_city(city)
    logger.info(f"Full analysis: {city} (flood_only={flood_only})")

    try:
        from engine.narrator import generate_narasi
        from engine.scoring import score_city

        vuln_result, weather_data, rel_alerts = score_city(
            city,
            include_alerts = True,
            include_weather = True,
            include_field = True,
        )

        # 4. Generate narasi
        narasi_out  = generate_narasi(vuln_result, use_gemini=use_gemini)

        # 5. Build response
        alert_summaries = [
            AlertSummary(
                id              = a.id,
                province        = a.province,
                title           = a.title,
                severity        = a.severity or "Unknown",
                kecamatan_count = len(a.kecamatan_list),
                effective       = a.effective or a.pub_date,
                expires         = a.expires or "",
                is_flood        = a.is_flood,
            )
            for a in rel_alerts[:5]
        ]

        return FullAnalysisResponse(
            city           = city,
            analyzed_at    = datetime.now(timezone.utc).isoformat(),
            active_alerts  = alert_summaries,
            weather        = _weather_to_response(weather_data),
            vulnerability  = _vuln_to_response(vuln_result),
            narasi         = NarasiResponse(
                city         = city,
                score        = vuln_result.score,
                category     = vuln_result.category,
                narasi       = narasi_out["narasi"],
                source       = narasi_out["source"],
                model        = narasi_out["model"],
                generated_at = datetime.now(timezone.utc).isoformat(),
            ),
            is_sample_data = vuln_result.is_sample_data,
        )

    except Exception as e:
        logger.error(f"Full analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Flood Report Endpoints (BARU) ─────────────────────────────────────────────

@app.post("/flood-report", response_model=FloodReportResponse, tags=["Field Reports"])
def submit_flood_report(body: FloodReportRequest):
    """
    Submit laporan lapangan dari koordinator BPBD.

    Satu desa per laporan. Kecamatan diisi dari kode wilayah.
    Laporan menaikkan skor kota dan menandai kecamatan induk di peta.

    flood_level: "normal" | "waspada" | "siaga" | "awas"
    """
    city = _validate_city(body.city)
    from engine.flood_report import add_report
    from engine.wilayah import VillageNotInCity
    try:
        report = add_report(
            city        = city,
            reporter    = body.reporter,
            desa_kode   = body.desa_kode,
            flood_level = body.flood_level,
            notes       = body.notes,
        )
        return FloodReportResponse(**report)
    except VillageNotInCity as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error submitting flood report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/flood-reports/{city}", response_model=FloodReportsListResponse, tags=["Field Reports"])
def get_flood_reports(city: str, limit: int = Query(10, ge=1, le=50)):
    """
    Ambil laporan lapangan terbaru untuk satu kota.
    Hanya laporan dalam 12 jam terakhir yang dihitung untuk boost score.
    """
    city = _validate_city(city)
    try:
        from engine.flood_report import get_kecamatan_boosts, get_latest_boost, get_reports

        reports = get_reports(city, limit=limit)
        boost   = get_latest_boost(city)

        return FloodReportsListResponse(
            city              = city,
            report_count      = len(reports),
            latest_boost      = boost["boost_score"],
            boost_reason      = boost["reason"],
            reports           = [FloodReportResponse(**r) for r in reports],
            kecamatan_boosts  = get_kecamatan_boosts(city),
        )
    except Exception as e:
        logger.error(f"Error getting flood reports: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/flood-villages/{city}", response_model=FloodVillagesResponse, tags=["Field Reports"])
def get_flood_villages(city: str):
    """Desa/kelurahan kota ini, dikelompokkan per kecamatan."""
    city = _validate_city(city)
    from engine.wilayah import get_villages
    return FloodVillagesResponse(city=city, groups=get_villages(city))


@app.delete("/flood-reports/{city}", tags=["Field Reports"])
def clear_flood_reports(city: str):
    """
    Hapus semua laporan lapangan untuk satu kota.
    Berguna untuk reset demo setelah presentasi.
    """
    city = _validate_city(city)
    try:
        from engine.flood_report import clear_reports
        count = clear_reports(city)
        return {"city": city, "cleared": count, "message": f"Berhasil menghapus {count} laporan"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Flood Polygon Endpoints (BARU) ────────────────────────────────────────────

@app.get("/flood-polygons/{city}", tags=["Map Data"])
def get_flood_polygons(city: str, force: bool = Query(False)):
    """
    Polygon batas kecamatan + Indeks Bahaya Banjir dari InaRisk BNPB.

    Menggantikan rectangular mock zones di frontend dengan polygon
    kecamatan yang akurat + nilai bahaya riil dari BNPB.

    Format: GeoJSON FeatureCollection (standard [lon,lat])
    Properties per feature: name, kab, prov, hazard (0-1), risk, color

    Note: Request pertama mungkin lambat (~20-30s) karena query ke InaRisk.
          Hasil di-cache 7 hari.
    """
    city = _validate_city(city)
    try:
        from engine.baseline import get_polygons
        return get_polygons(city, force=force)
    except Exception as e:
        logger.error(f"Error fetching flood polygons: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"InaRisk polygon service tidak tersedia: {str(e)}"
        )


# ── Vulnerability Map (per-kecamatan) ─────────────────────────────────────────

@app.get("/vulnerability-map/{city}", tags=["Map Data"])
def get_vulnerability_map(city: str):
    """
    GeoJSON polygon kecamatan dengan vulnerability score per kecamatan.
    Response di-cache 10 menit agar cepat dan tidak timeout di frontend.
    """
    city = _validate_city(city)

    # ── Cache check (10 menit) ────────────────────────────────────────────────
    import hashlib, time
    from pathlib import Path
    _cache_dir = Path("data/cache")
    _cache_file = _cache_dir / f"vuln_map_{city}.json"
    _CACHE_TTL = 600  # 10 menit

    if _cache_file.exists():
        age = time.time() - _cache_file.stat().st_mtime
        if age < _CACHE_TTL:
            import json as _json
            with open(_cache_file, encoding="utf-8") as f:
                cached = _json.load(f)
            logger.debug(f"  vuln_map cache hit: {city} (age {age:.0f}s)")
            return cached

    try:
        from pipeline.inarisk_polygon import get_flood_polygons as _get_polygons
        from engine.vulnerability     import (
            calculate_from_cache_or_ee, WEIGHTS, NORM, SCORE_CATEGORIES
        )

        # ── 1. Ambil city-level vulnerability (dengan semua boosts) ───────────
        city_result = calculate_from_cache_or_ee(
            city,
            include_weather=True,
            include_alerts=True,
        )

        city_base         = city_result.score - city_result.weather_boost - city_result.alert_boost
        city_hazard_contrib = round(city_result.hazard_score * WEIGHTS["hazard"] * 100, 2)
        non_hazard_base   = max(0, city_base - city_hazard_contrib)
        weather_boost     = city_result.weather_boost
        alert_boost       = city_result.alert_boost

        # ── 2. Ambil polygon kecamatan (cache 7 hari) ──────────────────────────
        polygons = _get_polygons(city)

        # ── 3. Hitung score per kecamatan ──────────────────────────────────────
        def _kec_score(hazard_val: float) -> float:
            # Hazard component untuk kecamatan ini — max 30 poin (weight 30%)
            kec_hazard = min(30.0, (hazard_val / NORM["flood_ratio_max"]) * WEIGHTS["hazard"] * 100)
            raw = non_hazard_base + kec_hazard + weather_boost + alert_boost
            return round(min(100.0, max(0.0, raw)), 1)

        def _kec_category(score: float) -> tuple[str, str]:
            for (lo, hi), (cat, _) in SCORE_CATEGORIES.items():
                if lo <= score < hi:
                    return cat, cat
            return "🔴 AWAS", "🔴 AWAS"

        VULN_COLORS = {
            "🟢 NORMAL":  "#22c55e",
            "🟡 WASPADA": "#eab308",
            "🟠 SIAGA":   "#f97316",
            "🔴 AWAS":    "#dc2626",
        }

        city_pop      = city_result.total_population
        n_features    = len(polygons.get("features", []))
        pop_per_kec   = round(city_pop / n_features) if n_features > 0 else 0

        enriched_features = []
        for feat in polygons.get("features", []):
            props      = dict(feat.get("properties", {}))
            hazard_val = props.get("hazard", 0.0)
            vs         = _kec_score(hazard_val)
            cat, _     = _kec_category(vs)

            # Estimasi populasi terdampak proporsional dengan hazard
            pop_factor = 0.5 + hazard_val * 0.5   # 50%–100% dari rata-rata populasi kecamatan
            pop_est    = round(pop_per_kec * pop_factor)

            props["vuln_score"]     = vs
            props["vuln_category"]  = cat
            props["vuln_color"]     = VULN_COLORS.get(cat, "#6b7280")
            props["population_est"] = pop_est

            enriched_features.append({
                "type":       feat["type"],
                "geometry":   feat["geometry"],
                "properties": props,
            })

        # Sort by vuln_score descending (highest risk pertama)
        enriched_features.sort(
            key=lambda f: f["properties"]["vuln_score"], reverse=True
        )

        result = {
            "type":     "FeatureCollection",
            "city":     city,
            "city_score": city_result.score,
            "city_category": city_result.category,
            "weather_boost": weather_boost,
            "alert_boost":   alert_boost,
            "features": enriched_features,
            "_source":  "InaRisk BNPB + SIGAP vulnerability engine",
            "_generated_at": datetime.now(timezone.utc).isoformat(),
        }

        # ── Simpan ke cache ───────────────────────────────────────────────────
        import json as _json
        _cache_dir.mkdir(parents=True, exist_ok=True)
        with open(_cache_file, "w", encoding="utf-8") as f:
            _json.dump(result, f, ensure_ascii=False)

        return result

    except Exception as e:
        logger.error(f"Error computing vulnerability map: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/internal/refresh-baselines", tags=["System"])
def refresh_baselines(
    limit: int = Query(5, ge=1, le=20),
    token: str = Query(""),
):
    """
    Refresh baseline InaRisk yang lebih tua dari 7 hari.
    Cloud Scheduler memanggil endpoint ini dengan REFRESH_TOKEN.
    """
    expected = os.getenv("REFRESH_TOKEN", "")
    if not expected or token != expected:
        raise HTTPException(status_code=401, detail="Token refresh tidak valid")
    from engine.baseline import refresh_stale
    return refresh_stale(limit=limit)
