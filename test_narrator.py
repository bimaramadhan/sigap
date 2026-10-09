"""
test_narrator.py
Test narrator.py — cek apakah Gemini AI Studio atau template jalan.
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from engine.narrator import _init_google_ai_studio, _init_vertex_ai, generate_narasi
from engine.vulnerability import calculate_from_cache_or_ee

print("=" * 55)
print("  Test Gemini Narrator")
print("=" * 55)
print()

# Cek ketersediaan
ai = _init_google_ai_studio()
vx = _init_vertex_ai()

print(f"Google AI Studio : {'TERSEDIA' if ai else 'Belum setup (set GEMINI_API_KEY)'}")
print(f"Vertex AI        : {'TERSEDIA' if vx else 'Belum setup (GCP_PROJECT_ID)'}")
print()

# Generate narasi
print("Generating narasi untuk Semarang...")
result = calculate_from_cache_or_ee("semarang", include_weather=False, include_alerts=False)
output = generate_narasi(result)

source_map = {
    "gemini_aistudio": "Gemini AI Studio (GRATIS)",
    "gemini_vertex":   "Gemini Vertex AI",
    "template":        "Template Engine (fallback)",
}
print(f"Source: {source_map.get(output['source'], output['source'])}")
print(f"Model : {output['model']}")
print()
print("-" * 55)
print(output["narasi"][:500] + "..." if len(output["narasi"]) > 500 else output["narasi"])
print("-" * 55)
