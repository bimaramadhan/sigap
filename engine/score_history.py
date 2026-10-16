"""
engine/score_history.py
────────────────────────
Menyimpan histori skor risiko per kota untuk menghitung MOMENTUM
(kecepatan & arah perubahan risiko).

Momentum membedakan dua situasi yang skornya sama:
  - Skor 60 dan NAIK +8/jam  → eskalasi cepat, prioritas tinggi
  - Skor 60 dan STABIL       → terkendali

Storage: file JSON ringan (data/cache/score_history.json).
Konsisten dengan arsitektur SKIP_DB — tidak butuh Postgres.
Hanya menyimpan 24 titik terakhir per kota (cukup untuk tren beberapa jam).
"""

import json
from datetime import datetime, timezone
from pathlib import Path

from loguru import logger

_HISTORY_FILE = Path("data/cache/score_history.json")
_MAX_POINTS   = 24          # simpan maksimal 24 snapshot per kota
_MIN_GAP_SEC  = 300         # jangan catat lebih sering dari tiap 5 menit


def _load() -> dict:
    if not _HISTORY_FILE.exists():
        return {}
    try:
        return json.loads(_HISTORY_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save(data: dict) -> None:
    try:
        _HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        _HISTORY_FILE.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    except Exception as exc:
        logger.warning(f"  Gagal simpan score history: {exc}")


def record(kab_kode: str, score: float) -> None:
    """Catat satu snapshot skor. Di-throttle agar tidak terlalu rapat."""
    data = _load()
    points = data.get(kab_kode, [])
    now = datetime.now(timezone.utc)

    # Throttle: skip kalau titik terakhir < 5 menit lalu
    if points:
        try:
            last_ts = datetime.fromisoformat(points[-1]["t"])
            if last_ts.tzinfo is None:
                last_ts = last_ts.replace(tzinfo=timezone.utc)
            if (now - last_ts).total_seconds() < _MIN_GAP_SEC:
                return
        except Exception:
            pass

    points.append({"t": now.isoformat(), "s": round(float(score), 1)})
    data[kab_kode] = points[-_MAX_POINTS:]   # jaga maksimal 24 titik
    _save(data)


def momentum(kab_kode: str) -> dict:
    """
    Hitung momentum dari histori: kecepatan perubahan skor per jam.

    Returns dict:
      - rate_per_hour : float   (Δskor per jam; positif = naik)
      - direction     : str     ('rising' / 'falling' / 'stable')
      - trend_label   : str     (teks siap tampil)
      - n_points      : int
    """
    points = _load().get(kab_kode, [])
    if len(points) < 2:
        return {
            "rate_per_hour": 0.0,
            "direction":     "stable",
            "trend_label":   "Belum cukup data tren",
            "n_points":      len(points),
        }

    # Pakai titik dalam ~3 jam terakhir untuk tren yang relevan
    try:
        now = datetime.fromisoformat(points[-1]["t"])
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)
    except Exception:
        return {"rate_per_hour": 0.0, "direction": "stable", "trend_label": "", "n_points": len(points)}

    recent = []
    for p in points:
        try:
            ts = datetime.fromisoformat(p["t"])
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            age_h = (now - ts).total_seconds() / 3600
            if age_h <= 3.5:
                recent.append((age_h, p["s"]))
        except Exception:
            continue

    if len(recent) < 2:
        return {"rate_per_hour": 0.0, "direction": "stable", "trend_label": "Risiko stabil", "n_points": len(points)}

    # Δskor / Δjam antara titik terjauh dan terbaru dalam window
    recent.sort(key=lambda x: x[0], reverse=True)  # terlama dulu
    oldest_age, oldest_s = recent[0]
    newest_age, newest_s = recent[-1]
    dt_h = oldest_age - newest_age
    if dt_h <= 0:
        rate = 0.0
    else:
        rate = (newest_s - oldest_s) / dt_h

    if rate >= 3:
        direction, label = "rising", f"⬆ Risiko naik cepat (+{rate:.0f}/jam)"
    elif rate >= 1:
        direction, label = "rising", f"↗ Risiko meningkat (+{rate:.0f}/jam)"
    elif rate <= -3:
        direction, label = "falling", f"⬇ Risiko turun cepat ({rate:.0f}/jam)"
    elif rate <= -1:
        direction, label = "falling", f"↘ Risiko menurun ({rate:.0f}/jam)"
    else:
        direction, label = "stable", "→ Risiko stabil"

    return {
        "rate_per_hour": round(rate, 1),
        "direction":     direction,
        "trend_label":   label,
        "n_points":      len(points),
    }
