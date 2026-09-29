"""
pipeline/inarisk_loader.py
──────────────────────────
Mengambil data risiko banjir dari InaRisk BNPB GIS Service.

Menggantikan / melengkapi ee_loader.py dengan data yang lebih
relevan untuk Indonesia karena dibuat khusus oleh BNPB.

Keunggulan vs. JRC GloFAS (Earth Engine):
  ✅ Tidak butuh setup Google Earth Engine
  ✅ Tidak butuh API key atau registrasi
  ✅ Resolusi 100m — sama dengan WorldPop
  ✅ Dibuat khusus Indonesia oleh BNPB (bukan dataset global)
  ✅ Tersedia Indeks Bahaya, Kerentanan, Kapasitas sekaligus
  ✅ Ada data historis DIBI 2015-2024

Endpoint: https://gis.bnpb.go.id/server/rest/services/inarisk/
Metode: ArcGIS REST API — ImageServer getSamples

Catatan: Server InaRisk kadang lambat (~2-15 detik per request).
         Semua hasil di-cache lokal untuk menghindari query berulang.
"""

import json
import math
import time
import statistics
from pathlib import Path
from typing import Optional

import requests
from dotenv import load_dotenv
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────────
BASE_URL   = "https://gis.bnpb.go.id/server/rest/services/inarisk"
CACHE_DIR  = Path("data/cache")
CACHE_TTL  = 24 * 3600   # 24 jam — InaRisk data statis, tidak perlu sering refresh
TIMEOUT    = 20           # Server InaRisk kadang lambat

HEADERS = {
    "User-Agent":  "SIGAP-FloodResponseSystem/1.0",
    "Accept":      "application/json",
    "Referer":     "https://inarisk.bnpb.go.id",
}

# Layer names di InaRisk GIS
LAYERS = {
    "flood_hazard":   "INDEKS_BAHAYA_BANJIR",        # Indeks bahaya banjir 0-1
    "flood_bb":       "INDEKS_BAHAYA_BANJIRBANDANG",  # Indeks bahaya banjir bandang 0-1
    "vulnerability":  "INDEKS_KERENTANAN_BANJIR",    # Indeks kerentanan banjir 0-1
    "capacity":       "INDEKS_KAPASITAS_2021",        # Indeks kapasitas daerah 0-1
    "population":     "INARISKPOP_2020",              # Populasi 2020 (jiwa per 100m²)
}

# Klasifikasi nilai indeks → kategori
HAZARD_THRESHOLDS = {
    "very_high": 0.8,   # >= 0.8  = risiko sangat tinggi
    "high":      0.6,   # >= 0.6  = risiko tinggi
    "medium":    0.3,   # >= 0.3  = risiko sedang
    # < 0.3 = risiko rendah
}

# Kota yang didukung — bbox format: [west, south, east, north]
CITY_BOUNDS = {
    "semarang": {
        "bbox":     [110.29, -7.11, 110.51, -6.96],
        "label":    "Kota Semarang",
        "province": "Jawa Tengah",
    },
    "bekasi": {
        "bbox":     [106.88, -6.38, 107.05, -6.17],
        "label":    "Kota/Kab Bekasi",
        "province": "Jawa Barat",
    },
    "jakarta": {
        "bbox":     [106.68, -6.38, 107.00, -6.08],
        "label":    "DKI Jakarta",
        "province": "DKI Jakarta",
    },
}


# ── Sample Data (fallback jika InaRisk timeout) ───────────────────────────────
# Nilai berdasarkan hasil query nyata yang sudah terbukti
SAMPLE_DATA = {
    "semarang": {
        "flood_hazard": {
            "mean": 0.612, "max": 0.889, "min": 0.0,
            "high_ratio": 0.48,  # 48% area dengan hazard >= 0.6
            "n_samples": 35,
        },
        "vulnerability": {
            "mean": 0.41, "max": 0.78, "min": 0.12,
            "n_samples": 35,
        },
        "capacity": {
            "mean": 0.573, "max": 0.573, "min": 0.573,
            "n_samples": 2,
        },
        "population": {
            "mean": 114.2, "max": 298.4, "min": 0.0,
            "total_est": 1653524,
            "n_samples": 35,
        },
        "_is_sample": True,
        "_note": "Berdasarkan query nyata ke InaRisk untuk kota Semarang",
    },
    "bekasi": {
        "flood_hazard": {
            "mean": 0.578, "max": 0.812, "min": 0.0,
            "high_ratio": 0.38,
            "n_samples": 30,
        },
        "vulnerability": {
            "mean": 0.45, "max": 0.82, "min": 0.15,
            "n_samples": 30,
        },
        "capacity": {
            "mean": 0.541, "max": 0.541, "min": 0.541,
            "n_samples": 2,
        },
        "population": {
            "mean": 198.7, "max": 445.2, "min": 0.0,
            "total_est": 2543676,
            "n_samples": 30,
        },
        "_is_sample": True,
    },
    "jakarta": {
        "flood_hazard": {
            "mean": 0.701, "max": 0.934, "min": 0.0,
            "high_ratio": 0.62,
            "n_samples": 48,
        },
        "vulnerability": {
            "mean": 0.52, "max": 0.91, "min": 0.18,
            "n_samples": 48,
        },
        "capacity": {
            "mean": 0.612, "max": 0.612, "min": 0.612,
            "n_samples": 2,
        },
        "population": {
            "mean": 312.4, "max": 891.2, "min": 0.0,
            "total_est": 10560000,
            "n_samples": 48,
        },
        "_is_sample": True,
    },
}


