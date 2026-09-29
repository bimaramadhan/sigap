"""
pipeline/city_registry.py
──────────────────────────
Registry semua kabupaten/kota di Indonesia dari InaRisk BNPB.

Mengambil data dari batas_administrasi/MapServer/2 (Batas Kabupaten)
dan menyimpan sebagai JSON lokal: data/registry/cities.json

Data per kota:
  - label      : Nama resmi (e.g., "Kota Semarang")
  - province   : Provinsi (e.g., "Jawa Tengah")
  - kode_bps   : Kode BPS (e.g., "3374")
  - bbox       : [west, south, east, north] dalam WGS84

Fitur:
  - build_registry()    : Ambil semua 514 kota dari InaRisk, simpan ke cache
  - get_registry()      : Load registry (dari cache atau build jika belum ada)
  - search_cities(q)    : Cari kota berdasarkan nama / provinsi
  - lookup_city(name)   : Ambil data satu kota spesifik
  - normalize_key(name) : Normalisasi nama untuk key dict

TIDAK mengubah kode yang sudah ada — ini additive only.
Kode yang sudah ada (CITY_BOUNDS hardcoded) tetap berjalan.

Cara pakai:
  python pipeline/city_registry.py --build     # Build registry sekali
  python pipeline/city_registry.py --search "bandung"
  python pipeline/city_registry.py --info      # Statistik registry
"""

import json
import re
import time
from pathlib import Path
from typing import Optional

import requests
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

# ── Config ────────────────────────────────────────────────────────────────────
BASE_GIS      = "https://gis.bnpb.go.id/server/rest/services/inarisk"
REGISTRY_DIR  = Path("data/registry")
REGISTRY_FILE = REGISTRY_DIR / "cities.json"
CACHE_TTL     = 30 * 24 * 3600   # 30 hari — data administrasi jarang berubah
TIMEOUT       = 30
MAX_RECORDS   = 600               # Indonesia punya ~514 kabupaten/kota

HEADERS = {
    "User-Agent": "SIGAP-FloodResponseSystem/1.0",
    "Referer":    "https://inarisk.bnpb.go.id",
}

# Layer 2 = Batas Kabupaten, Layer 3 = Batas Kecamatan
KABUPATEN_LAYER = f"{BASE_GIS}/batas_administrasi/MapServer/2"


# ── Normalisasi ───────────────────────────────────────────────────────────────
def normalize_key(name: str) -> str:
    """
    Normalisasi nama kota untuk key dict.
    'Kota Semarang' → 'kota_semarang'
    'Kab. Bandung Barat' → 'kab_bandung_barat'
    """
    s = name.lower().strip()
    s = re.sub(r'\s+', '_', s)
    s = re.sub(r'[^a-z0-9_]', '', s)
    return s


def short_key(name: str) -> str:
    """
    Short key untuk lookup cepat tanpa prefix kota/kab.
    'Kota Semarang' → 'semarang'
    'Kabupaten Bandung Barat' → 'bandung_barat'
    """
    s = name.lower().strip()
    # Hapus prefix kota/kabupaten
    for prefix in ['kota ', 'kabupaten ', 'kab. ', 'kab ']:
        if s.startswith(prefix):
            s = s[len(prefix):]
            break
    s = re.sub(r'\s+', '_', s)
    s = re.sub(r'[^a-z0-9_]', '', s)
    return s


# ── Geometry Utils ────────────────────────────────────────────────────────────
def _compute_bbox(rings: list) -> list[float]:
    """
    Hitung bounding box [west, south, east, north] dari polygon rings.
    """
    if not rings:
        return [0.0, 0.0, 0.0, 0.0]

    all_pts = [pt for ring in rings for pt in ring]
    if not all_pts:
        return [0.0, 0.0, 0.0, 0.0]

    lons = [p[0] for p in all_pts if len(p) >= 2]
    lats = [p[1] for p in all_pts if len(p) >= 2]

    if not lons or not lats:
        return [0.0, 0.0, 0.0, 0.0]

    return [
        round(min(lons), 4),
        round(min(lats), 4),
        round(max(lons), 4),
        round(max(lats), 4),
    ]


