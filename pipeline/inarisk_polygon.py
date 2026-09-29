"""
pipeline/inarisk_polygon.py
────────────────────────────
Mengambil polygon batas kecamatan dari InaRisk BNPB dan
menggabungkannya dengan nilai Indeks Bahaya Banjir per kecamatan.

Menggantikan MOCK_FLOOD_ZONES di mockData.js yang selama ini
hanya berupa kotak-kotak persegi hardcoded.

Sumber:
  - Polygon kecamatan : batas_administrasi/MapServer/3 (Batas Kecamatan)
  - Nilai bahaya      : INDEKS_BAHAYA_BANJIR/ImageServer/getSamples

Output: GeoJSON per kota, siap di-consume Leaflet di frontend.

Cara pakai:
  python pipeline/inarisk_polygon.py semarang
  python pipeline/inarisk_polygon.py bekasi
  python pipeline/inarisk_polygon.py jakarta

Output disimpan di:
  data/cache/flood_polygons_{kota}.geojson   ← untuk Leaflet
  data/cache/flood_polygons_{kota}.json      ← backup JSON
"""

import json
import math
import time
from pathlib import Path
from typing import Optional

import requests
from dotenv import load_dotenv
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────────
BASE_GIS   = "https://gis.bnpb.go.id/server/rest/services/inarisk"
CACHE_DIR  = Path("data/cache")
CACHE_TTL  = 7 * 24 * 3600   # 7 hari — data administrasi sangat jarang berubah
TIMEOUT    = 25

HEADERS = {
    "User-Agent": "SIGAP-FloodResponseSystem/1.0",
    "Accept":     "application/json",
    "Referer":    "https://inarisk.bnpb.go.id",
}

# Batas kota [west, south, east, north] dalam WGS84
CITY_BOUNDS = {
    "semarang": [110.29, -7.11, 110.51, -6.96],
    "bekasi":   [106.88, -6.38, 107.05, -6.17],
    "jakarta":  [106.68, -6.38, 107.00, -6.08],
    "surabaya": [112.60, -7.40, 112.85, -7.15],
}

# Klasifikasi indeks bahaya → risk level (sesuai BNPB No.3/2025)
def classify_hazard(value: float) -> str:
    """Klasifikasi indeks 0-1 ke level risiko."""
    if value >= 0.8:  return "very_high"
    if value >= 0.6:  return "high"
    if value >= 0.4:  return "medium"
    if value >= 0.2:  return "low"
    return "very_low"

# Warna per level (sesuai BNPB No.3/2025)
RISK_COLORS = {
    "very_high": "#dc2626",   # Merah tua
    "high":      "#ef4444",   # Merah
    "medium":    "#f97316",   # Oranye
    "low":       "#eab308",   # Kuning
    "very_low":  "#22c55e",   # Hijau
}


# ── Cache ─────────────────────────────────────────────────────────────────────
def _cache_path(city: str, ext: str = "geojson") -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR / f"flood_polygons_{city}.{ext}"


