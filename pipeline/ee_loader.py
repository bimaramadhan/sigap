"""
pipeline/ee_loader.py
─────────────────────
Load data geospasial dari Google Earth Engine:
  1. DEM (Digital Elevation Model) — SRTM 30m
  2. Flood Hazard Map — JRC/Copernicus GloFAS
  3. Historical Flood Events — Global Flood Database
  4. Population — WorldPop 100m (PRIMARY, menggantikan BPS manual)

Fallback mode: Jika EE belum authenticated, return sample data
               sehingga pipeline tetap bisa ditest end-to-end.

Setup EE (sekali saja):
  pip install earthengine-api
  earthengine authenticate
  → Lalu isi GCP_PROJECT_ID di .env
"""

import os
import json
import time
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from loguru import logger

load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────────
GCP_PROJECT = os.getenv("GCP_PROJECT_ID", "")
CACHE_DIR   = Path(os.getenv("CACHE_DIR", "data/cache"))
CACHE_TTL   = int(os.getenv("CACHE_TTL_MINUTES", "60")) * 60  # detik
DEMO_MODE   = os.getenv("DEMO_MODE", "false").lower() == "true"

# Bounding box kota — format: [west, south, east, north]
CITY_BOUNDS: dict[str, dict] = {
    "semarang": {
        "bbox":     [110.29, -7.11, 110.51, -6.96],
        "province": "Jawa Tengah",
        "label":    "Kota Semarang",
    },
    "bekasi": {
        "bbox":     [106.88, -6.38, 107.05, -6.17],
        "province": "Jawa Barat",
        "label":    "Kota/Kab Bekasi",
    },
    "jakarta": {
        "bbox":     [106.68, -6.38, 107.00, -6.08],
        "province": "DKI Jakarta",
        "label":    "DKI Jakarta",
    },
    "surabaya": {
        "bbox":     [112.60, -7.40, 112.85, -7.15],
        "province": "Jawa Timur",
        "label":    "Kota Surabaya",
    },
}

# EE Dataset IDs
EE_DEM           = "USGS/SRTMGL1_003"
EE_FLOOD_HAZARD  = "JRC/CEMS_GLOFAS_FloodHazard_v2_1"
EE_FLOOD_HISTORY = "GLOBAL_FLOOD_DB/MODIS_EVENTS/V1"
EE_WORLDPOP      = "WorldPop/GP/100m/pop"


# ── Fallback / Sample Data ────────────────────────────────────────────────────
# Dipakai saat EE belum authenticated (DEMO_MODE=true atau EE gagal init)
# Nilai ini berdasarkan data riil Semarang dari publikasi akademik

SAMPLE_DATA: dict[str, dict] = {
    "semarang": {
        "city": "semarang",
        "config": CITY_BOUNDS["semarang"],
        "dem": {
            "city": "semarang",
            "elevation_mean": 18.4,
            "elevation_min": -2.0,   # area pesisir — di bawah permukaan laut
            "elevation_max": 348.0,
            "elevation_std": 52.3,
            "source": "SAMPLE — ganti dengan EE auth"
        },
        "flood_hazard": {
            "10yr": {
                "city": "semarang",
                "return_period_yr": 10,
                "area_km2": {"safe": 142.3, "low": 38.7, "medium": 24.1, "high": 12.9},
                "total_area_km2": 218.0,
                "flood_ratio": 0.348,
                "source": "SAMPLE"
            },
            "100yr": {
                "city": "semarang",
                "return_period_yr": 100,
                "area_km2": {"safe": 98.2, "low": 52.4, "medium": 41.6, "high": 25.8},
                "total_area_km2": 218.0,
                "flood_ratio": 0.550,
                "source": "SAMPLE"
            }
        },
        "flood_history": {
            "city": "semarang",
            "historical_events": 14,
            "period": "2000-2018",
            "avg_per_year": 0.78,
            "source": "SAMPLE — berdasarkan data BNPB Semarang"
        },
        "population": {
            "city": "semarang",
            "year": 2020,
            "total_population": 1653524,
            "area_km2": 373.8,
            "density_per_km2": 4424,
            "elderly_ratio": 0.094,    # 9.4% lansia (BPS Semarang 2020)
            "children_ratio": 0.082,   # 8.2% balita
            "vulnerability_ratio": 0.176,  # elderly + children
            "source": "SAMPLE — BPS Kota Semarang SP2020"
        },
        "_is_sample": True
    },
    "bekasi": {
        "city": "bekasi",
        "config": CITY_BOUNDS["bekasi"],
        "dem": {
            "city": "bekasi",
            "elevation_mean": 19.2,
            "elevation_min": 4.0,
            "elevation_max": 72.0,
            "elevation_std": 12.1,
            "source": "SAMPLE"
        },
        "flood_hazard": {
            "10yr": {
                "city": "bekasi",
                "return_period_yr": 10,
                "area_km2": {"safe": 168.4, "low": 42.1, "medium": 28.3, "high": 8.2},
                "total_area_km2": 247.0,
                "flood_ratio": 0.319,
                "source": "SAMPLE"
            },
            "100yr": {
                "city": "bekasi",
                "return_period_yr": 100,
                "area_km2": {"safe": 112.0, "low": 58.3, "medium": 49.1, "high": 27.6},
                "total_area_km2": 247.0,
                "flood_ratio": 0.547,
                "source": "SAMPLE"
            }
        },
        "flood_history": {
            "city": "bekasi",
            "historical_events": 18,
            "period": "2000-2018",
            "avg_per_year": 1.0,
            "source": "SAMPLE"
        },
        "population": {
            "city": "bekasi",
            "year": 2020,
            "total_population": 2543676,
            "area_km2": 210.5,
            "density_per_km2": 12083,
            "elderly_ratio": 0.062,
            "children_ratio": 0.091,
            "vulnerability_ratio": 0.153,
            "source": "SAMPLE — BPS Kota Bekasi SP2020"
        },
        "_is_sample": True
    },
}


