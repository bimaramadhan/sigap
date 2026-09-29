"""
pipeline/bmkg_weather.py
─────────────────────────
Fetch prakiraan cuaca per kecamatan dari BMKG Open Data API.
Menghitung rainfall kumulatif 12 jam ke depan sebagai input
dinamis untuk vulnerability scorer.

Endpoint: https://api.bmkg.go.id/publik/prakiraan-cuaca?adm4={kode}
Format  : JSON, update 2x sehari
ADM4    : Kode wilayah BPS level desa/kelurahan

Tidak butuh API key. Tidak butuh registrasi.
"""

import os
import json
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

import requests
from dotenv import load_dotenv
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

load_dotenv()

CACHE_DIR     = Path(os.getenv("CACHE_DIR", "data/cache"))
CACHE_TTL_MIN = 60  # Cache 60 menit — BMKG update 2x sehari, tidak perlu terlalu sering
BASE_URL      = "https://api.bmkg.go.id/publik/prakiraan-cuaca"

# ── ADM4 Codes per kota ────────────────────────────────────────────────────────
# Kecamatan yang dipilih: area rawan banjir + area representatif kota
# Format: kode BPS 4 level (provinsi.kabkota.kecamatan.desa)
ADM4_CODES: dict[str, list[dict]] = {
    "semarang": [
        # Area rawan banjir utama Semarang
        {"adm4": "33.74.01.1001", "kecamatan": "Semarang Tengah",  "area": "Miroto"},
        {"adm4": "33.74.02.1001", "kecamatan": "Semarang Utara",   "area": "Bandarharjo"},
        {"adm4": "33.74.12.1001", "kecamatan": "Genuk",            "area": "Genuksari"},
        {"adm4": "33.74.06.1001", "kecamatan": "Pedurungan",       "area": "Penggaron Kidul"},
        {"adm4": "33.74.16.1001", "kecamatan": "Tugu",             "area": "Mangkang Kulon"},
    ],
    "bekasi": [
        {"adm4": "32.75.01.1001", "kecamatan": "Bekasi Utara",    "area": "Harapan Jaya"},
        {"adm4": "32.75.02.1001", "kecamatan": "Bekasi Barat",    "area": "Bintara"},
        {"adm4": "32.75.03.1001", "kecamatan": "Bekasi Selatan",  "area": "Marga Jaya"},
        {"adm4": "32.75.04.1001", "kecamatan": "Bekasi Timur",    "area": "Aren Jaya"},
    ],
    "jakarta": [
        {"adm4": "31.72.01.1001", "kecamatan": "Penjaringan",     "area": "Penjaringan"},
        {"adm4": "31.73.01.1001", "kecamatan": "Cengkareng",      "area": "Cengkareng Barat"},
        {"adm4": "31.71.01.1001", "kecamatan": "Gambir",          "area": "Gambir"},
        {"adm4": "31.75.01.1001", "kecamatan": "Matraman",        "area": "Pisangan Baru"},
    ],
    "surabaya": [
        {"adm4": "35.78.04.1001", "kecamatan": "Pabean Cantikan", "area": "Nyamplungan"},
        {"adm4": "35.78.02.1001", "kecamatan": "Kenjeran",        "area": "Bulak Banteng"},
        {"adm4": "35.78.03.1001", "kecamatan": "Semampir",        "area": "Ujung"},
        {"adm4": "35.78.06.1001", "kecamatan": "Bulak",           "area": "Kedung Cowek"},
        {"adm4": "35.78.05.1001", "kecamatan": "Bubutan",         "area": "Gundih"},
    ],
}