def _load_cache(city: str) -> Optional[dict]:
    path = _cache_path(city)
    if not path.exists():
        return None
    if (time.time() - path.stat().st_mtime) > CACHE_TTL:
        logger.debug(f"Polygon cache expired: {city}")
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _save_cache(city: str, data: dict) -> None:
    # Simpan sebagai GeoJSON
    geojson_path = _cache_path(city, "geojson")
    with open(geojson_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    # Simpan juga sebagai JSON backup
    json_path = _cache_path(city, "json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    logger.success(f"  Saved polygon data: {geojson_path}")


# ── HTTP ──────────────────────────────────────────────────────────────────────
@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
def _get_json(url: str, params: dict) -> dict:
    resp = requests.get(url, params=params, headers=HEADERS, timeout=TIMEOUT)
    resp.raise_for_status()
    data = resp.json()
    if "error" in data:
        raise ValueError(f"API error: {data['error']}")
    return data


# ── Coordinate Utilities ──────────────────────────────────────────────────────
def _polygon_centroid(rings: list) -> tuple[float, float]:
    """Hitung centroid dari polygon rings (WGS84)."""
    if not rings or not rings[0]:
        return (0.0, 0.0)
    pts   = rings[0]
    xs    = [p[0] for p in pts]
    ys    = [p[1] for p in pts]
    return (sum(xs) / len(xs), sum(ys) / len(ys))


def _rings_to_geojson(rings: list) -> list:
    """
    Return rings dalam format standard GeoJSON [lon, lat].
    ArcGIS output sudah dalam [lon, lat] — tidak perlu konversi.
    Ini berbeda dari Leaflet Polygon yang pakai [lat, lon].
    """
    return rings   # [lon, lat] — standard GeoJSON


def _simplify_polygon(rings: list, tolerance: float = 0.0005) -> list:
    """
    Simplifikasi polygon dengan Douglas-Peucker sederhana.
    Mengurangi jumlah titik untuk performa Leaflet lebih baik.
    Tolerance dalam derajat (0.0005 ≈ 50 meter).
    """
    def dp_simplify(points: list, tol: float) -> list:
        if len(points) <= 2:
            return points
        # Hitung jarak titik ke garis start-end
        start, end = points[0], points[-1]
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        d  = math.sqrt(dx*dx + dy*dy)

        max_dist, max_idx = 0.0, 0
        for i in range(1, len(points) - 1):
            if d == 0:
                dist = math.sqrt((points[i][0]-start[0])**2 + (points[i][1]-start[1])**2)
            else:
                dist = abs(dx*(start[1]-points[i][1]) - dy*(start[0]-points[i][0])) / d
            if dist > max_dist:
                max_dist, max_idx = dist, i

        if max_dist > tol:
            left  = dp_simplify(points[:max_idx+1], tol)
            right = dp_simplify(points[max_idx:], tol)
            return left[:-1] + right
        return [start, end]

    return [dp_simplify(ring, tolerance) for ring in rings]


# ── Flood Hazard per Point ────────────────────────────────────────────────────
def _get_hazard_values(points: list[tuple]) -> dict[int, float]:
    """
    Query Indeks Bahaya Banjir untuk list titik koordinat.

    Args:
        points: list of (lon, lat, index) tuples

    Returns:
        dict mapping index → hazard value (0-1)
    """
    if not points:
        return {}

    geometry = {
        "points":           [[lon, lat] for lon, lat, _ in points],
        "spatialReference": {"wkid": 4326},
    }

    url    = f"{BASE_GIS}/INDEKS_BAHAYA_BANJIR/ImageServer/getSamples"
    params = {
        "geometryType": "esriGeometryMultipoint",
        "geometry":     json.dumps(geometry),
        "f":            "json",
    }

    try:
        data    = _get_json(url, params)
        samples = data.get("samples", [])
        results = {}
        for i, (_, _, orig_idx) in enumerate(points):
            if i < len(samples):
                raw = samples[i].get("value", "")
                if raw not in ("", None):
                    try:
                        results[orig_idx] = float(raw)
                    except (ValueError, TypeError):
                        results[orig_idx] = 0.0
                else:
                    results[orig_idx] = 0.0
        return results
    except Exception as e:
        logger.warning(f"  Hazard query gagal: {e}")
        return {}


# ── Main Function ─────────────────────────────────────────────────────────────
def get_flood_polygons(city: str, force_refresh: bool = False) -> dict:
    """
    Ambil polygon kecamatan dengan nilai Indeks Bahaya Banjir.

    Proses:
    1. Query batas kecamatan dari InaRisk batas_administrasi/MapServer/3
    2. Hitung centroid tiap kecamatan
    3. Query INDEKS_BAHAYA_BANJIR/ImageServer/getSamples per centroid
    4. Gabungkan polygon + nilai hazard
    5. Return GeoJSON siap untuk Leaflet

    Returns:
        GeoJSON FeatureCollection dengan properties:
          - name (str):       Nama kecamatan
          - kab (str):        Nama kabupaten/kota
          - prov (str):       Nama provinsi
          - kode_bps (str):   Kode BPS kecamatan
          - hazard (float):   Indeks bahaya 0-1
          - risk (str):       very_low/low/medium/high/very_high
          - color (str):      Hex color untuk peta
    """
    city = city.lower()
    if city not in CITY_BOUNDS:
        raise ValueError(f"City '{city}' tidak dikenal. Pilihan: {list(CITY_BOUNDS)}")

    if not force_refresh:
        cached = _load_cache(city)
        if cached:
            logger.info(f"  Polygon cache hit: {city} ({len(cached.get('features', []))} kecamatan)")
            return cached

    bbox = CITY_BOUNDS[city]
    logger.info(f"  Fetching kecamatan polygons untuk {city}...")

    # ── Step 1: Query batas kecamatan ─────────────────────────────────────────
    url_admin = f"{BASE_GIS}/batas_administrasi/MapServer/3/query"
    params_admin = {
        "geometry":      f"{bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]}",
        "geometryType":  "esriGeometryEnvelope",
        "inSR":          "4326",
        "outSR":         "4326",  # Minta hasil dalam WGS84
        "spatialRel":    "esriSpatialRelIntersects",
        "outFields":     "WADMKC,WADMKK,WADMPR,KDCBPS,OBJECTID",
        "returnGeometry":"true",
        "f":             "json",
    }

    try:
        admin_data = _get_json(url_admin, params_admin)
    except Exception as e:
        logger.error(f"  Gagal query batas kecamatan: {e}")
        raise

    features_raw = admin_data.get("features", [])
    logger.info(f"  Kecamatan ditemukan: {len(features_raw)}")

    if not features_raw:
        raise ValueError(f"Tidak ada kecamatan ditemukan untuk bbox {bbox}")

    # ── Step 2: Hitung centroid tiap kecamatan ────────────────────────────────
    kec_data = []
    centroid_points = []  # (lon, lat, index)

    for i, feat in enumerate(features_raw):
        attrs = feat.get("attributes", {})
        geom  = feat.get("geometry", {})
        rings = geom.get("rings", [])

        if not rings:
            continue

        centroid_lon, centroid_lat = _polygon_centroid(rings)
        name     = attrs.get("WADMKC", f"Kecamatan {i+1}")
        kab      = attrs.get("WADMKK", "")
        prov     = attrs.get("WADMPR", "")
        kode_bps = attrs.get("KDCBPS", "")

        kec_data.append({
            "index":    i,
            "name":     name,
            "kab":      kab,
            "prov":     prov,
            "kode_bps": kode_bps,
            "rings":    rings,
            "centroid": (centroid_lon, centroid_lat),
        })
        centroid_points.append((centroid_lon, centroid_lat, i))

    logger.info(f"  Querying hazard values untuk {len(centroid_points)} kecamatan...")

    # ── Step 3: Query hazard per centroid (dalam chunks) ─────────────────────
    CHUNK = 30
    hazard_map = {}
    for chunk_start in range(0, len(centroid_points), CHUNK):
        chunk = centroid_points[chunk_start:chunk_start + CHUNK]
        vals  = _get_hazard_values(chunk)
        hazard_map.update(vals)
        time.sleep(0.3)

    # ── Step 4: Bangun GeoJSON ────────────────────────────────────────────────
    geojson_features = []

    for kec in kec_data:
        idx     = kec["index"]
        hazard  = hazard_map.get(idx, 0.0)
        risk    = classify_hazard(hazard)
        color   = RISK_COLORS.get(risk, "#94a3b8")

        # Simplifikasi polygon untuk performa Leaflet
        simplified_rings = _simplify_polygon(kec["rings"], tolerance=0.0003)
        # Simpan dalam format standard GeoJSON [lon, lat]
        geojson_rings = _rings_to_geojson(simplified_rings)

        # Geometry type: Polygon jika 1 ring, MultiPolygon jika lebih
        if len(geojson_rings) == 1:
            geometry = {
                "type":        "Polygon",
                "coordinates": geojson_rings,
            }
        else:
            geometry = {
                "type":        "MultiPolygon",
                "coordinates": [[ring] for ring in geojson_rings],
            }

        geojson_features.append({
            "type":     "Feature",
            "geometry": geometry,
            "properties": {
                "name":     kec["name"],
                "kab":      kec["kab"],
                "prov":     kec["prov"],
                "kode_bps": kec["kode_bps"],
                "hazard":   round(hazard, 4),
                "risk":     risk,
                "color":    color,
                "centroid": list(kec["centroid"]),
            },
        })

    # Sort: tampilkan risiko tinggi lebih dulu
    risk_order = {"very_high": 0, "high": 1, "medium": 2, "low": 3, "very_low": 4}
    geojson_features.sort(
        key=lambda f: risk_order.get(f["properties"]["risk"], 5)
    )

    geojson = {
        "type":     "FeatureCollection",
        "city":     city,
        "bbox":     bbox,
        "features": geojson_features,
        "stats": {
            "total_kecamatan":  len(geojson_features),
            "very_high_count":  sum(1 for f in geojson_features if f["properties"]["risk"] == "very_high"),
            "high_count":       sum(1 for f in geojson_features if f["properties"]["risk"] == "high"),
            "medium_count":     sum(1 for f in geojson_features if f["properties"]["risk"] == "medium"),
            "low_count":        sum(1 for f in geojson_features if f["properties"]["risk"] == "low"),
            "mean_hazard":      round(sum(f["properties"]["hazard"] for f in geojson_features) / max(1, len(geojson_features)), 4),
        },
        "_source":    "InaRisk BNPB — batas_administrasi + INDEKS_BAHAYA_BANJIR",
        "_timestamp": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
    }

    _save_cache(city, geojson)
    logger.success(
        f"  Polygons {city}: {len(geojson_features)} kecamatan | "
        f"very_high={geojson['stats']['very_high_count']} | "
        f"high={geojson['stats']['high_count']} | "
        f"mean_hazard={geojson['stats']['mean_hazard']}"
    )
    return geojson


def get_polygons_as_leaflet_format(city: str) -> list[dict]:
    """
    Return polygons dalam format yang langsung kompatibel dengan
    MOCK_FLOOD_ZONES di mockData.js.

    Format output per item:
      id, name, risk, coords (leaflet format [lat,lon]), pop_est, note, hazard, color
    """
    geojson = get_flood_polygons(city)
    result  = []

    for feat in geojson["features"]:
        props = feat["properties"]
        geom  = feat["geometry"]

        # Ambil ring pertama sebagai coords
        if geom["type"] == "Polygon":
            coords = geom["coordinates"][0]  # Sudah format [lat, lon]
        else:
            coords = geom["coordinates"][0][0]

        result.append({
            "id":     f"{city}_{props['kode_bps'] or props['name'].lower().replace(' ', '_')}",
            "name":   props["name"],
            "kab":    props["kab"],
            "risk":   props["risk"],
            "hazard": props["hazard"],
            "color":  props["color"],
            "coords": coords[:20],  # Batasi titik untuk performa (simplified)
            "note":   f"InaRisk: indeks bahaya {props['hazard']:.3f}",
        })

    return result


# ── CLI ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    from rich import print as rprint
    from rich.table import Table
    from rich import box

    city = (sys.argv[1] if len(sys.argv) > 1 else "semarang").lower()
    force = "--force" in sys.argv

    logger.info(f"=== InaRisk Polygon Loader | {city.upper()} ===")

    geojson = get_flood_polygons(city, force_refresh=force)
    stats   = geojson["stats"]

    tbl = Table(
        title=f"Kecamatan Bahaya Banjir -- {city.upper()} ({stats['total_kecamatan']} kecamatan)",
        box=box.ROUNDED
    )
    tbl.add_column("Kecamatan",     style="cyan",   min_width=20)
    tbl.add_column("Kab/Kota",      style="dim")
    tbl.add_column("Hazard Index",  justify="right")
    tbl.add_column("Risk Level",    justify="center")

    risk_emoji = {
        "very_high": "[red]SANGAT TINGGI[/red]",
        "high":      "[orange3]TINGGI[/orange3]",
        "medium":    "[yellow]SEDANG[/yellow]",
        "low":       "[cyan]RENDAH[/cyan]",
        "very_low":  "[green]SANGAT RENDAH[/green]",
    }

    for feat in geojson["features"][:25]:  # Max 25 rows
        p = feat["properties"]
        tbl.add_row(
            p["name"],
            p["kab"],
            f"{p['hazard']:.4f}",
            risk_emoji.get(p["risk"], p["risk"]),
        )

    rprint(tbl)

    rprint(f"\n[bold]Statistik:[/bold]")
    rprint(f"  Sangat tinggi : {stats['very_high_count']} kecamatan")
    rprint(f"  Tinggi        : {stats['high_count']} kecamatan")
    rprint(f"  Sedang        : {stats['medium_count']} kecamatan")
    rprint(f"  Rendah        : {stats['low_count']} kecamatan")
    rprint(f"  Mean hazard   : {stats['mean_hazard']:.4f}")
    rprint(f"\n[dim]GeoJSON: data/cache/flood_polygons_{city}.geojson[/dim]")
