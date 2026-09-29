"""
engine/narrator.py
──────────────────
Mengubah VulnerabilityResult (angka + data teknis) menjadi narasi
bahasa Indonesia yang bisa langsung dibaca oleh koordinator BPBD
tanpa background data science.

Menggunakan Gemini via Vertex AI (google-cloud-aiplatform).

Fallback: Jika Gemini tidak tersedia (belum setup GCP), pakai
          template-based narration sehingga POC tetap bisa berjalan.

Setup Gemini:
  1. Enable API: gcloud services enable aiplatform.googleapis.com
  2. gcloud auth application-default login
  3. Set GCP_PROJECT_ID di .env
"""

import os
from typing import Optional

from dotenv import load_dotenv
from loguru import logger

load_dotenv()

GCP_PROJECT  = os.getenv("GCP_PROJECT_ID", "")
GCP_REGION   = os.getenv("GCP_REGION", "asia-southeast2")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
DEMO_MODE    = os.getenv("DEMO_MODE", "false").lower() == "true"


# ── Prompt Template ───────────────────────────────────────────────────────────
SYSTEM_PROMPT = """Kamu adalah SIGAP AI, sistem pendukung keputusan penanggulangan banjir 
untuk koordinator BPBD Indonesia. Tugasmu adalah menjelaskan situasi bencana dan 
memberikan rekomendasi aksi dalam bahasa Indonesia yang jelas dan langsung dapat dikerjakan.

Aturan penting:
- Gunakan bahasa yang mudah dipahami oleh petugas lapangan, bukan bahasa ilmiah
- Selalu sebut angka konkret (jumlah jiwa, waktu, lokasi)
- Gunakan format yang mudah di-scan: bullet points untuk aksi, paragraf untuk konteks
- Jangan sebut istilah teknis seperti "return period", "flood ratio", atau "vulnerability score"
- Fokus pada: APA yang akan terjadi, SIAPA yang paling berisiko, APA yang harus dilakukan SEKARANG
- Maksimal 300 kata"""

def _build_prompt(result) -> str:
    """Build prompt dari VulnerabilityResult untuk Gemini."""
    breakdown = result.score_breakdown()
    return f"""Berikan briefing situasi bencana untuk koordinator BPBD {result.city_label}.

DATA SITUASI:
- Tingkat Risiko: {result.category} (skor {result.score}/100)
- Total Populasi: {result.total_population:,} jiwa
- Estimasi Warga Rentan (lansia + balita): {result.est_vulnerable:,} jiwa
- Kepadatan: {result.density_per_km2:,} jiwa/km²
- Proporsi area berpotensi banjir: {result.flood_ratio_10yr:.1%}
- Kejadian banjir historis (2000-2018): {result.historical_events} kali
- Elevasi minimum wilayah: {result.elevation_min}m dari permukaan laut
- Elevasi rata-rata: {result.elevation_mean}m

FAKTOR DOMINAN:
- Bahaya banjir: kontribusi {breakdown['hazard']} poin
- Kepadatan populasi: kontribusi {breakdown['exposure']} poin  
- Populasi rentan: kontribusi {breakdown['vulnerable']} poin

REKOMENDASI SISTEM:
{chr(10).join(f'- {a}' for a in result.priority_actions)}

Tulis briefing situasi untuk koordinator lapangan. Format:
1. Satu paragraf ringkasan situasi (2-3 kalimat)
2. Daftar 3-5 tindakan prioritas yang harus dilakukan sekarang
3. Satu kalimat penutup tentang sumber daya kritis yang dibutuhkan"""


# ── Gemini Client ─────────────────────────────────────────────────────────────
def _init_gemini():
    """Inisialisasi Vertex AI. Return None jika gagal."""
    if DEMO_MODE or not GCP_PROJECT:
        return None
    try:
        import vertexai
        from vertexai.generative_models import GenerativeModel
        vertexai.init(project=GCP_PROJECT, location=GCP_REGION)
        model = GenerativeModel(GEMINI_MODEL)
        logger.success(f"Gemini initialized: {GEMINI_MODEL} ✓")
        return model
    except Exception as e:
        logger.warning(f"Gemini init gagal: {e}")
        logger.info("→ Pakai template narasi. Untuk Gemini: set GCP_PROJECT_ID di .env")
        return None