# ── Weather Code Mapping (BMKG standard) ──────────────────────────────────────
WEATHER_CODES = {
    0:  {"label": "Cerah",              "risk": "none",    "emoji": "☀️"},
    1:  {"label": "Cerah Berawan",      "risk": "none",    "emoji": "🌤️"},
    2:  {"label": "Berawan",            "risk": "none",    "emoji": "⛅"},
    3:  {"label": "Berawan Tebal",      "risk": "low",     "emoji": "☁️"},
    60: {"label": "Hujan Lokal",        "risk": "low",     "emoji": "🌦️"},
    61: {"label": "Hujan Ringan",       "risk": "low",     "emoji": "🌧️"},
    63: {"label": "Hujan Sedang",       "risk": "medium",  "emoji": "🌧️"},
    65: {"label": "Hujan Lebat",        "risk": "high",    "emoji": "🌧️"},
    80: {"label": "Hujan Lebat + Petir","risk": "high",    "emoji": "⛈️"},
    95: {"label": "Badai Petir",        "risk": "extreme", "emoji": "⛈️"},
    97: {"label": "Badai Petir Parah",  "risk": "extreme", "emoji": "🌩️"},
}

# Rainfall 12 jam thresholds → boost ke vulnerability score
RAINFALL_THRESHOLDS = [
    (100, "extreme", 25, "Hujan sangat lebat (>100mm/12jam)"),
    (50,  "heavy",   15, "Hujan lebat (>50mm/12jam)"),
    (20,  "moderate", 8, "Hujan sedang (>20mm/12jam)"),
    (5,   "light",    3, "Hujan ringan (>5mm/12jam)"),
    (0,   "none",     0, "Tidak ada hujan signifikan"),
]


# ── Cache ─────────────────────────────────────────────────────────────────────
def _cache_path(city: str) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR / f"weather_{city}.json"


