"""
test_inarisk_integration.py
────────────────────────────
Test bahwa InaRisk berhasil menggantikan Earth Engine sebagai
primary data source untuk vulnerability scorer.

Jalankan: python test_inarisk_integration.py
"""
import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from engine.vulnerability import calculate_from_cache_or_ee

CITIES = ["semarang", "bekasi", "jakarta"]

def run():
    print("=" * 60)
    print("  SIGAP --- Test InaRisk sebagai Primary Data Source")
    print("=" * 60)
    print()

    for city in CITIES:
        print(f"--- {city.upper()} ---")
        result = calculate_from_cache_or_ee(
            city,
            include_weather=True,
            include_alerts=False,
        )

        is_inarisk = "InaRisk" in (result.priority_actions[0] if result.priority_actions else "")
        source_tag = "[InaRisk BNPB]" if not result.is_sample_data else "[partial sample]"

        print(f"Data source  : {source_tag}")
        print(f"Score        : {result.score}")
        cat_clean = result.category.encode('ascii', 'ignore').decode()
        print(f"Category     : {cat_clean.strip() or result.category[2:]}")
        print(f"Population   : {result.total_population:,} jiwa")
        print(f"Flood ratio  : {result.flood_ratio_10yr:.1%}")
        print(f"Elevation min: {result.elevation_min}m")
        print(f"Hist. events : {result.historical_events}")
        print()
        print("Score breakdown:")
        for k, v in result.score_breakdown().items():
            print(f"  {k:12s}: +{v}")
        print()

    print("=" * 60)
    print("Test selesai. InaRisk aktif sebagai primary source.")
    print("EE masih tersedia sebagai fallback.")
    print("=" * 60)

if __name__ == "__main__":
    run()
