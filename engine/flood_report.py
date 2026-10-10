"""
engine/flood_report.py
──────────────────────
Penyimpanan laporan lapangan dari koordinator BPBD.

Koordinator memilih satu desa/kelurahan. Kecamatan induk diambil dari
kode wilayah, bukan dari input bebas. Laporan ini menjadi boost ke
vulnerability score kota dan ke kecamatan tempat desa itu berada.

Sesuai Pasal 23 Peraturan BNPB No.2/2024 yang mewajibkan BPBD
memberikan umpan balik kondisi lapangan ke sistem peringatan dini.
"""

import json
import time
from datetime import datetime, timezone
from pathlib import Path

from loguru import logger

from engine.wilayah import resolve_village

# ── Config ────────────────────────────────────────────────────────────────────
DATA_DIR   = Path("data")
STORE_FILE = DATA_DIR / "flood_reports.json"

# Boost ke vulnerability score berdasarkan status banjir desa
FLOOD_LEVEL_BOOST = {
    "awas":    25,
    "siaga":   15,
    "waspada":  8,
    "normal":   0,
}

# Label lengkap per level (sesuai BNPB No.2/2024)
LEVEL_LABELS = {
    "normal":   {"label": "🟢 Normal",   "color": "green"},
    "waspada":  {"label": "🟡 Waspada",  "color": "yellow"},
    "siaga":    {"label": "🟠 Siaga",    "color": "orange"},
    "awas":     {"label": "🔴 Awas",     "color": "red"},
}

REPORT_WINDOW_SECONDS = 12 * 3600


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


_load_from_disk()


def _normalize_level(level: str) -> str:
    level = (level or "normal").lower()
    if level not in FLOOD_LEVEL_BOOST:
        return "normal"
    return level


def _calculate_boost(flood_level: str, desa_name: str, kecamatan: str) -> dict:
    """Boost hanya dari status banjir desa. Tidak ada tambahan per area genangan."""
    level_boost = FLOOD_LEVEL_BOOST.get(flood_level, 0)
    reason = (
        f"Desa {desa_name}, Kec. {kecamatan} — {flood_level.upper()} (+{level_boost})"
    )
    return {
        "total":       level_boost,
        "level_boost": level_boost,
        "flood_level": flood_level,
        "reason":      reason,
    }


def _public_report(report: dict) -> dict:
    """Bentuk laporan yang dikirim ke API, termasuk laporan sungai yang lama."""
    level = _normalize_level(report.get("flood_level") or report.get("river_level") or "normal")
    return {
        "id":                 report.get("id", ""),
        "city":               report.get("city", ""),
        "reported_at":        report.get("reported_at", ""),
        "reporter":           report.get("reporter") or "Koordinator BPBD",
        "desa_kode":          report.get("desa_kode") or "",
        "desa_name":          report.get("desa_name") or report.get("river_name") or "",
        "kecamatan":          report.get("kecamatan") or "",
        "kecamatan_kode":     report.get("kecamatan_kode") or "",
        "flood_level":        level,
        "flood_level_label":  report.get("flood_level_label") or report.get("river_level_label") or LEVEL_LABELS[level]["label"],
        "notes":              report.get("notes") or "",
        "boost_score":        float(report.get("boost_score") or 0),
        "boost_breakdown":    report.get("boost_breakdown") or {},
    }


def _recent_reports(city: str) -> list[dict]:
    """Laporan dalam 12 jam terakhir, terbaru dulu."""
    reports = _store.get(city.lower(), [])
    cutoff  = time.time() - REPORT_WINDOW_SECONDS
    recent  = []
    for report in reports:
        try:
            ts = datetime.fromisoformat(report["reported_at"]).timestamp()
        except Exception:
            continue
        if ts > cutoff:
            recent.append(report)
    return recent


# ── Public API ────────────────────────────────────────────────────────────────
def add_report(
    city:        str,
    reporter:    str,
    desa_kode:   str,
    flood_level: str,
    notes:       str = "",
) -> dict:
    """
    Tambah laporan banjir untuk satu desa.
    Kecamatan diisi dari katalog wilayah. Desa di luar kota ditolak.
    """
    city = city.lower()
    village = resolve_village(city, desa_kode)
    flood_level = _normalize_level(flood_level)
    boost = _calculate_boost(flood_level, village["nama"], village["kecamatan"])

    report = {
        "id":                 f"{city}_{int(time.time() * 1000)}",
        "city":               city,
        "reported_at":        datetime.now(timezone.utc).isoformat(),
        "reporter":           reporter or "Koordinator BPBD",
        "desa_kode":          village["kode"],
        "desa_name":          village["nama"],
        "kecamatan":          village["kecamatan"],
        "kecamatan_kode":     village["kecamatan_kode"],
        "flood_level":        flood_level,
        "flood_level_label":  LEVEL_LABELS[flood_level]["label"],
        "notes":              notes,
        "boost_score":        boost["total"],
        "boost_breakdown":    boost,
    }

    _store.setdefault(city, [])
    _store[city].insert(0, report)
    _store[city] = _store[city][:20]

    _save_to_disk()
    logger.success(
        f"  Field report: {city} | {village['nama']} ({village['kecamatan']}) "
        f"{flood_level.upper()} | boost=+{report['boost_score']}"
    )
    return _public_report(report)


def get_reports(city: str, limit: int = 10) -> list[dict]:
    """Ambil laporan terbaru untuk satu kota."""
    city = city.lower()
    return [_public_report(r) for r in _store.get(city, [])[:limit]]


def get_latest_boost(city: str) -> dict:
    """
    Boost tertinggi dari laporan 12 jam terakhir untuk seluruh kota.
    Bukan jumlah semua kecamatan.
    """
    recent = _recent_reports(city)
    if not recent:
        return {"boost_score": 0, "reason": "", "report_count": 0}

    best  = max(recent, key=lambda r: r.get("boost_score") or 0)
    total = best.get("boost_score") or 0
    reason = (best.get("boost_breakdown") or {}).get("reason", "")

    return {
        "boost_score":   total,
        "reason":        reason,
        "report_count":  len(recent),
        "latest_report": _public_report(best),
    }


def get_kecamatan_boosts(city: str) -> dict[str, dict]:
    """
    Boost tertinggi per nama kecamatan pada jendela 12 jam yang sama.
    Kunci adalah nama kecamatan supaya bisa dicocokkan ke WADMKC.
    Laporan lama tanpa kecamatan diabaikan.
    """
    best_by_name: dict[str, dict] = {}
    for report in _recent_reports(city):
        name = (report.get("kecamatan") or "").strip()
        if not name:
            continue
        score = float(report.get("boost_score") or 0)
        current = best_by_name.get(name)
        if current is not None and score <= current["boost_score"]:
            continue
        level = _normalize_level(report.get("flood_level") or report.get("river_level") or "normal")
        best_by_name[name] = {
            "boost_score": score,
            "flood_level": level,
            "desa_name":   report.get("desa_name") or "",
            "reason":      (report.get("boost_breakdown") or {}).get("reason", ""),
        }
    return best_by_name


def clear_reports(city: str) -> int:
    """Hapus semua laporan untuk satu kota. Return jumlah yang dihapus."""
    city  = city.lower()
    count = len(_store.get(city, []))
    _store[city] = []
    _save_to_disk()
    logger.info(f"Cleared {count} reports for {city}")
    return count
