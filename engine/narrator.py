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
     → Pakai SDK: google-genai (pip install google-genai)

  2. Vertex AI (berbayar, butuh GCP project + billing)
     → Set GCP_PROJECT_ID + gcloud auth application-default login
     → Dipakai otomatis jika GEMINI_API_KEY tidak ada

Prioritas: Google AI Studio → Vertex AI → Template fallback
"""

import os
from typing import Optional

from dotenv import load_dotenv
from loguru import logger

load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────────
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")           # Google AI Studio (gratis)
GCP_PROJECT    = os.getenv("GCP_PROJECT_ID", "")            # Vertex AI (berbayar)
GCP_REGION     = os.getenv("GCP_REGION", "asia-southeast2")
GEMINI_MODEL   = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
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
- Jika ada bagian "SOP & PEDOMAN BNPB" dalam konteks, jadikan ACUAN WAJIB untuk
  rekomendasi tindakan dan perhitungan kebutuhan sumber daya. Jangan membuat
  rekomendasi yang bertentangan dengan SOP tersebut.
- Jika ada "PROFIL WILAYAH", sebut kecamatan spesifik yang paling berisiko
  dalam rekomendasi evakuasi.
- Maksimal 300 kata"""


def _build_prompt(result, polygons: dict | None = None, lang: str = "id") -> str:
    """
    Build prompt dari VulnerabilityResult untuk Gemini.

    Meng-inject dua konteks tambahan secara scalable (tanpa markdown per kota):
      1. Profil kota — dirangkai otomatis dari data (city_profile.build_city_context)
      2. SOP universal — dari knowledge/sop/*.md, berlaku semua kota

    lang: "id" → narasi bahasa Indonesia, "en" → English.
    """
    bd = result.score_breakdown()

    # Instruksi bahasa output (ditambahkan di akhir prompt)
    if lang == "en":
        lang_instruction = (
            "\n\nIMPORTANT: Write the ENTIRE briefing in ENGLISH. "
            "Keep Indonesian proper nouns (city/district/river names, agency names "
            "like BPBD/BNPB/BMKG) as-is, but all narrative, labels, and recommendations "
            "must be in clear professional English. Keep status levels but add English "
            "in parentheses, e.g. 'SIAGA (Standby)', 'AWAS (Danger)'."
        )
    else:
        lang_instruction = ""

    # ── Konteks tambahan (scalable, bukan markdown per kota) ──────────────────
    city_ctx = ""
    sop_ctx  = ""
    try:
        from engine.city_profile import build_city_context, build_sop_context
        from engine.wilayah_geo import get_profil
        geo = get_profil(getattr(result, "city", "")) or None
        city_ctx = build_city_context(result, polygons=polygons, geo=geo)
        sop_ctx  = build_sop_context(max_chars=5000)
    except Exception as exc:
        logger.warning(f"  Konteks kota/SOP gagal dimuat: {exc}")

    knowledge_block = ""
    if city_ctx:
        knowledge_block += f"\n{city_ctx}\n"
    if sop_ctx:
        knowledge_block += (
            f"\nSOP & PEDOMAN BNPB (acuan wajib untuk rekomendasi):\n{sop_ctx}\n"
        )

    return f"""Berikan briefing situasi bencana untuk koordinator BPBD {result.city_label}.
{knowledge_block}

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
3. Satu kalimat penutup tentang sumber daya kritis yang dibutuhkan{lang_instruction}"""


# ── Google AI Studio (google-genai SDK) ───────────────────────────────────────
def _init_google_ai_studio():
    """
    Inisialisasi Google AI Studio menggunakan SDK google-genai (bukan google-generativeai).
    SDK baru: pip install google-genai
    """
    if not GEMINI_API_KEY or GEMINI_API_KEY in ("your-gemini-api-key", ""):
        logger.warning("GEMINI_API_KEY tidak ditemukan di .env → skip AI Studio")
        return None
    try:
        from google import genai
        client = genai.Client(api_key=GEMINI_API_KEY)
        logger.success(f"Gemini AI Studio initialized: {GEMINI_MODEL} (FREE tier)")
        return ("aistudio", client)
    except ImportError:
        logger.warning(
            "Package google-genai tidak terinstall. "
            "Jalankan: pip install google-genai"
        )
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
    Return: (source_type, client_or_model) atau None jika keduanya gagal.
    """
    # Prioritas 1: Google AI Studio (gratis, pakai google-genai SDK)
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
def _generate_with_aistudio(client, prompt: str) -> str:
    """
    Generate narasi menggunakan Google AI Studio via google-genai SDK.
    Ref: https://ai.google.dev/gemini-api/docs/text-generation

    Mengoptimalkan konfigurasi thinking:
    - Model Flash Lite menggunakan thinking_level=MINIMAL (thinking_budget=0 tidak didukung)
    - Model Flash standar mencoba thinking_budget=0 untuk menonaktifkan reasoning internal
    - Fallback otomatis tanpa thinking_config jika model tidak mendukung opsi tersebut.
    """
    from google.genai import types

    model_name = GEMINI_MODEL.lower()
    if "lite" in model_name:
        thinking_cfg = types.ThinkingConfig(thinking_level=types.ThinkingLevel.MINIMAL)
    else:
        thinking_cfg = types.ThinkingConfig(thinking_budget=0)

    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                temperature=0.4,
                max_output_tokens=1024,
                thinking_config=thinking_cfg,
            ),
            contents=prompt,
        )
        if response.text:
            return response.text.strip()
    except Exception as e:
        # Jika model menolak parameter thinking_config (400 INVALID_ARGUMENT), retry tanpa thinking_config
        err_msg = str(e)
        if "INVALID_ARGUMENT" in err_msg or "400" in err_msg:
            logger.info("  Thinking config khusus tidak didukung model, retry tanpa thinking_config...")
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    temperature=0.4,
                    max_output_tokens=1024,
                ),
                contents=prompt,
            )
            if response.text:
                return response.text.strip()
        raise

    raise RuntimeError("Gemini AI Studio menghasilkan response kosong.")


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
def generate_narasi(result, use_gemini: bool = True, polygons: dict | None = None, lang: str = "id") -> dict:
    """
    Generate narasi dari VulnerabilityResult.

    Urutan prioritas:
    1. Google AI Studio (GRATIS) — jika GEMINI_API_KEY ada di .env
    2. Vertex AI (berbayar) — jika GCP_PROJECT_ID + auth tersedia
    3. Template engine — selalu tersedia sebagai fallback

    Args:
        result:      VulnerabilityResult dari vulnerability.py
        use_gemini:  Coba Gemini dulu, fallback ke template jika gagal
        polygons:    GeoJSON vulnerability-map (opsional) untuk konteks per-kecamatan
        lang:        "id" (Bahasa Indonesia) atau "en" (English)

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
        source_type, client_or_model = gemini_init
        try:
            prompt = _build_prompt(result, polygons=polygons, lang=lang)
            if source_type == "aistudio":
                narasi = _generate_with_aistudio(client_or_model, prompt)
                logger.success(f"  Narasi Gemini AI Studio berhasil ({len(narasi)} chars)")
                return {
                    "narasi": narasi,
                    "source": "gemini_aistudio",
                    "model":  GEMINI_MODEL,
                }
            else:
                narasi = _generate_with_vertex(client_or_model, prompt)
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
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
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
