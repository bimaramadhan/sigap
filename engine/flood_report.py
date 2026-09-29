"""
engine/flood_report.py
──────────────────────
In-memory store untuk laporan lapangan dari koordinator BPBD.

Ini menggantikan keterbatasan data live banjir yang tidak tersedia
via public API. Koordinator BPBD input langsung ke SIGAP:
  - Level sungai (TMA) saat ini
  - Area yang sudah tergenang

Data ini kemudian digunakan sebagai boost ke vulnerability score,
membuat sistem responsif terhadap kondisi aktual di lapangan.

Sesuai Pasal 23 Peraturan BNPB No.2/2024 yang mewajibkan BPBD
memberikan umpan balik kondisi lapangan ke sistem peringatan dini.
"""

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from loguru import logger

# ── Config ────────────────────────────────────────────────────────────────────
DATA_DIR   = Path("data")
STORE_FILE = DATA_DIR / "flood_reports.json"

# Boost ke vulnerability score berdasarkan level sungai
RIVER_LEVEL_BOOST = {
    "awas":    25,   # TMA di atas batas bahaya
    "siaga":   15,   # TMA di batas siaga
    "waspada":  8,   # TMA mendekati batas waspada
    "normal":   0,   # TMA normal
}

# Tambahan boost per area genangan yang dilaporkan (max 15 poin total)
FLOODED_AREA_BOOST_PER_AREA = 3
FLOODED_AREA_MAX_BOOST      = 15

# Label lengkap per level (sesuai BNPB No.2/2024)
LEVEL_LABELS = {
    "normal":   {"label": "🟢 Normal",   "color": "green"},
    "waspada":  {"label": "🟡 Waspada",  "color": "yellow"},
    "siaga":    {"label": "🟠 Siaga",    "color": "orange"},
    "awas":     {"label": "🔴 Awas",     "color": "red"},
}

# Sungai kritis per kota (untuk dropdown di frontend)
RIVERS_BY_CITY = {
    "semarang": [
        "Sungai Banjirkanal Barat",
        "Sungai Banjirkanal Timur",
        "Sungai Beringin",
        "Sungai Silandak",
        "Sungai Plumbon",
        "Kali Garang",
    ],
    "bekasi": [
        "Kali Bekasi",
        "Kali Cikeas",
        "Kali Cileungsi",
        "Kali Sunter",
        "Saluran Tarum Barat",
    ],
    "jakarta": [
        "Kali Ciliwung",
        "Kali Pesanggrahan",
        "Kali Angke",
        "Kali Sunter",
        "Banjir Kanal Barat",
        "Banjir Kanal Timur",
        "Kali Krukut",
    ],
    "surabaya": [
        "Kali Mas",
        "Kali Surabaya",
        "Kali Wonokromo",
        "Kali Kenjeran",
        "Kali Lamong",
        "Kali Kedurus",
    ],
}


# ── In-Memory Store ───────────────────────────────────────────────────────────
# Format: { "semarang": [report1, report2, ...], "bekasi": [...] }
_store: dict[str, list[dict]] = {}


def _load_from_disk() -> None:
    """Load persisted reports dari file JSON saat startup."""
    global _store
    if STORE_FILE.exists():
        try:
            with open(STORE_FILE, encoding="utf-8") as f:
                _store = json.load(f)
            total = sum(len(v) for v in _store.values())
            if total > 0:
                logger.info(f"Loaded {total} flood reports dari disk")
        except Exception as e:
            logger.warning(f"Gagal load flood reports: {e}")
            _store = {}


