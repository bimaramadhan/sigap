"""
engine/narrator.py
──────────────────
Mengubah VulnerabilityResult (angka + data teknis) menjadi narasi
bahasa Indonesia yang bisa langsung dibaca oleh koordinator BPBD.

Menggunakan Google Gemini AI — dua opsi:
  1. Google AI Studio API (GRATIS, tidak perlu billing/kartu kredit)
     → Set GEMINI_API_KEY di .env
     → Daftar di: https://aistudio.google.com → Get API Key
     → Limit free tier: 15 req/menit, 1 juta token/hari

  2. Vertex AI (berbayar, butuh GCP project + billing)
     → Set GCP_PROJECT_ID + gcloud auth application-default login
     → Dipakai otomatis jika GEMINI_API_KEY tidak ada

Prioritas: Google AI Studio → Vertex AI → Template fallback

Fallback: Jika keduanya tidak tersedia, pakai template engine berbasis
          rules yang sudah fungsional dan informatif.
"""

import os
from typing import Optional

from dotenv import load_dotenv
from loguru import logger

load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────────
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")          # Google AI Studio (gratis)
GCP_PROJECT    = os.getenv("GCP_PROJECT_ID", "")           # Vertex AI (berbayar)
GCP_REGION     = os.getenv("GCP_REGION", "asia-southeast2")
GEMINI_MODEL   = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
DEMO_MODE      = os.getenv("DEMO_MODE", "false").lower() == "true"


# ── System Prompt ─────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """Kamu adalah SIGAP AI, sistem pendukung keputusan penanggulangan banjir
untuk koordinator BPBD Indonesia. Tugasmu adalah menjelaskan situasi bencana dan
memberikan rekomendasi aksi dalam bahasa Indonesia yang jelas dan langsung dapat dikerjakan.

Aturan penting:
- Gunakan bahasa yang mudah dipahami oleh petugas lapangan, bukan bahasa ilmiah
- Selalu sebut angka konkret (jumlah jiwa, waktu, lokasi)
- Gunakan format yang mudah di-scan: bullet points untuk aksi, paragraf untuk konteks
- Jangan sebut istilah teknis seperti "return period", "flood ratio", atau "vulnerability score"
- Fokus pada: APA yang akan terjadi, SIAPA yang paling berisiko, APA yang harus dilakukan SEKARANG
- Level status menggunakan NORMAL/WASPADA/SIAGA/AWAS sesuai Peraturan BNPB No.2/2024
- Maksimal 300 kata"""


def _build_prompt(result) -> str:
    """Build prompt dari VulnerabilityResult untuk Gemini."""
    bd = result.score_breakdown()
    return f"""Berikan briefing situasi bencana untuk koordinator BPBD {result.city_label}.

DATA SITUASI:
- Status: {result.category} (skor {result.score}/100)
- Total Populasi: {result.total_population:,} jiwa
- Estimasi Warga Rentan (lansia + balita): {result.est_vulnerable:,} jiwa
- Kepadatan: {result.density_per_km2:,} jiwa/km²
- Proporsi area berpotensi banjir: {result.flood_ratio_10yr:.1%}
- Kejadian banjir historis (2000-2018): {result.historical_events} kali
- Elevasi minimum wilayah: {result.elevation_min}m dari permukaan laut
- Elevasi rata-rata: {result.elevation_mean}m

FAKTOR DOMINAN:
- Bahaya banjir: kontribusi {bd.get('hazard', 0)} poin
- Kepadatan populasi: kontribusi {bd.get('exposure', 0)} poin
- Populasi rentan: kontribusi {bd.get('vulnerable', 0)} poin
{f"- Cuaca terkini: {result.weather_desc} (+{result.weather_boost:.0f} poin)" if result.weather_boost > 0 else ""}
{f"- Alert BMKG aktif: +{result.alert_boost:.0f} poin" if result.alert_boost > 0 else ""}

REKOMENDASI SISTEM:
{chr(10).join(f'- {a}' for a in result.priority_actions[:5])}

