"""Test city registry."""
import sys
sys.path.insert(0, ".")
from pipeline.city_registry import search_cities, get_city_bbox, get_registry_stats

# Test search
queries = ["bandung", "surabaya", "makassar", "medan", "jawa timur"]
for q in queries:
    results = search_cities(q, limit=3)
    names = [r["label"] for r in results]
    print(f"{q:15s}: {names}")

# Stats
print()
stats = get_registry_stats()
print(f"Total cities : {stats['total_cities']}")
print(f"Total provinsi: {stats['total_provinces']}")

# Test bbox on-demand
print()
print("Testing bbox Kota Semarang...")
bbox = get_city_bbox("kota_semarang")
print(f"Kota Semarang: {bbox}")
