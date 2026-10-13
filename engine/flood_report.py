"""
engine/flood_report.py
──────────────────────
Laporan lapangan dari koordinator BPBD, disimpan di Postgres.

Koordinator memilih satu desa/kelurahan. Kecamatan induk diambil dari
kode wilayah. Laporan menaikkan skor kota selama 12 jam dan menandai
kecamatan di peta. Riwayat laporan tetap tersimpan setelah jendela itu.
"""

import time
from datetime import datetime, timedelta, timezone

from loguru import logger
from psycopg.types.json import Jsonb

from engine.db import connect, peek_base_score
from engine.wilayah import canonical_kab, resolve_village

FLOOD_LEVEL_BOOST = {
    "awas":    25,
    "siaga":   15,
    "waspada":  8,
    "normal":   0,
}

LEVEL_LABELS = {
    "normal":   {"label": "🟢 Normal",   "color": "green"},
    "waspada":  {"label": "🟡 Waspada",  "color": "yellow"},
    "siaga":    {"label": "🟠 Siaga",    "color": "orange"},
    "awas":     {"label": "🔴 Awas",     "color": "red"},
}

REPORT_WINDOW = timedelta(hours=12)


def _normalize_level(level: str) -> str:
    level = (level or "normal").lower()
    if level not in FLOOD_LEVEL_BOOST:
        return "normal"
    return level


def _calculate_boost(flood_level: str, desa_name: str, kecamatan: str) -> dict:
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
    level = _normalize_level(report.get("flood_level") or "normal")
    reported_at = report.get("reported_at") or ""
    if hasattr(reported_at, "isoformat"):
        reported_at = reported_at.isoformat()
    return {
        "id":                 report.get("id", ""),
        "city":               report.get("kab_kode") or report.get("city") or "",
        "reported_at":        reported_at,
        "reporter":           report.get("reporter") or "Koordinator BPBD",
        "desa_kode":          report.get("desa_kode") or "",
        "desa_name":          report.get("desa_name") or "",
        "kecamatan":          report.get("kecamatan") or "",
        "kecamatan_kode":     report.get("kecamatan_kode") or "",
        "flood_level":        level,
        "flood_level_label":  LEVEL_LABELS[level]["label"],
        "notes":              report.get("notes") or "",
        "boost_score":        float(report.get("boost_score") or 0),
        "boost_breakdown":    report.get("boost_breakdown") or {},
    }


def _require_kab(city: str) -> str:
    kab = canonical_kab(city)
    if not kab:
        raise ValueError(f"Kab/kota '{city}' tidak ada di katalog wilayah")
    return kab


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
    kab = _require_kab(city)
    village = resolve_village(kab, desa_kode)
    flood_level = _normalize_level(flood_level)
    boost = _calculate_boost(flood_level, village["nama"], village["kecamatan"])
    report_id = f"{kab}_{int(time.time() * 1000)}"
    reported_at = datetime.now(timezone.utc)

    row = {
        "id": report_id,
        "kab_kode": kab,
        "desa_kode": village["kode"],
        "desa_name": village["nama"],
        "kecamatan_kode": village["kecamatan_kode"],
        "kecamatan": village["kecamatan"],
        "flood_level": flood_level,
        "boost_score": boost["total"],
        "boost_breakdown": boost,
        "reporter": reporter or "Koordinator BPBD",
        "notes": notes or "",
        "reported_at": reported_at,
        "base_score_at_report": peek_base_score(kab),
    }

    with connect() as conn:
        conn.execute(
            """
            INSERT INTO flood_reports (
                id, kab_kode, desa_kode, desa_name, kecamatan_kode, kecamatan,
                flood_level, boost_score, boost_breakdown, reporter, notes,
                reported_at, base_score_at_report
            ) VALUES (
                %(id)s, %(kab_kode)s, %(desa_kode)s, %(desa_name)s, %(kecamatan_kode)s,
                %(kecamatan)s, %(flood_level)s, %(boost_score)s, %(boost_breakdown)s,
                %(reporter)s, %(notes)s, %(reported_at)s, %(base_score_at_report)s
            )
            """,
            {**row, "boost_breakdown": Jsonb(boost)},
        )
        conn.commit()

    logger.success(
        f"  Field report: {kab} | {village['nama']} ({village['kecamatan']}) "
        f"{flood_level.upper()} | boost=+{boost['total']}"
    )
    return _public_report(row)


def get_reports(city: str, limit: int = 10) -> list[dict]:
    """Riwayat laporan terbaru untuk satu kab/kota, tidak dibatasi 12 jam."""
    kab = _require_kab(city)
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT * FROM flood_reports
            WHERE kab_kode = %s
            ORDER BY reported_at DESC
            LIMIT %s
            """,
            (kab, limit),
        ).fetchall()
    return [_public_report(row) for row in rows]


def _recent_reports(kab: str) -> list[dict]:
    cutoff = datetime.now(timezone.utc) - REPORT_WINDOW
    with connect() as conn:
        return conn.execute(
            """
            SELECT * FROM flood_reports
            WHERE kab_kode = %s AND reported_at > %s
            ORDER BY reported_at DESC
            """,
            (kab, cutoff),
        ).fetchall()


def get_latest_boost(city: str) -> dict:
    """
    Boost tertinggi dari laporan 12 jam terakhir untuk seluruh kab/kota.
    Bukan jumlah semua kecamatan.
    """
    kab = canonical_kab(city)
    if not kab:
        return {"boost_score": 0, "reason": "", "report_count": 0}

    recent = _recent_reports(kab)
    if not recent:
        return {"boost_score": 0, "reason": "", "report_count": 0}

    best = max(recent, key=lambda row: row.get("boost_score") or 0)
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
    """
    kab = canonical_kab(city)
    if not kab:
        return {}

    best_by_name: dict[str, dict] = {}
    for report in _recent_reports(kab):
        name = (report.get("kecamatan") or "").strip()
        if not name:
            continue
        score = float(report.get("boost_score") or 0)
        current = best_by_name.get(name)
        if current is not None and score <= current["boost_score"]:
            continue
        level = _normalize_level(report.get("flood_level") or "normal")
        best_by_name[name] = {
            "boost_score": score,
            "flood_level": level,
            "desa_name":   report.get("desa_name") or "",
            "reason":      (report.get("boost_breakdown") or {}).get("reason", ""),
        }
    return best_by_name


def clear_reports(city: str) -> int:
    """Hapus semua laporan untuk satu kab/kota. Return jumlah yang dihapus."""
    kab = _require_kab(city)
    with connect() as conn:
        deleted = conn.execute(
            "DELETE FROM flood_reports WHERE kab_kode = %s",
            (kab,),
        )
        count = deleted.rowcount
        conn.commit()
    logger.info(f"Cleared {count} reports for {kab}")
    return count
