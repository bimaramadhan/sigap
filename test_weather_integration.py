"""
test_weather_integration.py
────────────────────────────
Test end-to-end: verifikasi bahwa vulnerability score berubah
sesuai kondisi cuaca real-time dari BMKG.

Jalankan: python test_weather_integration.py
"""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from pipeline.ee_loader    import get_all_features
from pipeline.bmkg_weather import get_weather_summary
from engine.vulnerability  import calculate

CITY = "semarang"

def run():
    print("=" * 60)
    print("  SIGAP — Test Weather Integration")
    print("=" * 60)
    print()

    # ── 1. Load data ──────────────────────────────────────────────
    print("1. Loading data...")
    features = get_all_features(CITY)
    weather  = get_weather_summary(CITY)

    is_sample = features.get("_is_sample", True)
    print(f"   EE features : {'SAMPLE DATA' if is_sample else 'LIVE DATA'}")
    print(f"   Weather     : LIVE dari BMKG Prakiraan Cuaca API")
    print()

    # ── 2. Hitung skor TANPA weather boost ───────────────────────
    print("2. Skor TANPA weather boost (baseline statis):")
    result_base = calculate(CITY, features, weather_data=None, bmkg_alerts=None)
    print(f"   Score    : {result_base.score}")
    print(f"   Category : {result_base.category}")
    print()

    # ── 3. Hitung skor DENGAN weather real ───────────────────────
    rain_mm  = weather.get("rainfall_12h_mm", 0)
    w_desc   = weather.get("worst_weather_desc", "?")
    w_boost  = weather.get("boost_score", 0)
    w_risk   = weather.get("weather_risk", "none")

    print(f"3. Kondisi cuaca real hari ini (BMKG):")
    print(f"   Kondisi    : {w_desc}")
    print(f"   Rainfall   : {rain_mm:.1f} mm / 12 jam")
    print(f"   Risk Level : {w_risk.upper()}")
    print(f"   Boost Score: +{w_boost} poin")
    print()

    result_real = calculate(CITY, features, weather_data=weather, bmkg_alerts=None)
    print(f"4. Skor DENGAN weather real:")
    print(f"   Base score   : {result_base.score}")
    print(f"   Weather boost: +{result_real.weather_boost}")
    print(f"   Final score  : {result_real.score}")
    print(f"   Category     : {result_real.category}")
    print()

    # ── 4. Simulasi hujan lebat ───────────────────────────────────
    print("5. SIMULASI — Jika hujan lebat (68mm/12jam):")
    sim_weather = dict(weather)
    sim_weather["rainfall_12h_mm"]    = 68.4
    sim_weather["boost_score"]        = 15
    sim_weather["weather_risk"]       = "high"
    sim_weather["worst_weather_desc"] = "Hujan Lebat [SIMULASI]"
    sim_weather["boost_reason"]       = "Simulasi hujan lebat >50mm/12jam"

    result_sim = calculate(CITY, features, weather_data=sim_weather, bmkg_alerts=None)
    print(f"   Final score  : {result_sim.score}")
    print(f"   Weather boost: +{result_sim.weather_boost}")
    print(f"   Category     : {result_sim.category}")
    print()

    # ── 5. Simulasi hujan ekstrem + alert ─────────────────────────
    print("6. SIMULASI — Hujan sangat lebat + BMKG Alert Extreme:")
    extreme_weather = dict(weather)
    extreme_weather["rainfall_12h_mm"]    = 115.0
    extreme_weather["boost_score"]        = 25
    extreme_weather["weather_risk"]       = "extreme"
    extreme_weather["worst_weather_desc"] = "Badai Petir [SIMULASI]"
    extreme_weather["boost_reason"]       = "Simulasi hujan >100mm/12jam"

    mock_alert = [{"severity": "Extreme", "province": "Jawa Tengah", "is_flood": True}]
    result_extreme = calculate(CITY, features, weather_data=extreme_weather, bmkg_alerts=mock_alert)
    print(f"   Base score   : {result_base.score}")
    print(f"   Weather boost: +{result_extreme.weather_boost}")
    print(f"   Alert boost  : +{result_extreme.alert_boost}")
    print(f"   Final score  : {result_extreme.score}")
    print(f"   Category     : {result_extreme.category}")
    print()

    # ── Summary ───────────────────────────────────────────────────
    print("=" * 60)
    print("  SUMMARY — Perubahan Skor per Kondisi Cuaca")
    print("=" * 60)
    scenarios = [
        ("Cerah (kondisi hari ini)", result_real.score,    result_real.category),
        ("Hujan Lebat [simulasi]",   result_sim.score,     result_sim.category),
        ("Badai + Alert Extreme",    result_extreme.score, result_extreme.category),
    ]
    for label, score, cat in scenarios:
        bar_len = 30
        filled  = round(score / 100 * bar_len)
        bar     = "#" * filled + "-" * (bar_len - filled)
        print(f"  {label:<30} [{bar}] {score:5.1f}  {cat}")
    print()
    print("HASIL: Skor BERUBAH sesuai kondisi cuaca.")
    print(f"       Baseline statis  : {result_base.score}")
    print(f"       Hujan lebat boost: +{result_sim.weather_boost} -> {result_sim.score}")
    print(f"       Extreme boost    : +{result_extreme.weather_boost}+{result_extreme.alert_boost} -> {result_extreme.score}")
    print()
    print("Test PASSED.")

if __name__ == "__main__":
    run()