def _save_to_disk() -> None:
    """Persist reports ke file JSON."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(STORE_FILE, "w", encoding="utf-8") as f:
        json.dump(_store, f, ensure_ascii=False, indent=2)


# Load saat module diimport
_load_from_disk()


# ── Data Models ───────────────────────────────────────────────────────────────
def _make_report(
    city:            str,
    reporter:        str,
    river_name:      str,
    water_level_cm:  int,
    river_level:     str,            # normal / waspada / siaga / awas
    flooded_areas:   list[dict],     # [{"name": "RT 04 Semarang Utara", "depth_cm": 50, "est_affected": 200}]
    notes:           str = "",
) -> dict:
    """Buat satu objek flood report terstandarisasi."""
    river_level = river_level.lower()
    if river_level not in RIVER_LEVEL_BOOST:
        river_level = "normal"

    boost = _calculate_boost(river_level, flooded_areas)

    return {
        "id":              f"{city}_{int(time.time() * 1000)}",
        "city":            city,
        "reported_at":     datetime.now(timezone.utc).isoformat(),
        "reporter":        reporter or "Koordinator BPBD",
        "river_name":      river_name,
        "water_level_cm":  water_level_cm,
        "river_level":     river_level,
        "river_level_label": LEVEL_LABELS[river_level]["label"],
        "flooded_areas":   flooded_areas or [],
        "notes":           notes,
        "boost_score":     boost["total"],
        "boost_breakdown": boost,
    }


def _calculate_boost(river_level: str, flooded_areas: list[dict]) -> dict:
    """
    Hitung boost score dari laporan lapangan.

    River level boost: berdasarkan status TMA sungai
    Area boost: +3 per area genangan, max 15 poin
    Total max: RIVER_LEVEL_BOOST[max] + FLOODED_AREA_MAX_BOOST = 25 + 15 = 40
    (akan di-cap oleh vulnerability.py agar total boost max 30)
    """
    river_boost = RIVER_LEVEL_BOOST.get(river_level, 0)
    area_boost  = min(
        len(flooded_areas) * FLOODED_AREA_BOOST_PER_AREA,
        FLOODED_AREA_MAX_BOOST
    )
    total_boost = river_boost + area_boost

    return {
        "total":       total_boost,
        "river_boost": river_boost,
        "area_boost":  area_boost,
        "river_level": river_level,
        "areas_count": len(flooded_areas),
        "reason": (
            f"TMA {river_level.upper()} (+{river_boost})"
            + (f" + {len(flooded_areas)} area genangan (+{area_boost})" if area_boost > 0 else "")
        ),
    }


# ── Public API ────────────────────────────────────────────────────────────────
def add_report(
    city:           str,
    reporter:       str,
    river_name:     str,
    water_level_cm: int,
    river_level:    str,
    flooded_areas:  list[dict],
    notes:          str = "",
) -> dict:
    """
    Tambah laporan banjir baru untuk satu kota.
    Return: report yang baru dibuat.
    """
    city = city.lower()
    report = _make_report(
        city, reporter, river_name,
        water_level_cm, river_level,
        flooded_areas, notes,
    )

    if city not in _store:
        _store[city] = []

    # Simpan hanya 20 laporan terakhir per kota (untuk POC)
    _store[city].insert(0, report)
    _store[city] = _store[city][:20]

    _save_to_disk()
    logger.success(
        f"  Field report: {city} | {river_name} {water_level_cm}cm "
        f"({river_level.upper()}) | boost=+{report['boost_score']}"
    )
    return report


def get_reports(city: str, limit: int = 10) -> list[dict]:
    """Ambil laporan terbaru untuk satu kota."""
    city = city.lower()
    return _store.get(city, [])[:limit]


def get_latest_boost(city: str) -> dict:
    """
    Ambil boost score terbaru dari laporan lapangan.
    Hanya menggunakan laporan dalam 12 jam terakhir.

    Return: dict dengan boost_score dan reason.
    """
    city       = city.lower()
    reports    = _store.get(city, [])
    cutoff     = time.time() - 12 * 3600  # 12 jam

    recent = []
    for r in reports:
        try:
            ts = datetime.fromisoformat(r["reported_at"]).timestamp()
            if ts > cutoff:
                recent.append(r)
        except Exception:
            continue

    if not recent:
        return {"boost_score": 0, "reason": "", "report_count": 0}

    # Ambil boost tertinggi dari laporan terbaru (bukan kumulatif)
    best  = max(recent, key=lambda r: r["boost_score"])
    total = best["boost_score"]

    return {
        "boost_score":  total,
        "reason":       best["boost_breakdown"]["reason"],
        "report_count": len(recent),
        "latest_report": best,
    }


def clear_reports(city: str) -> int:
    """Hapus semua laporan untuk satu kota. Return jumlah yang dihapus."""
    city  = city.lower()
    count = len(_store.get(city, []))
    _store[city] = []
    _save_to_disk()
    logger.info(f"Cleared {count} reports for {city}")
    return count


def get_rivers(city: str) -> list[str]:
    """Daftar sungai kritis untuk kota tertentu."""
    return RIVERS_BY_CITY.get(city.lower(), [])