Tulis briefing situasi untuk koordinator lapangan. Format:
1. Satu paragraf ringkasan situasi (2-3 kalimat)
2. Daftar 3-5 tindakan prioritas yang harus dilakukan sekarang
3. Satu kalimat penutup tentang sumber daya kritis yang dibutuhkan"""


# ── Client Initializer ────────────────────────────────────────────────────────
def _init_google_ai_studio():
    """
    Inisialisasi Google AI Studio (gratis).
    Butuh GEMINI_API_KEY dari https://aistudio.google.com
    """
    if not GEMINI_API_KEY or GEMINI_API_KEY == "your-gemini-api-key":
        return None
    try:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel(
            model_name=GEMINI_MODEL,
            system_instruction=SYSTEM_PROMPT,
        )
        logger.success(f"Gemini AI Studio initialized: {GEMINI_MODEL} (FREE tier)")
        return ("aistudio", model)
    except ImportError:
        logger.warning("google-generativeai tidak terinstall. Jalankan: pip install google-generativeai")
        return None
    except Exception as e:
        logger.warning(f"Gemini AI Studio init gagal: {e}")
        return None


def _init_vertex_ai():
    """
    Inisialisasi Vertex AI (berbayar — fallback ke AI Studio).
    Butuh GCP_PROJECT_ID + gcloud auth application-default login.
    """
    if not GCP_PROJECT or DEMO_MODE:
        return None
    try:
        import vertexai
        from vertexai.generative_models import GenerativeModel
        vertexai.init(project=GCP_PROJECT, location=GCP_REGION)
        model = GenerativeModel(GEMINI_MODEL)
        logger.success(f"Vertex AI initialized: {GEMINI_MODEL} (project={GCP_PROJECT})")
        return ("vertex", model)
    except ImportError:
        logger.warning("google-cloud-aiplatform tidak terinstall")
        return None
    except Exception as e:
        logger.warning(f"Vertex AI init gagal: {e}")
        return None


def _init_gemini():
    """
    Coba inisialisasi Gemini — AI Studio dulu, Vertex AI sebagai fallback.
    Return: (source_type, model) atau None jika keduanya gagal.
    """
    # Prioritas 1: Google AI Studio (gratis)
    result = _init_google_ai_studio()
    if result:
        return result

    # Prioritas 2: Vertex AI (berbayar)
    result = _init_vertex_ai()
    if result:
        return result

    logger.info("Gemini tidak tersedia → pakai template narasi")
    return None


# ── Generation ────────────────────────────────────────────────────────────────
def _generate_with_aistudio(model, prompt: str) -> str:
    """Generate narasi menggunakan Google AI Studio."""
    response = model.generate_content(
        prompt,
        generation_config={
            "temperature":      0.4,
            "max_output_tokens":512,
        }
    )
    return response.text.strip()


def _generate_with_vertex(model, prompt: str) -> str:
    """Generate narasi menggunakan Vertex AI."""
    from vertexai.generative_models import GenerationConfig
    response = model.generate_content(
        [SYSTEM_PROMPT, prompt],
        generation_config=GenerationConfig(
            temperature=0.4,
            max_output_tokens=512,
        ),
    )
    return response.text.strip()


# ── Fallback Template ─────────────────────────────────────────────────────────
def _template_narasi(result) -> str:
    """Template narasi berbasis rules — dipakai saat Gemini tidak tersedia."""
    score    = result.score
    city     = result.city_label
    pop      = result.total_population
    vuln     = result.est_vulnerable
    flood_r  = result.flood_ratio_10yr
    hist     = result.historical_events
    elev_min = result.elevation_min
    resources= result.resource_needs

    if score >= 75:
        intro = (
            f"🚨 SITUASI {result.category} — {city} menghadapi ancaman banjir serius. "
            f"Dari {pop:,} jiwa penduduk, diperkirakan {resources.get('estimated_affected', 0):,} jiwa "
            f"di zona terdampak dan {vuln:,} warga rentan membutuhkan prioritas evakuasi segera."
        )
    elif score >= 50:
        intro = (
            f"⚠️  SITUASI {result.category} — {city} menunjukkan risiko banjir signifikan. "
            f"Sekitar {flood_r:.0%} wilayah kota berpotensi terkena genangan. "
            f"Dari {pop:,} jiwa penduduk, {vuln:,} warga rentan perlu perhatian khusus."
        )
    elif score >= 25:
        intro = (
            f"📋 SITUASI {result.category} — {city} berada pada level risiko sedang. "
            f"Kondisi perlu dipantau secara aktif, terutama wilayah dengan elevasi rendah."
        )
    else:
        intro = (
            f"✅ SITUASI {result.category} — {city} saat ini berada pada risiko rendah. "
            f"Pantau peringatan BMKG secara berkala."
        )

    actions_text = "\n".join(
        f"  {i+1}. {a}" for i, a in enumerate(result.priority_actions[:5])
    )

    resource_text = (
        f"Estimasi kebutuhan minimal: {resources.get('perahu_minimal', 0)} perahu evakuasi, "
        f"{resources.get('tim_sar_minimal', 0)} tim SAR, "
        f"{resources.get('titik_evakuasi', 0)} titik pengungsian untuk "
        f"{resources.get('estimated_affected', 0):,} jiwa terdampak."
    )

    hist_notes = []
    if hist >= 10:
        hist_notes.append(
            f"📊 {city} memiliki rekam jejak {hist} kejadian banjir (2000-2018)."
        )
    if elev_min < 0:
        hist_notes.append(
            f"🌊 Sebagian wilayah di bawah permukaan laut (min {elev_min}m) — risiko rob."
        )

    parts = [intro, "", "TINDAKAN PRIORITAS:", actions_text, "", resource_text]
    if hist_notes:
        parts.extend([""] + hist_notes)

    parts.append("\n[Narasi dari template engine — aktifkan Gemini AI untuk narasi yang lebih adaptif]")
    return "\n".join(parts).strip()


# ── Public API ────────────────────────────────────────────────────────────────
def generate_narasi(result, use_gemini: bool = True) -> dict:
    """
    Generate narasi bahasa Indonesia dari VulnerabilityResult.

    Urutan prioritas:
    1. Google AI Studio (GRATIS) — jika GEMINI_API_KEY ada di .env
    2. Vertex AI (berbayar) — jika GCP_PROJECT_ID + auth tersedia
    3. Template engine — selalu tersedia sebagai fallback

    Args:
        result:      VulnerabilityResult dari vulnerability.py
        use_gemini:  Coba Gemini dulu, fallback ke template jika gagal

    Returns:
        dict dengan keys: narasi, source, model
    """
    if not use_gemini:
        return {
            "narasi": _template_narasi(result),
            "source": "template",
            "model":  "rule-based",
        }

    gemini_init = _init_gemini()

    if gemini_init:
        source_type, model = gemini_init
        try:
            prompt = _build_prompt(result)
            if source_type == "aistudio":
                narasi = _generate_with_aistudio(model, prompt)
                logger.success(f"  Narasi Gemini AI Studio berhasil ({len(narasi)} chars)")
                return {
                    "narasi": narasi,
                    "source": "gemini_aistudio",
                    "model":  GEMINI_MODEL,
                }
            else:
                narasi = _generate_with_vertex(model, prompt)
                logger.success(f"  Narasi Vertex AI berhasil ({len(narasi)} chars)")
                return {
                    "narasi": narasi,
                    "source": "gemini_vertex",
                    "model":  GEMINI_MODEL,
                }
        except Exception as e:
            logger.warning(f"  Gemini generation gagal: {e} → fallback ke template")

    return {
        "narasi": _template_narasi(result),
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

    source_labels = {
        "gemini_aistudio": "[green]Gemini AI Studio (GRATIS)[/green]",
        "gemini_vertex":   "[blue]Gemini Vertex AI[/blue]",
        "template":        "[yellow]Template Engine[/yellow]",
    }
    src_label = source_labels.get(output["source"], output["source"])

    rprint(Panel(
        output["narasi"],
        title=f"[bold blue]Narasi SIGAP -- {result.city_label}[/bold blue] (via {src_label})",
        border_style="blue",
        padding=(1, 2),
    ))
