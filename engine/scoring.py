"""
engine/scoring.py
─────────────────
Skor akhir dihitung saat dibaca.

base_score datang dari baseline InaRisk yang di-cache.
Boost cuaca, alert BMKG, dan laporan lapangan ditambahkan di memori request
dan tidak ditulis kembali ke tabel baseline.
"""

from loguru import logger

from engine.baseline import ensure_baseline
from engine.flood_report import get_latest_boost
from engine.vulnerability import _get_category, calculate
from engine.wilayah import canonical_kab, province_matches, province_of
from pipeline.bmkg_weather import _default_weather, get_weather_summary


def score_city(
    city: str,
    include_weather: bool = True,
    include_alerts: bool = True,
    include_field: bool = True,
):
    """
    Return (VulnerabilityResult, weather_dict, alert_list).
    """
    kab = canonical_kab(city)
    if not kab:
        raise ValueError(f"Kab/kota '{city}' tidak ada di katalog wilayah")

    baseline = ensure_baseline(kab)
    features = baseline["features"]
    prov = province_of(kab)

    weather_data = None
    if include_weather:
        try:
            weather_data = get_weather_summary(kab)
        except Exception as exc:
            logger.warning(f"  Weather fetch gagal: {exc}")
            weather_data = _default_weather(kab)

    alert_data = []
    if include_alerts:
        try:
            from pipeline.bmkg_ingest import fetch_active_alerts
            all_alerts = fetch_active_alerts(flood_only=True)
            if prov:
                alert_data = [
                    alert for alert in all_alerts
                    if province_matches(alert.province, prov)
                ]
            else:
                alert_data = all_alerts[:3]
        except Exception as exc:
            logger.warning(f"  Alert fetch gagal: {exc}")

    # calculate() tetap menghasilkan komponen *_score + weather/alert boost.
    result = calculate(kab, features, weather_data, alert_data)
    result.baseline_fetched_at = baseline["fetched_at_iso"]
    result.baseline_age_hours = baseline["age_hours"]

    # Ambil boost laporan lapangan (dipakai Layer 2 risk model)
    field_reason = ""
    if include_field:
        field = get_latest_boost(kab)
        if field["boost_score"] > 0:
            result.field_boost = float(field["boost_score"])
            field_reason = field.get("reason") or ""

    # ── Model risiko 3-lapis (UNDRR structural × saturasi × momentum) ────────
    # Menggantikan penjumlahan linear lama (base + boost) yang bisa "mentok 100".
    from engine.risk_model import compute_advanced_score
    adv = compute_advanced_score(result, features, record_history=True)

    result.score              = adv["final_score"]
    result.structural_score   = adv["structural_score"]
    result.trigger_multiplier = adv["trigger_multiplier"]
    result.momentum_rate      = adv["momentum"]["rate_per_hour"]
    result.momentum_label     = adv["momentum"]["trend_label"]
    result.risk_method        = adv["_method"]
    result.category, result.category_message = _get_category(result.score)

    # Konteks tindakan: laporan lapangan + momentum (untuk Gemini & UI)
    if field_reason:
        result.priority_actions.insert(0, f"📡 Laporan lapangan: {field_reason}")
    if adv["momentum"]["direction"] == "rising" and adv["momentum"]["rate_per_hour"] >= 3:
        result.priority_actions.insert(
            0, f"⚡ {adv['momentum']['trend_label']} — antisipasi eskalasi 1-2 jam ke depan"
        )

    return result, weather_data or _default_weather(kab), alert_data
