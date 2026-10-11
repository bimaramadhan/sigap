"""
engine/wilayah_geo.py
─────────────────────
Profil provinsi dan kab/kota dari knowledge/geografi/wilayah_level_1_2.sql.

Koordinat path dipakai hanya untuk menghitung bounding box, lalu dibuang.
Yang disimpan di memori: pusat, elevasi, zona waktu, luas, penduduk, dan bbox.
"""

import re
from pathlib import Path

from loguru import logger

SQL_PATH = Path(__file__).resolve().parents[1] / "knowledge" / "geografi" / "wilayah_level_1_2.sql"

_HEAD_RE = re.compile(
    r"\('([^']*)','((?:[^']|'')*)','((?:[^']|'')*)',\s*"
    r"(-?\d+(?:\.\d+)?),\s*(-?\d+(?:\.\d+)?),\s*"
    r"(-?\d+(?:\.\d+)?),\s*(-?\d+),\s*"
    r"(NULL|-?\d+(?:\.\d+)?),\s*(NULL|-?\d+(?:\.\d+)?),"
)
_PAIR_RE = re.compile(r"\[(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)\]")

_by_kode: dict[str, dict] = {}


def _num(value: str) -> float | None:
    if value == "NULL":
        return None
    return float(value)


def _bbox_from_line(line: str, lat: float, lng: float) -> list[float]:
    """Path menyimpan pasangan [lat, lng]."""
    lats: list[float] = []
    lngs: list[float] = []
    for lat_s, lng_s in _PAIR_RE.findall(line):
        lats.append(float(lat_s))
        lngs.append(float(lng_s))
    if not lats:
        return [
            round(lng - 0.2, 4),
            round(lat - 0.2, 4),
            round(lng + 0.2, 4),
            round(lat + 0.2, 4),
        ]
    return [
        round(min(lngs), 4),
        round(min(lats), 4),
        round(max(lngs), 4),
        round(max(lats), 4),
    ]


def _load() -> None:
    global _by_kode
    if not SQL_PATH.exists():
        logger.warning(f"wilayah_level_1_2.sql tidak ditemukan: {SQL_PATH}")
        _by_kode = {}
        return

    rows: dict[str, dict] = {}
    with SQL_PATH.open(encoding="utf-8") as handle:
        for line in handle:
            match = _HEAD_RE.search(line)
            if not match:
                continue
            kode = match.group(1)
            lat = float(match.group(4))
            lng = float(match.group(5))
            rows[kode] = {
                "kode":     kode,
                "nama":     match.group(2).replace("''", "'").strip(),
                "ibukota":  match.group(3).replace("''", "'").strip(),
                "lat":      lat,
                "lng":      lng,
                "elv":      float(match.group(6)),
                "tz":       int(match.group(7)),
                "luas":     _num(match.group(8)),
                "penduduk": _num(match.group(9)),
                "bbox":     _bbox_from_line(line, lat, lng),
            }
    _by_kode = rows
    logger.info(f"Wilayah geo loaded: {len(rows)} provinsi/kab/kota")


_load()


def get_profil(kode: str) -> dict | None:
    row = _by_kode.get((kode or "").strip())
    if not row:
        return None
    return dict(row)


def bbox_of(kode: str) -> list[float] | None:
    row = _by_kode.get((kode or "").strip())
    if not row:
        return None
    return list(row["bbox"])


def all_profil() -> list[dict]:
    return [dict(row) for row in _by_kode.values()]
