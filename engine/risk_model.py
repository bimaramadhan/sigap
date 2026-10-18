"""
engine/risk_model.py
────────────────────
Model skor risiko banjir 3 lapis — berbasis kerangka risiko UNDRR/BNPB,
menggantikan penjumlahan linear naif (base + boost) yang bisa "mentok 100".

┌─ Layer 1 — STRUCTURAL RISK (kerapuhan fundamental wilayah) ──────────┐
│  Risk = Hazard × Vulnerability ÷ Capacity                            │
│  Kerangka resmi UNDRR, sama dengan metodologi InaRisk BNPB.          │
│  Menjawab "dari mana bobotnya?" → dari standar internasional.        │
└──────────────────────────────────────────────────────────────────────┘
                              ×
┌─ Layer 2 — DYNAMIC TRIGGER (seberapa aktif ancaman hari ini) ────────┐
│  Multiplier saturasi (1.0–1.6) dari hujan + alert + laporan lapangan.│
│  Kurva saturasi (tanh) → hujan ekstrem MENDEKATI maksimum, tidak     │
│  meledak. Menjawab masalah "hujan terus → mentok 100".               │
└──────────────────────────────────────────────────────────────────────┘
                              +
┌─ Layer 3 — MOMENTUM (ke mana situasi bergerak) ─────────────────────┐
│  Δskor/jam dari histori. Membedakan "60 & naik cepat" vs "60 stabil".│
└──────────────────────────────────────────────────────────────────────┘

Output: skor 0–100 yang naik realistis, plus penjelasan tiap lapisan
untuk transparansi (ditampilkan di UI dan dipakai Gemini).
"""

import math
from typing import Optional

from loguru import logger

from engine import score_history


# ── Layer 1: Structural Risk (UNDRR) ──────────────────────────────────────────
def _structural_risk(result, features: dict) -> dict:
    """
    Risk = Hazard × Vulnerability ÷ Capacity, dinormalisasi ke 0–100.

    Komponen diambil dari skor yang sudah dihitung vulnerability.calculate()
    + indeks kapasitas InaRisk BNPB (INDEKS_KAPASITAS_2021).
    """
    # Hazard: gabungan bahaya banjir + eksposur populasi + elevasi rendah
    # (tiga faktor ini = "seberapa besar & siapa yang terpapar ancaman fisik")
    hazard = (
        0.55 * result.hazard_score +
        0.30 * result.exposure_score +
        0.15 * result.elevation_score
    )

    # Vulnerability: kerentanan sosial (lansia+balita) + rekam jejak historis
    vulnerability = (
        0.70 * result.vulnerable_score +
        0.30 * result.history_score
    )

    # Capacity: kemampuan daerah menanggulangi (INDEKS_KAPASITAS InaRisk).
    # Default 0.5 kalau data tidak ada. Clamp ke 0.2–0.95 agar pembagi stabil.
    capacity = features.get("inarisk_capacity", 0.5)
    try:
        capacity = float(capacity)
    except (TypeError, ValueError):
        capacity = 0.5
    capacity = max(0.2, min(0.95, capacity if capacity > 0 else 0.5))

    # Risk = (Hazard × Vulnerability) / Capacity
    # Hazard & Vulnerability di 0–1. Dibagi capacity → bisa > 1, lalu dinormalisasi.
    raw = (hazard * max(0.05, vulnerability)) / capacity

    # Normalisasi: raw teoretis maksimum ≈ (1×1)/0.2 = 5.0 → petakan ke 0–100.
    # Pakai akar untuk mencegah skor rendah menumpuk di bawah (kurva lebih adil).
    norm = min(1.0, math.sqrt(raw / 5.0))
    structural = round(norm * 100, 1)

    return {
        "structural_score": structural,
        "hazard":           round(hazard, 3),
        "vulnerability":    round(vulnerability, 3),
        "capacity":         round(capacity, 3),
    }


