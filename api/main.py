"""
api/main.py
───────────
FastAPI backend untuk SIGAP POC.

Endpoints:
  GET  /                          Health check
  GET  /cities                    List kota yang didukung
  GET  /alerts                    BMKG alerts aktif (flood-relevant)
  GET  /weather/{city}            Prakiraan cuaca + rainfall 12 jam [BARU]
  GET  /features/{city}           Raw EE geospatial features
  GET  /vulnerability/{city}      Vulnerability score + weather boost
  GET  /narasi/{city}             Narasi bahasa Indonesia
  GET  /analyze/{city}            Full pipeline: alert + weather + score + narasi

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
    version     = "0.2.0",
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
):
    """
    Vulnerability score 0-100 dengan breakdown lengkap.

    Score = base (statis) + weather_boost (dinamis) + alert_boost (dinamis)

    Skor akan BERBEDA antara hari cerah dan hari hujan lebat.
    """
    city = _validate_city(city)
    try:
        from engine.vulnerability import calculate_from_cache_or_ee
        result = calculate_from_cache_or_ee(
            city,
            include_weather = with_weather,
            include_alerts  = with_alerts,
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