# ── HTTP ──────────────────────────────────────────────────────────────────────
@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
def _query_kabupaten_attrs() -> dict:
    """Query nama + kode semua kabupaten tanpa geometry (cepat)."""
    params = {
        "where":              "1=1",
        "outFields":          "OBJECTID,WADMKK,WADMPR,KDPKAB,KDPPUM",
        "returnGeometry":     "false",
        "resultRecordCount":  MAX_RECORDS,
        "f":                  "json",
    }
    resp = requests.get(
        f"{KABUPATEN_LAYER}/query",
        params=params,
        headers=HEADERS,
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()


@retry(stop=stop_after_attempt(2), wait=wait_exponential(min=2, max=8))
def _query_city_bbox(object_id: int) -> list[float]:
    """
    Query bbox satu kota berdasarkan OBJECTID.
    Dipanggil on-demand saat kota dipilih user.
    """
    params = {
        "where":              f"OBJECTID={object_id}",
        "outFields":          "OBJECTID",
        "returnGeometry":     "true",
        "outSR":              "4326",
        "geometryPrecision":  "4",
        "resultRecordCount":  "1",
        "f":                  "json",
    }
    resp = requests.get(
        f"{KABUPATEN_LAYER}/query",
        params=params,
        headers=HEADERS,
        timeout=25,
    )
    resp.raise_for_status()
    data     = resp.json()
    features = data.get("features", [])
    if not features:
        return [0.0, 0.0, 0.0, 0.0]
    rings = features[0].get("geometry", {}).get("rings", [])
    return _compute_bbox(rings)


# ── Build Registry ────────────────────────────────────────────────────────────
def build_registry(force: bool = False) -> dict:
    """
    Ambil semua kabupaten/kota Indonesia dari InaRisk dan simpan ke cache.

    Strategi dua tahap:
    1. Query attributes only (cepat, <5 detik) → nama + kode semua kota
    2. Bbox disimpan sebagai None → diisi on-demand saat kota dipilih

    Args:
        force: Paksa rebuild meski cache masih valid

    Returns:
        Registry dict: {short_key: {label, province, kode_bps, bbox, object_id}}
    """
    REGISTRY_DIR.mkdir(parents=True, exist_ok=True)

    # Cek cache
    if not force and REGISTRY_FILE.exists():
        age = time.time() - REGISTRY_FILE.stat().st_mtime
        if age < CACHE_TTL:
            logger.info(f"Registry cache valid ({age/3600:.1f}h old)")
            with open(REGISTRY_FILE, encoding="utf-8") as f:
                return json.load(f)

    logger.info("Building city registry dari InaRisk BNPB (attributes only)...")

    try:
        data     = _query_kabupaten_attrs()
        features = data.get("features", [])
    except Exception as e:
        logger.error(f"Query gagal: {e}")
        return {}

    if not features:
        logger.error("Tidak ada data dari InaRisk")
        return {}

    registry = {}
    for feat in features:
        attrs    = feat.get("attributes", {})
        raw_name = str(attrs.get("WADMKK", "")).strip()
        province = str(attrs.get("WADMPR", "")).strip()
        kode_bps = str(attrs.get("KDPKAB", "") or attrs.get("KDPPUM", "")).strip()
        oid      = attrs.get("OBJECTID")

        if not raw_name or raw_name.lower() in ("null", "none", ""):
            continue

        key  = normalize_key(raw_name)
        skey = short_key(raw_name)

        registry[key] = {
            "id":        skey,
            "label":     raw_name,
            "short":     skey,
            "province":  province,
            "kode_bps":  kode_bps,
            "object_id": oid,
            "bbox":      None,   # Diisi on-demand via get_city_bbox()
        }

    # Simpan ke file
    # Seed bbox untuk kota yang sudah kita ketahui (dari CITY_BOUNDS)
    KNOWN_BBOXES = {
        "kota_semarang": [110.29, -7.11, 110.51, -6.96],
        "semarang":      [110.16, -7.27, 110.80, -6.90],  # Kab Semarang
        "bekasi":        [106.88, -6.38, 107.05, -6.17],  # Kota Bekasi
        "kabupaten_bekasi": [106.84, -6.46, 107.26, -6.04],
        "jakarta_pusat": [106.78, -6.23, 106.87, -6.12],
        "jakarta_utara": [106.73, -6.17, 106.97, -6.07],
        "jakarta_barat": [106.69, -6.28, 106.84, -6.10],
        "jakarta_selatan": [106.77, -6.34, 106.93, -6.20],
        "jakarta_timur": [106.85, -6.34, 107.00, -6.16],
        "kota_surabaya": [112.60, -7.40, 112.85, -7.15],
        "kota_bandung":  [107.52, -7.01, 107.72, -6.85],
        "kota_medan":    [98.60,  -3.71, 98.84,  -3.53],
        "kota_makassar": [119.37, -5.25, 119.50, -5.08],
        "kota_yogyakarta": [110.32, -7.84, 110.43, -7.77],
    }
    for key, bbox in KNOWN_BBOXES.items():
        if key in registry and not registry[key].get("bbox"):
            registry[key]["bbox"] = bbox

    with open(REGISTRY_FILE, "w", encoding="utf-8") as f:
        json.dump(registry, f, ensure_ascii=False, indent=2)

    logger.success(
        f"Registry saved: {len(registry)} kota → {REGISTRY_FILE}"
    )
    return registry


def get_city_bbox(city_key: str) -> list[float]:
    """
    Ambil bbox satu kota dari InaRisk on-demand.
    Menyimpan hasil ke registry untuk dipakai berikutnya.
    Cache ke registry file.

    Returns:
        [west, south, east, north] atau [0,0,0,0] jika gagal
    """
    registry = get_registry()
    entry    = registry.get(city_key)
    if not entry:
        return [0.0, 0.0, 0.0, 0.0]

    # Kalau sudah ada bbox, return langsung
    if entry.get("bbox") and entry["bbox"] != [0.0, 0.0, 0.0, 0.0]:
        return entry["bbox"]

    oid = entry.get("object_id")
    if not oid:
        return [0.0, 0.0, 0.0, 0.0]

    try:
        logger.info(f"Fetching bbox untuk {entry['label']} (OID={oid})...")
        bbox = _query_city_bbox(oid)
        if bbox != [0.0, 0.0, 0.0, 0.0]:
            # Update registry
            registry[city_key]["bbox"] = bbox
            with open(REGISTRY_FILE, "w", encoding="utf-8") as f:
                json.dump(registry, f, ensure_ascii=False, indent=2)
            logger.success(f"  bbox {entry['label']}: {bbox}")
        return bbox
    except Exception as e:
        logger.warning(f"  bbox gagal untuk {entry['label']}: {e}")
        return [0.0, 0.0, 0.0, 0.0]


# ── Load Registry ─────────────────────────────────────────────────────────────
_cached_registry: Optional[dict] = None

def get_registry(auto_build: bool = True) -> dict:
    """
    Load registry dari cache. Build jika belum ada dan auto_build=True.

    Returns:
        Registry dict atau {} jika tidak tersedia.
    """
    global _cached_registry

    # In-memory cache
    if _cached_registry is not None:
        return _cached_registry

    if REGISTRY_FILE.exists():
        with open(REGISTRY_FILE, encoding="utf-8") as f:
            _cached_registry = json.load(f)
        logger.debug(f"Registry loaded: {len(_cached_registry)} cities")
        return _cached_registry

    if auto_build:
        logger.info("Registry belum ada — building dari InaRisk...")
        _cached_registry = build_registry()
        return _cached_registry

    return {}


def reload_registry() -> None:
    """Force reload dari file (buang in-memory cache)."""
    global _cached_registry
    _cached_registry = None


# ── Search ────────────────────────────────────────────────────────────────────
def search_cities(query: str, limit: int = 10) -> list[dict]:
    """
    Cari kota berdasarkan nama atau provinsi.

    Args:
        query: String pencarian, e.g. "sema", "bandung", "jawa tengah"
        limit: Jumlah hasil maksimum

    Returns:
        List dict: [{id, label, province, kode_bps, bbox}]
    """
    registry = get_registry()
    if not registry:
        return []

    q = query.lower().strip()
    if len(q) < 2:
        return []

    results = []
    for key, data in registry.items():
        label_lower    = data["label"].lower()
        province_lower = data["province"].lower()
        short_lower    = data.get("short", "").lower()

        # Prioritas: exact match > starts_with > contains
        if (q == short_lower or q == label_lower):
            score = 3
        elif (label_lower.startswith(q) or short_lower.startswith(q)):
            score = 2
        elif (q in label_lower or q in province_lower or q in short_lower):
            score = 1
        else:
            continue

        results.append({
            "score":    score,
            "id":       data.get("id", key),
            "label":    data["label"],
            "short":    data.get("short", key),
            "province": data["province"],
            "kode_bps": data["kode_bps"],
            "bbox":     data["bbox"],
        })

    # Sort: score desc, lalu label asc
    results.sort(key=lambda x: (-x["score"], x["label"]))

    # Hapus score dari output
    for r in results:
        del r["score"]

    return results[:limit]


def lookup_city(name: str) -> Optional[dict]:
    """
    Cari satu kota berdasarkan nama persis atau short key.
    Return None jika tidak ditemukan.

    Contoh: lookup_city("semarang") atau lookup_city("Kota Semarang")
    """
    registry = get_registry()
    if not registry:
        return None

    name_lower = name.lower().strip()
    key        = normalize_key(name)
    skey       = short_key(name)

    # 1. Exact key match
    if key in registry:
        return registry[key]

    # 2. Short key match
    for data in registry.values():
        if data.get("short", "") == skey or data.get("id", "") == name_lower:
            return data

    # 3. Label match (case-insensitive)
    for data in registry.values():
        if data["label"].lower() == name_lower:
            return data

    return None


def get_registry_stats() -> dict:
    """Statistik registry."""
    registry = get_registry(auto_build=False)
    if not registry:
        return {"status": "not_built", "count": 0}

    provinces = {}
    for data in registry.values():
        p = data["province"]
        provinces[p] = provinces.get(p, 0) + 1

    return {
        "status":         "ready",
        "total_cities":   len(registry),
        "total_provinces":len(provinces),
        "provinces":      dict(sorted(provinces.items())),
        "registry_file":  str(REGISTRY_FILE),
        "file_exists":    REGISTRY_FILE.exists(),
    }


# ── CLI ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    from rich import print as rprint
    from rich.table import Table
    from rich import box

    args = sys.argv[1:]

    if "--build" in args or "-b" in args:
        force = "--force" in args
        rprint("[bold]Building city registry dari InaRisk BNPB...[/bold]")
        reg = build_registry(force=force)
        rprint(f"[green]Done! {len(reg)} kota tersimpan.[/green]")

    elif "--search" in args or "-s" in args:
        idx = args.index("--search") if "--search" in args else args.index("-s")
        q   = args[idx + 1] if idx + 1 < len(args) else ""
        if not q:
            rprint("[red]Usage: python city_registry.py --search 'bandung'[/red]")
            sys.exit(1)

        results = search_cities(q, limit=20)
        if not results:
            rprint(f"[yellow]Tidak ada hasil untuk '{q}'[/yellow]")
        else:
            tbl = Table(title=f"Hasil pencarian: '{q}' ({len(results)} kota)", box=box.ROUNDED)
            tbl.add_column("ID",       style="cyan", min_width=15)
            tbl.add_column("Nama",     style="white", min_width=20)
            tbl.add_column("Provinsi", style="dim", min_width=15)
            tbl.add_column("BPS",      style="dim", justify="center")
            tbl.add_column("Bbox",     style="dim", min_width=30)

            for r in results:
                bbox     = r.get("bbox")
                bbox_str = f"[{bbox[0]:.2f},{bbox[1]:.2f}]→[{bbox[2]:.2f},{bbox[3]:.2f}]" if bbox else "(bbox on-demand)"
                tbl.add_row(r["id"], r["label"], r["province"], r.get("kode_bps",""), bbox_str)

            rprint(tbl)

    elif "--info" in args or "-i" in args:
        stats = get_registry_stats()
        if stats["status"] == "not_built":
            rprint("[yellow]Registry belum dibuild. Jalankan: python city_registry.py --build[/yellow]")
        else:
            rprint(f"[bold]Registry Status:[/bold]")
            rprint(f"  Total kota   : [cyan]{stats['total_cities']}[/cyan]")
            rprint(f"  Total provinsi: [cyan]{stats['total_provinces']}[/cyan]")
            rprint(f"  File         : [dim]{stats['registry_file']}[/dim]")
            rprint()
            tbl = Table(title="Kota per Provinsi", box=box.SIMPLE)
            tbl.add_column("Provinsi", style="cyan")
            tbl.add_column("Jumlah", justify="right", style="yellow")
            for prov, count in stats["provinces"].items():
                tbl.add_row(prov, str(count))
            rprint(tbl)

    elif "--lookup" in args or "-l" in args:
        idx  = args.index("--lookup") if "--lookup" in args else args.index("-l")
        name = args[idx + 1] if idx + 1 < len(args) else ""
        city = lookup_city(name)
        if city:
            rprint(city)
        else:
            rprint(f"[red]Kota '{name}' tidak ditemukan[/red]")

    else:
        rprint("""
[bold]City Registry — SIGAP[/bold]

Commands:
  --build, -b          Build registry dari InaRisk BNPB (~514 kota)
  --build --force      Force rebuild meski cache masih valid
  --search 'query'     Cari kota (e.g. 'bandung', 'jawa tengah')
  --lookup 'name'      Lookup satu kota persis
  --info, -i           Tampilkan statistik registry

Contoh:
  python pipeline/city_registry.py --build
  python pipeline/city_registry.py --search 'semarang'
  python pipeline/city_registry.py --lookup 'Kota Surabaya'
  python pipeline/city_registry.py --info
""")