# ── Fallback Template Narasi ──────────────────────────────────────────────────
def _template_narasi(result) -> str:
    """
    Template narasi berbasis rules — dipakai saat Gemini belum tersedia.
    Sudah cukup informatif untuk demo awal.
    """
    score     = result.score
    city      = result.city_label
    cat       = result.category
    pop       = result.total_population
    vuln      = result.est_vulnerable
    flood_r   = result.flood_ratio_10yr
    hist      = result.historical_events
    elev_min  = result.elevation_min
    resources = result.resource_needs

    # Intro berdasarkan kategori
    if score >= 75:
        intro = (
            f"⚠️  SITUASI KRITIS — {city} saat ini berada dalam kondisi risiko banjir "
            f"yang sangat tinggi dengan skor {score}/100. Dari total {pop:,} jiwa penduduk, "
            f"diperkirakan {resources['estimated_affected']:,} jiwa berada di zona terdampak "
            f"dan {vuln:,} di antaranya adalah warga rentan (lansia dan balita) yang "
            f"membutuhkan prioritas evakuasi segera."
        )
    elif score >= 50:
        intro = (
            f"⚠️  WASPADA — {city} menunjukkan risiko banjir tinggi (skor {score}/100). "
            f"Sekitar {flood_r:.0%} wilayah kota berpotensi terkena genangan. "
            f"Dari {pop:,} jiwa penduduk, terdapat {vuln:,} warga rentan yang perlu "
            f"mendapat perhatian khusus dalam kesiapsiagaan ini."
        )
    elif score >= 25:
        intro = (
            f"📋 SIAGA — {city} berada pada level risiko sedang (skor {score}/100). "
            f"Kondisi perlu dipantau secara aktif. Wilayah dengan elevasi rendah "
            f"dan kepadatan tinggi perlu mendapat perhatian lebih."
        )
    else:
        intro = (
            f"✅ NORMAL — {city} saat ini berada pada risiko rendah (skor {score}/100). "
            f"Tidak ada tindakan darurat yang diperlukan. Pantau peringatan BMKG secara berkala."
        )

    # Action list
    actions_text = "\n".join(f"  {i+1}. {a}" for i, a in enumerate(result.priority_actions[:5]))

    # Resource summary
    resource_text = (
        f"Estimasi kebutuhan minimal: {resources['perahu_minimal']} perahu evakuasi, "
        f"{resources['tim_sar_minimal']} tim SAR, "
        f"{resources['titik_evakuasi']} titik pengungsian untuk "
        f"{resources['estimated_affected']:,} jiwa terdampak."
    )

    # Historical context
    hist_text = ""
    if hist >= 10:
        hist_text = (
            f"\n\n📊 Catatan historis: {city} tercatat mengalami {hist} kejadian banjir "
            f"antara 2000-2018. Ini adalah wilayah dengan rekam jejak banjir yang signifikan."
        )
    if elev_min < 0:
        hist_text += (
            f"\n\n🌊 Perhatian: Sebagian wilayah berada di bawah permukaan laut "
            f"(min {elev_min}m), sangat rentan terhadap banjir rob."
        )

    narasi = f"""{intro}

TINDAKAN PRIORITAS:
{actions_text}

{resource_text}{hist_text}

[Narasi ini dihasilkan oleh SIGAP template engine. 
Aktifkan Gemini AI untuk narasi yang lebih adaptif dan kontekstual.]"""

    return narasi.strip()


# ── Public API ────────────────────────────────────────────────────────────────
def generate_narasi(result, use_gemini: bool = True) -> dict:
    """
    Generate narasi bahasa Indonesia dari VulnerabilityResult.

    Args:
        result:      VulnerabilityResult dari vulnerability.py
        use_gemini:  Coba Gemini dulu, fallback ke template jika gagal

    Returns:
        dict dengan keys: narasi, source, model
    """
    gemini_model = _init_gemini() if use_gemini else None

    if gemini_model:
        try:
            from vertexai.generative_models import GenerationConfig
            logger.info("  Generating narasi via Gemini...")

            response = gemini_model.generate_content(
                [SYSTEM_PROMPT, _build_prompt(result)],
                generation_config=GenerationConfig(
                    temperature=0.4,    # Sedikit kreatif tapi tetap faktual
                    max_output_tokens=512,
                ),
            )
            narasi = response.text.strip()
            logger.success("  Narasi Gemini berhasil ✓")
            return {
                "narasi": narasi,
                "source": "gemini",
                "model":  GEMINI_MODEL,
            }
        except Exception as e:
            logger.warning(f"  Gemini generation gagal: {e} → fallback ke template")

    # Fallback
    logger.info("  Generating narasi via template...")
    narasi = _template_narasi(result)
    return {
        "narasi": narasi,
        "source": "template",
        "model":  "rule-based",
    }


# ── CLI ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    from rich import print as rprint
    from rich.panel import Panel
    from engine.vulnerability import calculate_from_cache_or_ee

    city   = (sys.argv[1] if len(sys.argv) > 1 else "semarang").lower()
    result = calculate_from_cache_or_ee(city)
    output = generate_narasi(result)

    source_label = (
        f"[green]Gemini {output['model']}[/green]"
        if output["source"] == "gemini"
        else "[yellow]Template Engine[/yellow]"
    )

    rprint(Panel(
        output["narasi"],
        title=f"[bold blue]Narasi SIGAP — {result.city_label}[/bold blue] "
              f"(via {source_label})",
        border_style="blue",
        padding=(1, 2),
    ))
