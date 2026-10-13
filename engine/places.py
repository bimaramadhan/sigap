"""
engine/places.py
────────────────
Bounding box kab/kota. Kota demo punya bbox tetap. Kota lain diambil
dari batas kabupaten InaRisk. Kode yang dipakai adalah kode bertitik
Kemendagri, sama dengan kolom KDPKAB (11.05, bukan 1105).
"""

import math
import re

import requests
from loguru import logger

# [west, south, east, north]
KNOWN_BBOX: dict[str, list[float]] = {
    "33.74": [110.29, -7.11, 110.51, -6.96],
    "32.75": [106.88, -6.38, 107.05, -6.17],
    "35.78": [112.60, -7.40, 112.85, -7.15],
    "31.71": [106.78, -6.23, 106.87, -6.12],
    "31.72": [106.73, -6.17, 106.97, -6.07],
    "31.73": [106.69, -6.28, 106.84, -6.10],
    "31.74": [106.77, -6.34, 106.93, -6.20],
    "31.75": [106.85, -6.34, 107.00, -6.16],
}

_KAB_LAYER = (
    "https://gis.bnpb.go.id/server/rest/services/inarisk/"
    "batas_administrasi/MapServer/2/query"
)
_bbox_cache: dict[str, list[float]] = {}


def known_bbox(kab_kode: str) -> list[float] | None:
    bbox = KNOWN_BBOX.get(kab_kode) or _bbox_cache.get(kab_kode)
    if not bbox:
        return None
    return list(bbox)


def _finite_bbox(extent: dict) -> list[float]:
    try:
        west = float(extent["xmin"])
        south = float(extent["ymin"])
        east = float(extent["xmax"])
        north = float(extent["ymax"])
    except (KeyError, TypeError, ValueError):
        return []
    if not all(math.isfinite(value) for value in (west, south, east, north)):
        return []
    if east <= west or north <= south:
        return []
    return [round(west, 4), round(south, 4), round(east, 4), round(north, 4)]


def _bbox_from_inarisk(kab_kode: str) -> list[float]:
    """Extent satu kab/kota. KDPKAB di InaRisk memakai kode bertitik."""
    if not re.fullmatch(r"\d+\.\d+", kab_kode):
        return []
    try:
        resp = requests.get(
            _KAB_LAYER,
            params={
                "where": f"KDPKAB='{kab_kode}'",
                "returnExtentOnly": "true",
                "outSR": "4326",
                "f": "json",
            },
            headers={
                "User-Agent": "SIGAP-FloodResponseSystem/1.0",
                "Referer": "https://inarisk.bnpb.go.id",
            },
            timeout=20,
        )
        resp.raise_for_status()
        return _finite_bbox(resp.json().get("extent") or {})
    except Exception as exc:
        logger.warning(f"Gagal mengambil bbox {kab_kode}: {exc}")
        return []


def resolve_bbox(kab_kode: str) -> list[float]:
    """Bbox WGS84 untuk satu kab/kota. Daftar kosong jika geometri tidak ada."""
    from engine.wilayah_geo import bbox_of
    local = bbox_of(kab_kode)
    if local:
        return local

    cached = known_bbox(kab_kode)
    if cached:
        return cached

    bbox = _bbox_from_inarisk(kab_kode)
    if bbox:
        _bbox_cache[kab_kode] = bbox
        logger.info(f"bbox {kab_kode}: {bbox}")
        return bbox

    logger.warning(f"Tidak ada bbox untuk {kab_kode}")
    return []
