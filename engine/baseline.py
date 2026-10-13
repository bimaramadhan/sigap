"""
engine/baseline.py
──────────────────
Cache baseline InaRisk per kab/kota.

Yang disimpan: fitur mentah dan base_score, plus polygon kecamatan.
Skor akhir (cuaca, alert, laporan) tidak disimpan di sini.
"""

import threading
from datetime import datetime, timezone

from loguru import logger

from engine.db import (
    baseline_is_fresh,
    db_available,
    list_stale_baselines,
    load_baseline,
    save_baseline,
)
from engine.places import resolve_bbox
from engine.wilayah import canonical_kab, lookup_kab

_locks: dict[str, threading.Lock] = {}
_locks_guard = threading.Lock()


def _city_lock(kab_kode: str) -> threading.Lock:
    with _locks_guard:
        lock = _locks.get(kab_kode)
        if lock is None:
            lock = threading.Lock()
            _locks[kab_kode] = lock
        return lock


def _row_is_fresh(row: dict) -> bool:
    """Baseline live berlaku 7 hari. Hasil fallback dicek lagi setelah 30 menit."""
    if not baseline_is_fresh(row["fetched_at"]):
        return False
    if (row.get("source") or "") == "fallback" and _age_hours(row["fetched_at"]) > 0.5:
        return False
    return True


def _age_hours(fetched_at: datetime) -> float:
    if fetched_at.tzinfo is None:
        fetched_at = fetched_at.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - fetched_at).total_seconds() / 3600


def _attach_meta(row: dict) -> dict:
    fetched_at = row["fetched_at"]
    return {
        **row,
        "features": row.get("features_json") or {},
        "age_hours": round(_age_hours(fetched_at), 2),
        "fetched_at_iso": fetched_at.isoformat() if hasattr(fetched_at, "isoformat") else str(fetched_at),
    }


def _fetch_and_store(kab_kode: str) -> dict:
    kab = lookup_kab(kab_kode)
    if not kab:
        raise ValueError(f"Kab/kota '{kab_kode}' tidak ada di katalog wilayah")

    bbox = resolve_bbox(kab_kode)
    if len(bbox) != 4:
        raise ValueError(f"Batas peta untuk {kab['label']} belum tersedia")

    from engine.vulnerability import calculate
    from pipeline.inarisk_loader import get_all_features, to_vulnerability_format

    raw = get_all_features(
        kab_kode,
        force_refresh=True,
        bbox=bbox,
        label=kab["label"],
        province=kab["province"],
    )
    features = to_vulnerability_format(kab_kode, raw)
    features["config"] = {
        "label": kab["label"],
        "province": kab["province"],
        "bbox": bbox,
    }
    base = calculate(kab_kode, features)
    source = "fallback" if features.get("_is_sample") else (features.get("_source") or "InaRisk BNPB")

    polygons = None
    try:
        from pipeline.inarisk_polygon import get_flood_polygons
        polygons = get_flood_polygons(kab_kode, force_refresh=True, bbox=bbox)
    except Exception as exc:
        logger.warning(f"Polygon {kab_kode} gagal, baseline fitur tetap disimpan: {exc}")

    saved = save_baseline(
        kab_kode=kab_kode,
        features=features,
        base_score=base.score,
        polygons=polygons,
        source=source,
    )
    logger.success(f"Baseline {kab['label']} tersimpan, base={base.score}")
    return _attach_meta(saved)


def ensure_baseline(city: str, force: bool = False) -> dict:
    """
    Baseline segar untuk satu kab/kota.
    Kota yang belum pernah dibuka di-fetch saat dipanggil.

    Kalau Postgres tidak tersedia, fallback ke file cache dari inarisk_loader.
    """
    kab = canonical_kab(city)
    if not kab:
        raise ValueError(f"Kab/kota '{city}' tidak ada di katalog wilayah")

    # ── Fallback: tanpa DB → pakai inarisk_loader file cache langsung ─────────
    if not db_available():
        return _ensure_baseline_filecache(kab)

    with _city_lock(kab):
        if not force:
            current = load_baseline(kab, with_polygons=False)
            if current and _row_is_fresh(current):
                return _attach_meta(current)
        return _fetch_and_store(kab)


def _ensure_baseline_filecache(kab_kode: str) -> dict:
    """
    Fallback tanpa Postgres — fetch InaRisk dengan bbox + label dari katalog
    wilayah, sama seperti _fetch_and_store tapi tanpa simpan ke DB.
    """
    from datetime import datetime, timezone
    from pipeline.inarisk_loader import get_all_features, to_vulnerability_format

    kab = lookup_kab(kab_kode)
    if not kab:
        raise ValueError(f"Kab/kota '{kab_kode}' tidak ada di katalog wilayah")

    bbox = resolve_bbox(kab_kode)
    if len(bbox) != 4:
        raise ValueError(f"Batas peta untuk {kab['label']} belum tersedia")

    logger.debug(f"  baseline fallback (no DB): {kab['label']}")

    # Fetch InaRisk dengan bbox + label eksplisit (bukan nama kota via CITY_BOUNDS)
    raw = get_all_features(
        kab_kode,
        bbox=bbox,
        label=kab["label"],
        province=kab["province"],
    )
    features = to_vulnerability_format(kab_kode, raw)
    features["config"] = {
        "label":    kab["label"],
        "province": kab["province"],
        "bbox":     bbox,
    }

    now = datetime.now(timezone.utc)
    return {
        "kab_kode":       kab_kode,
        "features":       features,
        "features_json":  features,
        "base_score":     0,            # scored live in scoring.py
        "polygons_json":  None,
        "fetched_at":     now,
        "fetched_at_iso": now.isoformat(),
        "age_hours":      0,
        "source":         "file-cache",
    }


def get_polygons(city: str, force: bool = False) -> dict:
    """GeoJSON kecamatan dari cache baseline, di-refresh jika kosong atau basi."""
    kab = canonical_kab(city)
    if not kab:
        raise ValueError(f"Kab/kota '{city}' tidak ada di katalog wilayah")

    # Fallback tanpa DB → query inarisk_polygon langsung (punya file cache sendiri)
    if not db_available():
        from pipeline.inarisk_polygon import get_flood_polygons
        bbox = resolve_bbox(kab)
        return get_flood_polygons(kab, bbox=bbox)

    cached = load_baseline(kab, with_polygons=True)
    fresh = bool(cached) and baseline_is_fresh(cached["fetched_at"])
    if fresh and cached.get("polygons_json") and not force:
        return cached["polygons_json"]

    if force or not fresh:
        ensure_baseline(kab, force=force or not fresh)
        cached = load_baseline(kab, with_polygons=True)

    polygons = (cached or {}).get("polygons_json")
    if not polygons:
        raise ValueError(f"Polygon kecamatan untuk {kab} belum tersedia")
    return polygons


def refresh_stale(limit: int = 5) -> dict:
    """Refresh baseline yang lebih tua dari 7 hari. Dipakai Cloud Scheduler."""
    targets = list_stale_baselines(limit)
    refreshed = []
    errors = []
    for kab in targets:
        try:
            ensure_baseline(kab, force=True)
            refreshed.append(kab)
        except Exception as exc:
            logger.warning(f"Refresh baseline {kab} gagal: {exc}")
            errors.append({"kab_kode": kab, "error": str(exc)})
    return {"checked": len(targets), "refreshed": refreshed, "errors": errors}