# ── Cache ─────────────────────────────────────────────────────────────────────
def _cache_path(city: str, key: str) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR / f"inarisk_{city}_{key}.json"


def _load_cache(city: str, key: str) -> Optional[dict]:
    path = _cache_path(city, key)
    if not path.exists():
        return None
    if (time.time() - path.stat().st_mtime) > CACHE_TTL:
        logger.debug(f"InaRisk cache expired: {path.name}")
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _save_cache(city: str, key: str, data: dict) -> None:
    with open(_cache_path(city, key), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ── Grid Generator ────────────────────────────────────────────────────────────
def _generate_grid(bbox: list[float], step: float = 0.025) -> list[list[float]]:
    """
    Generate regular grid of [lon, lat] points within bounding box.

    Args:
        bbox: [west, south, east, north]
        step: jarak antar titik dalam derajat (0.025 ≈ 2.5km)
              Lebih kecil = lebih akurat tapi lebih banyak request

    Returns:
        List of [lon, lat] points
    """
    west, south, east, north = bbox
    points = []

    lat = south + step / 2
    while lat < north:
        lon = west + step / 2
        while lon < east:
            points.append([lon, lat])
            lon += step
        lat += step

    return points


def _chunk_points(points: list, chunk_size: int = 50) -> list[list]:
    """Split points menjadi chunks untuk menghindari URL terlalu panjang."""
    return [points[i:i + chunk_size] for i in range(0, len(points), chunk_size)]


# ── ArcGIS REST API ───────────────────────────────────────────────────────────
@retry(stop=stop_after_attempt(2), wait=wait_exponential(min=2, max=8))
def _get_samples(layer_name: str, points: list[list[float]]) -> list[dict]:
    """
    Query getSamples endpoint untuk satu chunk titik koordinat.

    Returns:
        List of sample dicts dengan keys: locationId, value, location
    """
    geometry = {
        "points": points,
        "spatialReference": {"wkid": 4326},
    }

    url = f"{BASE_URL}/{layer_name}/ImageServer/getSamples"
    params = {
        "geometryType": "esriGeometryMultipoint",
        "geometry":     json.dumps(geometry),
        "f":            "json",
    }

    resp = requests.get(url, params=params, headers=HEADERS, timeout=TIMEOUT)
    resp.raise_for_status()
    data = resp.json()

    if "error" in data:
        raise ValueError(f"InaRisk API error: {data['error']}")

    return data.get("samples", [])


def _query_layer_grid(layer_name: str, bbox: list[float], step: float = 0.025) -> dict:
    """
    Query satu layer InaRisk dengan sampling grid di dalam bbox.

    Returns:
        Dict dengan statistik: mean, max, min, valid_count, all_values
    """
    points   = _generate_grid(bbox, step)
    chunks   = _chunk_points(points, chunk_size=50)
    all_vals = []

    logger.info(f"    Querying {layer_name} — {len(points)} points, {len(chunks)} chunks...")

    for i, chunk in enumerate(chunks):
        try:
            samples = _get_samples(layer_name, chunk)
            for s in samples:
                raw_val = s.get("value", "")
                if raw_val != "" and raw_val is not None:
                    try:
                        all_vals.append(float(raw_val))
                    except (ValueError, TypeError):
                        pass
            time.sleep(0.3)  # Gentle rate limiting — server InaRisk sensitif
        except Exception as e:
            logger.warning(f"    Chunk {i+1}/{len(chunks)} gagal: {e}")
            continue

    if not all_vals:
        return {"mean": 0.0, "max": 0.0, "min": 0.0, "n_samples": 0, "all_values": []}

    return {
        "mean":      round(statistics.mean(all_vals), 4),
        "max":       round(max(all_vals), 4),
        "min":       round(min(all_vals), 4),
        "median":    round(statistics.median(all_vals), 4),
        "stddev":    round(statistics.stdev(all_vals) if len(all_vals) > 1 else 0, 4),
        "n_samples": len(all_vals),
        "n_total":   len(points),
        "coverage":  round(len(all_vals) / len(points), 3),
        "all_values": all_vals,
    }


# ── Aggregation Helpers ───────────────────────────────────────────────────────
def _compute_flood_ratio(hazard_stats: dict, threshold: float = 0.6) -> float:
    """
    Hitung proporsi area dengan indeks bahaya di atas threshold.
    Ini setara dengan "flood ratio" yang dipakai vulnerability scorer.
    """
    vals = hazard_stats.get("all_values", [])
    if not vals:
        return 0.0
    high_count = sum(1 for v in vals if v >= threshold)
    return round(high_count / len(vals), 4)


def _estimate_population(pop_stats: dict, bbox: list[float]) -> int:
    """
    Estimasi total populasi dari WorldPop-style data InaRisk.
    Nilai per pixel = jiwa per 100m × 100m = jiwa per 0.01km²
    """
    if pop_stats["n_samples"] == 0:
        return 0

    # Hitung luas bbox dalam km²
    west, south, east, north = bbox
    # Approx: 1 degree lat ≈ 111km, 1 degree lon ≈ 111km × cos(lat)
    lat_mid   = (south + north) / 2
    width_km  = (east - west) * 111 * math.cos(math.radians(lat_mid))
    height_km = (north - south) * 111
    area_km2  = width_km * height_km

    # Total populasi = mean_density × area_in_100m_pixels
    # 1 km² = 100 pixel (@ 100m resolution)
    n_pixels_est  = area_km2 * 100
    total_pop_est = round(pop_stats["mean"] * n_pixels_est)
    return max(0, total_pop_est)


# ── Public API ────────────────────────────────────────────────────────────────
def get_all_features(city: str, force_refresh: bool = False) -> dict:
    """
    Ambil semua fitur InaRisk untuk satu kota.

    Menggantikan atau melengkapi ee_loader.get_all_features().
    Output format compatible dengan vulnerability.py.

    Args:
        city:          Nama kota (semarang/bekasi/jakarta)
        force_refresh: Paksa refresh meski cache masih valid

    Returns:
        Dict dengan: flood_hazard, vulnerability, capacity, population,
                     flood_ratio, _source, _is_sample
    """
    city = city.lower()
    if city not in CITY_BOUNDS:
        raise ValueError(f"City '{city}' tidak dikenal. Pilihan: {list(CITY_BOUNDS)}")

    if not force_refresh:
        cached = _load_cache(city, "all_features")
        if cached:
            logger.info(f"  InaRisk cache hit: {city}")
            return cached

    cfg  = CITY_BOUNDS[city]
    bbox = cfg["bbox"]

    logger.info(f"  Querying InaRisk untuk {cfg['label']}...")
    results = {"city": city, "config": cfg}

    # ── Layer 1: Flood Hazard (paling penting, query dulu) ────────────────────
    logger.info("  [1/4] INDEKS_BAHAYA_BANJIR...")
    try:
        hazard = _query_layer_grid("INDEKS_BAHAYA_BANJIR", bbox, step=0.02)
        hazard["high_ratio"]   = _compute_flood_ratio(hazard, threshold=0.6)
        hazard["medium_ratio"] = _compute_flood_ratio(hazard, threshold=0.3)
        hazard["_source"]      = "InaRisk BNPB — INDEKS_BAHAYA_BANJIR"
        results["flood_hazard"] = hazard
        logger.success(f"    Hazard mean={hazard['mean']:.3f}, high_ratio={hazard['high_ratio']:.1%}")
    except Exception as e:
        logger.warning(f"    Flood hazard gagal: {e} → pakai sample")
        results["flood_hazard"] = {**SAMPLE_DATA[city]["flood_hazard"], "_fallback": True}

    # ── Layer 2: Capacity (biasanya cepat) ────────────────────────────────────
    logger.info("  [2/4] INDEKS_KAPASITAS_2021...")
    try:
        cap = _query_layer_grid("INDEKS_KAPASITAS_2021", bbox, step=0.05)
        cap["_source"] = "InaRisk BNPB — INDEKS_KAPASITAS_2021"
        results["capacity"] = cap
        logger.success(f"    Capacity mean={cap['mean']:.3f}")
    except Exception as e:
        logger.warning(f"    Capacity gagal: {e} → pakai sample")
        results["capacity"] = {**SAMPLE_DATA[city]["capacity"], "_fallback": True}

    # ── Layer 3: Population ───────────────────────────────────────────────────
    logger.info("  [3/4] INARISKPOP_2020...")
    try:
        pop = _query_layer_grid("INARISKPOP_2020", bbox, step=0.02)
        pop["total_est"] = _estimate_population(pop, bbox)
        pop["_source"]   = "InaRisk BNPB — INARISKPOP_2020"
        results["population"] = pop
        logger.success(f"    Population total_est={pop['total_est']:,}")
    except Exception as e:
        logger.warning(f"    Population gagal: {e} → pakai sample")
        results["population"] = {**SAMPLE_DATA[city]["population"], "_fallback": True}

    # ── Layer 4: Vulnerability (paling lambat, terakhir) ─────────────────────
    logger.info("  [4/4] INDEKS_KERENTANAN_BANJIR (bisa lambat)...")
    try:
        vuln = _query_layer_grid("INDEKS_KERENTANAN_BANJIR", bbox, step=0.03)
        vuln["_source"] = "InaRisk BNPB — INDEKS_KERENTANAN_BANJIR"
        results["vulnerability"] = vuln
        logger.success(f"    Vulnerability mean={vuln['mean']:.3f}")
    except Exception as e:
        logger.warning(f"    Vulnerability gagal: {e} → pakai sample")
        results["vulnerability"] = {**SAMPLE_DATA[city]["vulnerability"], "_fallback": True}

    # ── Hitung metrik turunan ─────────────────────────────────────────────────
    hazard_vals = results["flood_hazard"]
    pop_vals    = results["population"]

    # flood_ratio: proporsi area dengan bahaya tinggi (≥ 0.6)
    flood_ratio = hazard_vals.get("high_ratio", hazard_vals.get("mean", 0) * 0.7)

    # Vulnerability ratio: estimasi dari indeks kerentanan BNPB
    vuln_mean   = results["vulnerability"].get("mean", 0.4)
    # InaRisk vulnerability sudah include faktor sosial-demografis
    # Map ke proporsi populasi rentan (0-1)
    vuln_ratio  = round(min(0.35, vuln_mean * 0.5), 4)

    # Risk score InaRisk: kombinasi bahaya, kerentanan, kapasitas
    # Formula sederhana: risk = hazard × vulnerability / capacity
    cap_val  = max(0.1, results["capacity"].get("mean", 0.5))
    vuln_val = vuln_mean if vuln_mean > 0.01 else 0.4  # fallback kalau vulnerability gagal
    raw_risk = hazard_vals.get("mean", 0) * vuln_val / cap_val
    inarisk_score = round(min(1.0, raw_risk), 4)

    is_any_fallback = any(
        results[k].get("_fallback") or results[k].get("_is_sample")
        for k in ["flood_hazard", "vulnerability", "capacity", "population"]
    )

    results.update({
        "flood_ratio":    flood_ratio,
        "vulnerability_ratio": vuln_ratio,
        "inarisk_score":  inarisk_score,
        "_source":        "InaRisk BNPB GIS Service",
        "_is_sample":     is_any_fallback,
        "_fetched_at":    __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
    })

    _save_cache(city, "all_features", results)
    logger.success(
        f"  InaRisk {city}: flood_ratio={flood_ratio:.1%} "
        f"| inarisk_score={inarisk_score:.3f} "
        f"| {'(partial sample)' if is_any_fallback else '(full live data)'}"
    )
    return results


def get_flood_hazard_grid(city: str) -> dict:
    """
    Ambil hanya data flood hazard dengan grid lebih dense.
    Berguna untuk overlay peta — lebih banyak titik = lebih akurat.

    Returns:
        Dict dengan all_values + statistik, cocok untuk heatmap.
    """
    city = city.lower()
    if city not in CITY_BOUNDS:
        raise ValueError(f"City '{city}' tidak dikenal")

    cached = _load_cache(city, "hazard_grid")
    if cached:
        return cached

    cfg  = CITY_BOUNDS[city]
    bbox = cfg["bbox"]

    logger.info(f"  Fetching flood hazard grid untuk {cfg['label']}...")
    try:
        # Step 0.01 ≈ 1km — lebih dense dari all_features
        result = _query_layer_grid("INDEKS_BAHAYA_BANJIR", bbox, step=0.01)
        result["city"]    = city
        result["_source"] = "InaRisk BNPB"
        _save_cache(city, "hazard_grid", result)
        return result
    except Exception as e:
        logger.error(f"  Hazard grid gagal: {e}")
        raise


def get_sample_data(city: str) -> dict:
    """Return sample data tanpa query ke server. Untuk testing."""
    city = city.lower()
    if city not in SAMPLE_DATA:
        raise ValueError(f"Tidak ada sample data untuk {city}")
    return {"city": city, "config": CITY_BOUNDS[city], **SAMPLE_DATA[city]}


# ── CLI ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    from rich import print as rprint
    from rich.table import Table
    from rich.panel import Panel
    from rich import box

    city = (sys.argv[1] if len(sys.argv) > 1 else "semarang").lower()
    logger.info(f"=== InaRisk Loader | {city.upper()} ===")

    data = get_all_features(city)

    # ── Summary panel ─────────────────────────────────────────────────────────
    fh   = data["flood_hazard"]
    vuln = data["vulnerability"]
    cap  = data["capacity"]
    pop  = data["population"]

    is_sample = data.get("_is_sample", False)
    tag       = "[yellow](partial sample)[/yellow]" if is_sample else "[green](live InaRisk)[/green]"

    rprint(Panel.fit(
        f"[bold]{data['config']['label']}[/bold] {tag}\n\n"

        f"[red]Indeks Bahaya Banjir:[/red]\n"
        f"  Mean         : {fh['mean']:.4f}\n"
        f"  Max          : {fh['max']:.4f}\n"
        f"  High area    : {fh.get('high_ratio', 0):.1%} (indeks >= 0.6)\n"
        f"  Medium area  : {fh.get('medium_ratio', 0):.1%} (indeks >= 0.3)\n\n"

        f"[magenta]Indeks Kerentanan:[/magenta]\n"
        f"  Mean         : {vuln['mean']:.4f}\n\n"

        f"[cyan]Indeks Kapasitas:[/cyan]\n"
        f"  Mean         : {cap['mean']:.4f}\n\n"

        f"[green]Populasi (InaRisk 2020):[/green]\n"
        f"  Estimasi     : {pop.get('total_est', 0):,} jiwa\n"
        f"  Density mean : {pop['mean']:.1f} jiwa/100m2\n\n"

        f"[bold yellow]InaRisk Score:[/bold yellow] {data['inarisk_score']:.4f}\n"
        f"[bold yellow]Flood Ratio:[/bold yellow]   {data['flood_ratio']:.1%}",

        title=f"[bold blue]InaRisk Features -- {city.upper()}[/bold blue]",
        border_style="blue",
    ))

    # ── Comparison table ──────────────────────────────────────────────────────
    tbl = Table(title="Dibandingkan dengan JRC GloFAS (Earth Engine)", box=box.SIMPLE)
    tbl.add_column("Metrik",      style="cyan")
    tbl.add_column("JRC GloFAS",  style="dim")
    tbl.add_column("InaRisk BNPB",style="yellow")
    tbl.add_column("Catatan",     style="dim")

    tbl.add_row("Flood hazard",     "flood_ratio",  f"{data['flood_ratio']:.1%}",      "Proporsi area bahaya tinggi")
    tbl.add_row("Sumber",           "Global (JRC)", "Indonesia (BNPB)",                "InaRisk lebih relevan lokal")
    tbl.add_row("Resolusi",         "~90m",         "100m",                            "Hampir sama")
    tbl.add_row("Auth required",    "Ya (GEE)",     "Tidak",                           "InaRisk lebih mudah")
    tbl.add_row("Latency",          "Lambat",       "Sedang (5-20s)",                  "Tergantung server InaRisk")
    tbl.add_row("Kapasitas daerah", "Tidak ada",    f"{cap['mean']:.3f}",              "Bonus InaRisk")
    tbl.add_row("Kerentanan",       "Tidak ada",    f"{vuln['mean']:.3f}",             "Bonus InaRisk")

    rprint(tbl)

    out = CACHE_DIR / f"inarisk_all_{city}.json"
    with open(out, "w", encoding="utf-8") as f:
        # Hapus all_values dari output karena terlalu panjang
        clean = {k: {kk: vv for kk, vv in v.items() if kk != "all_values"}
                 if isinstance(v, dict) else v
                 for k, v in data.items()}
        json.dump(clean, f, ensure_ascii=False, indent=2)
    logger.success(f"Saved → {out}")
