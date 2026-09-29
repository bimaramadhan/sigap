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
  GET  /flood-rivers/{city}       Daftar sungai kritis per kota [BARU]
  DELETE /flood-reports/{city}    Hapus semua laporan (reset demo) [BARU]

Jalankan:
  uvicorn api.main:app --reload --port 8080
  Buka: http://localhost:8080/docs
"""

import os
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from loguru import logger

load_dotenv()

app = FastAPI(
    title       = "SIGAP API",
    description = "Sistem Integrasi Geospasial Aksi Penanggulangan Bencana",
    version     = "0.3.0",
    docs_url    = "/docs",
    redoc_url   = "/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

SUPPORTED_CITIES = ["semarang", "bekasi", "jakarta"]


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


# ── Flood Report Models (BARU) ────────────────────────────────────────────────

class FloodedArea(BaseModel):
    name:         str            # "RT 04 Kelurahan Semarang Utara"
    depth_cm:     int            # kedalaman genangan cm
    est_affected: int = 0        # estimasi jiwa terdampak


class FloodReportRequest(BaseModel):
    city:           str
    reporter:       str = "Koordinator BPBD"
    river_name:     str
    water_level_cm: int
    river_level:    str          # normal / waspada / siaga / awas
    flooded_areas:  list[FloodedArea] = []
    notes:          str = ""


class FloodReportResponse(BaseModel):
    id:                str
    city:              str
    reported_at:       str
    reporter:          str
    river_name:        str
    water_level_cm:    int
    river_level:       str
    river_level_label: str
    flooded_areas:     list[dict]
    notes:             str
    boost_score:       float
    boost_breakdown:   dict


class FloodReportsListResponse(BaseModel):
    city:         str
    report_count: int
    latest_boost: float
    boost_reason: str
    reports:      list[FloodReportResponse]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _validate_city(city: str) -> str:
    city = city.lower()
    if city not in SUPPORTED_CITIES:
        raise HTTPException(
            status_code=400,
            detail=f"City '{city}' tidak didukung. Pilihan: {SUPPORTED_CITIES}",
        )
    return city


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
    )


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/", response_model=HealthResponse, tags=["System"])
def health_check():
    """Health check."""
    return HealthResponse(
        status    = "ok",
        timestamp = datetime.now(timezone.utc).isoformat(),
        version   = "0.2.0",
        demo_mode = os.getenv("DEMO_MODE", "false").lower() == "true",
    )


@app.get("/cities", tags=["System"])
def list_cities():
    """List kota yang didukung."""
    from pipeline.ee_loader import CITY_BOUNDS
    return {
        "cities": [
            {"id": k, **v}
            for k, v in CITY_BOUNDS.items()
            if k in SUPPORTED_CITIES
        ]
    }


@app.get("/alerts", response_model=AlertsResponse, tags=["Data"])
def get_alerts(
    flood_only: bool = Query(True, description="Hanya alert berpotensi banjir"),
):
    """Peringatan dini cuaca aktif dari BMKG (cache 30 menit)."""
    try:
        from pipeline.bmkg_ingest import fetch_active_alerts
        alerts     = fetch_active_alerts(flood_only=flood_only)
        all_alerts = fetch_active_alerts(flood_only=False) if flood_only else alerts

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
            for a in alerts
        ]
        return AlertsResponse(
            fetched_at   = datetime.now(timezone.utc).isoformat(),
            total_alerts = len(all_alerts),
            flood_alerts = len([a for a in all_alerts if a.is_flood]),
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
    Cache 60 menit.
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
    """Raw geospatial features dari Earth Engine."""
    city = _validate_city(city)
    try:
        from pipeline.ee_loader import get_all_features
        return get_all_features(city)
    except Exception as e:
        logger.error(f"Error fetching EE features: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
        from engine.vulnerability import calculate_from_cache_or_ee
        from engine.flood_report  import get_latest_boost as get_field_boost

        result      = calculate_from_cache_or_ee(
            city,
            include_weather = with_weather,
            include_alerts  = with_alerts,
        )

        # Tambahkan field report boost jika ada laporan baru
        if with_field:
            field = get_field_boost(city)
            if field["boost_score"] > 0:
                # Inject ke result — cap total boost pada 30
                extra = min(field["boost_score"], max(0, 30 - result.weather_boost - result.alert_boost))
                result.score           = round(min(100, result.score + extra), 1)
                result.priority_actions.insert(0,
                    f"📡 Laporan lapangan: {field['boost_reason']} (+{extra:.0f} poin)"
                )
                # Update kategori
                from engine.vulnerability import _get_category
                result.category, result.category_message = _get_category(result.score)

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
        from engine.vulnerability import calculate_from_cache_or_ee
        from engine.narrator      import generate_narasi

        result = calculate_from_cache_or_ee(city)
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
    logger.info(f"Full analysis: {city}")

    try:
        from pipeline.bmkg_ingest    import fetch_active_alerts
        from pipeline.bmkg_weather   import get_weather_summary
        from pipeline.ee_loader      import get_all_features, CITY_BOUNDS
        from engine.vulnerability    import calculate
        from engine.narrator         import generate_narasi

        # 1. Fetch semua data paralel (sequential untuk simplicity)
        alerts       = fetch_active_alerts(flood_only=flood_only)
        weather_data = get_weather_summary(city)
        ee_features  = get_all_features(city)

        # 2. Filter alert relevan untuk kota ini
        city_prov  = CITY_BOUNDS.get(city, {}).get("province", "").lower()
        rel_alerts = [
            a for a in alerts
            if city_prov.split()[0] in a.province.lower()
        ] if city_prov else alerts[:5]

        # 3. Hitung vulnerability dengan weather + alert boost
        vuln_result = calculate(city, ee_features, weather_data, rel_alerts)

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

    Laporan ini langsung mempengaruhi vulnerability score kota.
    Berdasarkan Pasal 23 Peraturan BNPB No.2/2024 — BPBD wajib
    memberikan umpan balik kondisi lapangan ke sistem peringatan dini.

    river_level: "normal" | "waspada" | "siaga" | "awas"
    """
    city = _validate_city(body.city)
    try:
        from engine.flood_report import add_report

        report = add_report(
            city           = city,
            reporter       = body.reporter,
            river_name     = body.river_name,
            water_level_cm = body.water_level_cm,
            river_level    = body.river_level,
            flooded_areas  = [a.dict() for a in body.flooded_areas],
            notes          = body.notes,
        )
        return FloodReportResponse(**report)
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
        from engine.flood_report import get_reports, get_latest_boost

        reports = get_reports(city, limit=limit)
        boost   = get_latest_boost(city)

        return FloodReportsListResponse(
            city         = city,
            report_count = len(reports),
            latest_boost = boost["boost_score"],
            boost_reason = boost["reason"],
            reports      = [FloodReportResponse(**r) for r in reports],
        )
    except Exception as e:
        logger.error(f"Error getting flood reports: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/flood-rivers/{city}", tags=["Field Reports"])
def get_flood_rivers(city: str):
    """Daftar sungai kritis untuk dropdown input laporan."""
    city = _validate_city(city)
    from engine.flood_report import get_rivers
    return {"city": city, "rivers": get_rivers(city)}


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