def _load_cache(city: str) -> Optional[dict]:
    path = _cache_path(city)
    if not path.exists():
        return None
    age_min = (time.time() - path.stat().st_mtime) / 60
    if age_min > CACHE_TTL_MIN:
        logger.debug(f"Weather cache expired ({age_min:.0f} min): {city}")
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _save_cache(city: str, data: dict) -> None:
    with open(_cache_path(city), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ── HTTP ──────────────────────────────────────────────────────────────────────
@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=5))
def _fetch_forecast(adm4: str) -> Optional[dict]:
    """Fetch prakiraan cuaca untuk satu kode ADM4."""
    try:
        resp = requests.get(
            BASE_URL,
            params={"adm4": adm4},
            timeout=10,
            headers={"User-Agent": "SIGAP/1.0"},
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.warning(f"  Gagal fetch weather {adm4}: {e}")
        return None


# ── Parsing ───────────────────────────────────────────────────────────────────
def _extract_next_12h(forecast_data: dict) -> list[dict]:
    """
    Ekstrak forecast entries untuk 12 jam ke depan dari response BMKG.
    BMKG return data sebagai list-of-lists (per hari, per 3-jam slot).
    """
    now_utc    = datetime.now(timezone.utc)
    cutoff_utc = now_utc + timedelta(hours=12)
    entries    = []

    raw_data = forecast_data.get("data", [])
    # raw_data bisa berupa list of dicts (masing-masing punya "cuaca")
    # atau dict tunggal dengan key "cuaca"
    if isinstance(raw_data, dict):
        raw_data = [raw_data]

    for day_block in raw_data:
        # Tiap day_block adalah dict dengan key "cuaca" berisi list of list
        cuaca_blocks = day_block.get("cuaca", []) if isinstance(day_block, dict) else []
        for time_block in cuaca_blocks:
            # time_block adalah list of forecast dicts untuk slot waktu tertentu
            items = time_block if isinstance(time_block, list) else [time_block]
            for item in items:
                dt_str = item.get("utc_datetime", "")
                if not dt_str:
                    continue
                try:
                    dt = datetime.fromisoformat(dt_str.replace(" ", "T")).replace(tzinfo=timezone.utc)
                except ValueError:
                    continue
                if now_utc <= dt <= cutoff_utc:
                    entries.append({
                        "datetime":     dt.isoformat(),
                        "local_time":   item.get("local_datetime", ""),
                        "tp":           float(item.get("tp", 0) or 0),   # presipitasi mm
                        "weather":      int(item.get("weather", 0) or 0),
                        "weather_desc": item.get("weather_desc", ""),
                        "humidity":     int(item.get("hu", 0) or 0),
                        "temp":         float(item.get("t", 27) or 27),
                        "wind_speed":   float(item.get("ws", 0) or 0),
                    })

    return sorted(entries, key=lambda x: x["datetime"])


def _calculate_rainfall_score(rainfall_12h: float) -> tuple[int, str, str]:
    """
    Hitung weather boost score dari rainfall 12 jam.
    Returns: (boost_points, severity_label, description)
    """
    for threshold, severity, boost, desc in RAINFALL_THRESHOLDS:
        if rainfall_12h >= threshold:
            return boost, severity, desc
    return 0, "none", "Tidak ada hujan"


# ── Public API ────────────────────────────────────────────────────────────────
def get_weather_summary(city: str) -> dict:
    """
    Ambil ringkasan cuaca untuk satu kota — rata-rata dari semua kecamatan.

    Returns dict dengan:
      - city, fetched_at
      - rainfall_12h_mm    : total presipitasi 12 jam ke depan (mm)
      - max_rainfall_3h    : max presipitasi dalam 1 slot 3 jam (mm)
      - worst_weather_code : kode cuaca terburuk dalam 12 jam
      - worst_weather_desc : deskripsi cuaca terburuk
      - weather_risk       : none/low/medium/high/extreme
      - boost_score        : berapa poin tambahan ke vulnerability score (0-25)
      - boost_reason       : penjelasan boost
      - kecamatan_data     : detail per kecamatan
      - is_rainy_season    : estimasi apakah musim hujan (Oktober–April)
    """
    city = city.lower()
    if city not in ADM4_CODES:
        logger.warning(f"Kota {city} tidak ada di ADM4_CODES, return default")
        return _default_weather(city)

    cached = _load_cache(city)
    if cached:
        logger.info(f"  Weather cache hit: {city}")
        return cached

    logger.info(f"  Fetching weather data untuk {city} ({len(ADM4_CODES[city])} kecamatan)...")

    kecamatan_results = []
    all_tp:      list[float] = []
    all_codes:   list[int]   = []

    for area in ADM4_CODES[city]:
        time.sleep(0.2)  # gentle rate limiting
        raw = _fetch_forecast(area["adm4"])
        if not raw:
            continue

        entries = _extract_next_12h(raw)
        if not entries:
            continue

        rainfall_12h = sum(e["tp"] for e in entries)
        max_tp_3h    = max((e["tp"] for e in entries), default=0)
        worst_code   = max(
            (e["weather"] for e in entries),
            key=lambda c: WEATHER_CODES.get(c, {}).get("risk", "none"),
            default=0,
        )
        all_tp.append(rainfall_12h)
        all_codes.append(worst_code)

        kecamatan_results.append({
            "kecamatan":    area["kecamatan"],
            "area":         area["area"],
            "adm4":         area["adm4"],
            "rainfall_12h": round(rainfall_12h, 2),
            "max_tp_3h":    round(max_tp_3h, 2),
            "worst_weather":WEATHER_CODES.get(worst_code, {}).get("label", "Unknown"),
            "entries_count":len(entries),
        })

    if not kecamatan_results:
        logger.warning(f"  Tidak ada data weather untuk {city}")
        return _default_weather(city)

    # Ambil nilai terburuk (paling konservatif untuk early warning)
    max_rainfall = max(all_tp) if all_tp else 0
    worst_code   = max(all_codes, key=lambda c: list(WEATHER_CODES).index(c)
                       if c in WEATHER_CODES else 0, default=0)

    boost, severity, boost_reason = _calculate_rainfall_score(max_rainfall)

    # Override boost jika weather code sangat buruk
    code_info = WEATHER_CODES.get(worst_code, {})
    if code_info.get("risk") == "extreme" and boost < 20:
        boost = 20
        boost_reason = f"Badai petir terdeteksi di {city.title()}"

    now = datetime.now(timezone.utc)
    is_rainy = now.month in [10, 11, 12, 1, 2, 3, 4]  # Oktober-April musim hujan

    result = {
        "city":              city,
        "fetched_at":        now.isoformat(),
        "rainfall_12h_mm":   round(max_rainfall, 2),
        "max_rainfall_3h":   round(max(all_tp) / 4 if all_tp else 0, 2),
        "worst_weather_code":worst_code,
        "worst_weather_desc":code_info.get("label", "Unknown"),
        "worst_weather_emoji":code_info.get("emoji", "🌡️"),
        "weather_risk":      severity,
        "boost_score":       boost,
        "boost_reason":      boost_reason,
        "is_rainy_season":   is_rainy,
        "kecamatan_count":   len(kecamatan_results),
        "kecamatan_data":    kecamatan_results,
        "_source":           "BMKG Prakiraan Cuaca API",
    }

    _save_cache(city, result)
    logger.success(
        f"  Weather {city}: rainfall={max_rainfall:.1f}mm/12h "
        f"| {code_info.get('label', '?')} | boost=+{boost}"
    )
    return result


def _default_weather(city: str) -> dict:
    """Return weather data default (aman) jika API tidak bisa diakses."""
    return {
        "city":               city,
        "fetched_at":         datetime.now(timezone.utc).isoformat(),
        "rainfall_12h_mm":    0.0,
        "max_rainfall_3h":    0.0,
        "worst_weather_code": 0,
        "worst_weather_desc": "Data tidak tersedia",
        "worst_weather_emoji":"❓",
        "weather_risk":       "none",
        "boost_score":        0,
        "boost_reason":       "Data cuaca tidak tersedia — gunakan baseline statis",
        "is_rainy_season":    False,
        "kecamatan_count":    0,
        "kecamatan_data":     [],
        "_source":            "default_fallback",
    }


# ── CLI ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    from rich import print as rprint
    from rich.table import Table
    from rich.panel import Panel
    from rich import box

    city = (sys.argv[1] if len(sys.argv) > 1 else "semarang").lower()
    logger.info(f"=== BMKG Weather Pipeline | {city.upper()} ===")

    result = get_weather_summary(city)

    # Summary panel
    risk_color = {
        "extreme": "red", "high": "orange3",
        "medium": "yellow", "low": "cyan", "none": "green"
    }.get(result["weather_risk"], "white")

    rprint(Panel.fit(
        f"[bold]{city.title()}[/bold]\n\n"
        f"{result['worst_weather_emoji']} [bold]{result['worst_weather_desc']}[/bold]\n\n"
        f"[cyan]Rainfall 12 jam:[/cyan] {result['rainfall_12h_mm']:.1f} mm\n"
        f"[{risk_color}]Risk level   :[/{risk_color}] [{risk_color}]{result['weather_risk'].upper()}[/{risk_color}]\n"
        f"[yellow]Score boost  :[/yellow] [yellow]+{result['boost_score']} poin[/yellow]\n"
        f"[dim]Reason       : {result['boost_reason']}[/dim]\n"
        f"[dim]Musim hujan  : {'Ya' if result['is_rainy_season'] else 'Tidak'}[/dim]",
        title="[bold blue]BMKG Weather Summary[/bold blue]",
        border_style=risk_color,
    ))

    if result["kecamatan_data"]:
        tbl = Table(title="Detail per Kecamatan", box=box.SIMPLE)
        tbl.add_column("Kecamatan",    style="cyan")
        tbl.add_column("Rainfall 12h", justify="right", style="yellow")
        tbl.add_column("Cuaca Terburuk")
        tbl.add_column("Data Points",  justify="right", style="dim")

        for kec in result["kecamatan_data"]:
            tbl.add_row(
                kec["kecamatan"],
                f"{kec['rainfall_12h']:.1f} mm",
                kec["worst_weather"],
                str(kec["entries_count"]),
            )
        rprint(tbl)

    # Save
    out = CACHE_DIR / f"weather_{city}.json"
    rprint(f"\n[dim]Saved → {out}[/dim]")