# ── Cache Helpers ─────────────────────────────────────────────────────────────
def _cache_path(city: str, key: str) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR / f"ee_{city}_{key}.json"


def _load_cache(city: str, key: str) -> Optional[dict]:
    path = _cache_path(city, key)
    if not path.exists():
        return None
    if (time.time() - path.stat().st_mtime) > CACHE_TTL:
        logger.debug(f"Cache expired: {path.name}")
        return None
    with open(path) as f:
        return json.load(f)


def _save_cache(city: str, key: str, data: dict) -> None:
    with open(_cache_path(city, key), "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ── EE Init ───────────────────────────────────────────────────────────────────
_ee_initialized = False

def _init_ee() -> bool:
    """Coba initialize Earth Engine. Return False jika gagal (akan pakai fallback)."""
    global _ee_initialized
    if _ee_initialized:
        return True
    if DEMO_MODE:
        logger.info("DEMO_MODE=true → skip EE init, pakai sample data")
        return False
    try:
        import ee
        if GCP_PROJECT:
            ee.Initialize(project=GCP_PROJECT)
        else:
            ee.Initialize()
        _ee_initialized = True
        logger.success(f"Earth Engine initialized ✓")
        return True
    except Exception as e:
        logger.warning(f"EE init gagal: {e}")
        logger.info("→ Pakai sample data. Untuk data real: jalankan 'earthengine authenticate'")
        return False


# ── EE Query Functions ────────────────────────────────────────────────────────
def _get_dem_stats(city: str) -> dict:
    import ee
    cached = _load_cache(city, "dem")
    if cached:
        return cached

    logger.info(f"  EE: Fetching DEM untuk {city}...")
    cfg  = CITY_BOUNDS[city]
    west, south, east, north = cfg["bbox"]
    geom = ee.Geometry.Rectangle([west, south, east, north])

    stats = (
        ee.Image(EE_DEM)
        .select("elevation")
        .reduceRegion(
            reducer=ee.Reducer.mean()
                    .combine(ee.Reducer.min(), sharedInputs=True)
                    .combine(ee.Reducer.max(), sharedInputs=True)
                    .combine(ee.Reducer.stdDev(), sharedInputs=True),
            geometry=geom,
            scale=30,
            maxPixels=1e9,
        )
        .getInfo()
    )

    result = {
        "city":            city,
        "elevation_mean":  round(stats.get("elevation_mean", 0), 2),
        "elevation_min":   round(stats.get("elevation_min", 0), 2),
        "elevation_max":   round(stats.get("elevation_max", 0), 2),
        "elevation_std":   round(stats.get("elevation_stdDev", 0), 2),
        "source":          "SRTM via Google Earth Engine",
    }
    _save_cache(city, "dem", result)
    return result


def _get_flood_hazard(city: str, return_period: int = 10) -> dict:
    import ee
    cache_key = f"flood_hazard_rp{return_period}"
    cached    = _load_cache(city, cache_key)
    if cached:
        return cached

    logger.info(f"  EE: Fetching flood hazard RP={return_period}yr untuk {city}...")
    cfg  = CITY_BOUNDS[city]
    west, south, east, north = cfg["bbox"]
    geom = ee.Geometry.Rectangle([west, south, east, north])

    col        = ee.ImageCollection(EE_FLOOD_HAZARD)
    first_img  = col.first()
    band_names = first_img.bandNames().getInfo()

    # Cari band yang sesuai return period
    target_band = f"depth_{return_period}y"
    if target_band not in band_names:
        # Ambil band depth pertama yang tersedia
        depth_bands = [b for b in band_names if "depth" in b]
        target_band = depth_bands[0] if depth_bands else band_names[0]
        logger.warning(f"Band depth_{return_period}y tidak ada, pakai: {target_band}")

    depth = first_img.select(target_band)

    # Klasifikasi: 0=aman, 1=rendah(0-0.5m), 2=sedang(0.5-1.5m), 3=tinggi(>1.5m)
    classified = (
        depth.gt(1.5).multiply(3)
        .where(depth.gt(0.5).And(depth.lte(1.5)), 2)
        .where(depth.gt(0).And(depth.lte(0.5)), 1)
        .where(depth.eq(0), 0)
    )

    area_img = classified.addBands(ee.Image.pixelArea().divide(1e6))
    area_result = area_img.reduceRegion(
        reducer=ee.Reducer.sum().group(groupField=0, groupName="cls"),
        geometry=geom,
        scale=90,
        maxPixels=1e9,
    ).getInfo()

    labels    = {0: "safe", 1: "low", 2: "medium", 3: "high"}
    area_km2  = {"safe": 0.0, "low": 0.0, "medium": 0.0, "high": 0.0}
    for grp in area_result.get("groups", []):
        cls   = int(grp.get("cls", 0))
        area  = round(grp.get("sum", 0), 4)
        area_km2[labels.get(cls, "safe")] = area

    total      = sum(area_km2.values())
    flood_area = total - area_km2["safe"]

    result = {
        "city":             city,
        "return_period_yr": return_period,
        "area_km2":         area_km2,
        "total_area_km2":   round(total, 2),
        "flood_ratio":      round(flood_area / total, 4) if total > 0 else 0,
        "source":           "JRC GloFAS via Google Earth Engine",
    }
    _save_cache(city, cache_key, result)
    return result


def _get_flood_history(city: str) -> dict:
    import ee
    cached = _load_cache(city, "flood_history")
    if cached:
        return cached

    logger.info(f"  EE: Fetching flood history untuk {city}...")
    cfg  = CITY_BOUNDS[city]
    west, south, east, north = cfg["bbox"]
    geom = ee.Geometry.Rectangle([west, south, east, north])

    col = ee.ImageCollection(EE_FLOOD_HISTORY)

    # Map: cek apakah setiap event menyentuh area kota
    def has_overlap(img):
        hit = (
            img.select("flooded")
            .gt(0)
            .reduceRegion(
                reducer=ee.Reducer.anyNonZero(),
                geometry=geom,
                scale=500,
                maxPixels=1e8,
            )
            .get("flooded")
        )
        return img.set("hit", hit)

    events = col.map(has_overlap).filter(ee.Filter.eq("hit", 1))
    count  = events.size().getInfo()

    result = {
        "city":              city,
        "historical_events": count,
        "period":            "2000-2018",
        "avg_per_year":      round(count / 18, 2),
        "source":            "Global Flood Database via Google Earth Engine",
    }
    _save_cache(city, "flood_history", result)
    return result


def _get_population(city: str) -> dict:
    """
    WorldPop 100m grid — total populasi + estimasi kelompok rentan.
    WorldPop hanya punya total population, bukan breakdown umur.
    Vulnerability ratio (lansia + balita) diestimasi dari proporsi nasional BPS.
    """
    import ee
    cached = _load_cache(city, "population")
    if cached:
        return cached

    logger.info(f"  EE: Fetching WorldPop population untuk {city}...")
    cfg  = CITY_BOUNDS[city]
    west, south, east, north = cfg["bbox"]
    geom = ee.Geometry.Rectangle([west, south, east, north])

    # WorldPop: cari image Indonesia tahun terbaru
    col = (
        ee.ImageCollection(EE_WORLDPOP)
        .filter(ee.Filter.eq("country", "IDN"))
        .sort("year", False)
    )

    # Ambil image tahun terbaru yang tersedia
    pop_img  = col.first()
    year_val = pop_img.get("year").getInfo()

    pop_stats = pop_img.reduceRegion(
        reducer=ee.Reducer.sum(),
        geometry=geom,
        scale=100,
        maxPixels=1e9,
    ).getInfo()

    area_m2  = geom.area().getInfo()
    area_km2 = area_m2 / 1e6
    total    = round(pop_stats.get("population", 0))
    density  = round(total / area_km2, 1) if area_km2 > 0 else 0

    # Estimasi vulnerability ratio dari proporsi BPS nasional 2020:
    # Lansia (60+) ~9.6%, Balita (0-4) ~8.0% → combined ~17.6%
    ELDERLY_RATIO   = 0.096
    CHILDREN_RATIO  = 0.080
    vuln_ratio      = ELDERLY_RATIO + CHILDREN_RATIO

    result = {
        "city":               city,
        "year":               year_val,
        "total_population":   total,
        "area_km2":           round(area_km2, 2),
        "density_per_km2":    density,
        "elderly_ratio":      ELDERLY_RATIO,
        "children_ratio":     CHILDREN_RATIO,
        "vulnerability_ratio":vuln_ratio,
        "est_elderly":        round(total * ELDERLY_RATIO),
        "est_children":       round(total * CHILDREN_RATIO),
        "est_vulnerable":     round(total * vuln_ratio),
        "source":             f"WorldPop {year_val} via Earth Engine + BPS proporsi nasional",
    }
    _save_cache(city, "population", result)
    return result


# ── Public API ────────────────────────────────────────────────────────────────
def get_all_features(city: str) -> dict:
    """
    Entry point utama. Ambil semua fitur geospasial untuk satu kota.

    Urutan prioritas:
    1. Cache (hindari repeat EE calls)
    2. Earth Engine (jika authenticated)
    3. Sample data (jika EE gagal / DEMO_MODE=true)

    Return: dict lengkap siap dikonsumsi oleh vulnerability.py
    """
    city = city.lower()
    if city not in CITY_BOUNDS:
        raise ValueError(f"City '{city}' tidak dikenal. Pilihan: {list(CITY_BOUNDS)}")

    # Cek full cache dulu
    cached = _load_cache(city, "all_features")
    if cached:
        logger.info(f"  Cache hit: all_features_{city}")
        return cached

    ee_ok = _init_ee()

    if not ee_ok:
        # Pakai sample data
        if city in SAMPLE_DATA:
            logger.warning(f"  Pakai SAMPLE DATA untuk {city} (EE belum ready)")
            result = SAMPLE_DATA[city]
            _save_cache(city, "all_features", result)
            return result
        raise RuntimeError(f"EE tidak tersedia dan tidak ada sample data untuk {city}")

    # Fetch semua dari EE
    try:
        dem         = _get_dem_stats(city)
        flood_10yr  = _get_flood_hazard(city, 10)
        flood_100yr = _get_flood_hazard(city, 100)
        flood_hist  = _get_flood_history(city)
        population  = _get_population(city)

        result = {
            "city":          city,
            "config":        CITY_BOUNDS[city],
            "dem":           dem,
            "flood_hazard":  {"10yr": flood_10yr, "100yr": flood_100yr},
            "flood_history": flood_hist,
            "population":    population,
            "_is_sample":    False,
        }
        _save_cache(city, "all_features", result)
        logger.success(f"  Semua EE features berhasil untuk {city} ✓")
        return result

    except Exception as e:
        logger.error(f"  EE query gagal: {e}")
        logger.info("  → Fallback ke sample data")
        if city in SAMPLE_DATA:
            return SAMPLE_DATA[city]
        raise


# ── CLI ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    from rich import print as rprint
    from rich.panel import Panel

    city = (sys.argv[1] if len(sys.argv) > 1 else "semarang").lower()
    logger.info(f"=== EE Loader: {city} ===")

    data = get_all_features(city)
    pop  = data["population"]
    fh   = data["flood_hazard"]["10yr"]
    hist = data["flood_history"]
    dem  = data["dem"]

    is_sample = data.get("_is_sample", False)
    tag       = "[yellow](SAMPLE DATA)[/yellow]" if is_sample else "[green](REAL EE DATA)[/green]"

    rprint(Panel.fit(
        f"[bold]{data['config']['label']}[/bold] {tag}\n\n"
        f"[cyan]Elevasi:[/cyan] {dem['elevation_min']}m – {dem['elevation_max']}m "
        f"(avg {dem['elevation_mean']}m)\n\n"
        f"[red]Flood Hazard (10yr):[/red]\n"
        f"  Aman   : {fh['area_km2']['safe']:.1f} km²\n"
        f"  Rendah : {fh['area_km2']['low']:.1f} km²\n"
        f"  Sedang : {fh['area_km2']['medium']:.1f} km²\n"
        f"  Tinggi : {fh['area_km2']['high']:.1f} km²\n"
        f"  Flood ratio: {fh['flood_ratio']:.1%}\n\n"
        f"[magenta]Banjir Historis (2000-2018):[/magenta] "
        f"{hist['historical_events']} events ({hist['avg_per_year']}/yr)\n\n"
        f"[green]Populasi (WorldPop):[/green]\n"
        f"  Total     : {pop['total_population']:,}\n"
        f"  Kepadatan : {pop['density_per_km2']:,} jiwa/km²\n"
        f"  Est. Lansia  : {pop['est_elderly']:,} jiwa\n"
        f"  Est. Balita  : {pop['est_children']:,} jiwa\n"
        f"  Est. Rentan  : {pop['est_vulnerable']:,} jiwa ({pop['vulnerability_ratio']:.1%})",
        title="[bold blue]Earth Engine Features[/bold blue]",
        border_style="blue",
    ))