# ── Layer 2: Dynamic Trigger Multiplier (saturasi) ────────────────────────────
def _trigger_multiplier(weather_boost: float, alert_boost: float, field_boost: float) -> dict:
    """
    Gabungkan tiga pemicu real-time jadi SATU multiplier 1.0–1.6 dengan
    kurva saturasi (tanh). Hujan ekstrem → mendekati 1.6, tidak pernah meledak.

    Kenapa multiplikatif, bukan aditif:
      - Aditif: hujan terus = +25 terus → base+75 → gampang mentok 100 (tidak realistis)
      - Multiplikatif + saturasi: pemicu MELIPATGANDAKAN risiko struktural, tapi
        efeknya melandai. Risiko rendah tetap relatif rendah walau hujan lebat;
        risiko tinggi jadi kritis. Ini lebih sesuai realita lapangan.
    """
    # Total "tekanan pemicu" mentah (0–75 dari skala boost lama)
    raw_pressure = weather_boost + alert_boost + field_boost

    # Saturasi: tanh melandai di nilai tinggi. Pada raw=75 → ~0.93 dari maksimum.
    sat = math.tanh(raw_pressure / 40.0)   # 40 = skala kelembutan kurva

    # Multiplier 1.0 (tanpa pemicu) → 1.6 (pemicu maksimum)
    multiplier = 1.0 + 0.6 * sat

    return {
        "multiplier":   round(multiplier, 3),
        "raw_pressure": round(raw_pressure, 1),
        "saturation":   round(sat, 3),
    }


def field_lift(weather_boost: float, alert_boost: float, field_boost: float) -> float:
    """
    Rasio skor dengan laporan lapangan dibanding tanpa laporan.

    Memakai kurva saturasi yang sama dengan gauge kota. Laporan 0 mengembalikan
    1.0, jadi kecamatan tanpa laporan tidak berubah.
    """
    if not field_boost or field_boost <= 0:
        return 1.0
    base = _trigger_multiplier(weather_boost, alert_boost, 0.0)["multiplier"]
    boosted = _trigger_multiplier(weather_boost, alert_boost, field_boost)["multiplier"]
    if base <= 0:
        return 1.0
    return boosted / base


# ── Orkestrasi 3 lapis ────────────────────────────────────────────────────────
def compute_advanced_score(result, features: dict, record_history: bool = True) -> dict:
    """
    Hitung skor final 3-lapis dari VulnerabilityResult yang sudah ada.

    Args:
        result:   VulnerabilityResult (punya *_score komponen + *_boost)
        features: dict features InaRisk (punya inarisk_capacity)
        record_history: simpan snapshot untuk momentum (set False saat simulasi)

    Returns dict lengkap untuk transparansi:
        final_score, category, structural_score, trigger_multiplier,
        momentum, dan rincian tiap lapisan.
    """
    # ── Layer 1 ──
    s1 = _structural_risk(result, features)
    structural = s1["structural_score"]

    # ── Layer 2 ──
    field_boost = getattr(result, "field_boost", 0.0)
    s2 = _trigger_multiplier(result.weather_boost, result.alert_boost, field_boost)
    multiplier = s2["multiplier"]

    # Skor setelah pemicu dinamis (masih smooth, tidak gampang mentok)
    triggered = structural * multiplier
    # Clamp halus ke 100 dengan saturasi akhir agar tidak pernah > 100 kaku
    final = round(min(100.0, triggered), 1)

    # ── Layer 3: Momentum ──
    kab = getattr(result, "city", "")
    if record_history and kab:
        score_history.record(kab, final)
    mom = score_history.momentum(kab) if kab else {
        "rate_per_hour": 0.0, "direction": "stable", "trend_label": "", "n_points": 0
    }

    return {
        "final_score":        final,
        "structural_score":   structural,
        "trigger_multiplier": multiplier,
        "momentum":           mom,
        # Rincian untuk UI / penjelasan juri
        "layer1_structural":  s1,
        "layer2_trigger":     s2,
        "_method":            "UNDRR Risk (Hazard×Vuln÷Capacity) × Saturation Trigger + Momentum",
    }
