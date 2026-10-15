"""
engine/city_profile.py
───────────────────────
Merangkai "profil kota" secara OTOMATIS dari data yang sudah ada di sistem,
menggantikan markdown manual per kota yang tidak scalable untuk 514 kab/kota.

Sumber data (semua sudah tersedia, tidak perlu input manual):
  - VulnerabilityResult   → skor, populasi, elevasi, flood ratio, boosts
  - polygon kecamatan     → kecamatan hazard tertinggi, distribusi risiko
  - wilayah_geo           → elevasi, luas, penduduk, pesisir atau tidak
  - laporan lapangan      → kecamatan yang sedang dilaporkan banjir

Output: teks ringkas bahasa Indonesia yang di-inject ke prompt Gemini,
sehingga narasi jadi kontekstual per kota TANPA menulis file per kota.

Dipakai oleh engine/narrator.py.
"""

from loguru import logger


def _rank_kecamatan(polygons: dict, top_n: int = 5) -> list[dict]:
    """Ambil kecamatan dengan skor/hazard tertinggi dari GeoJSON vulnerability map."""
    feats = (polygons or {}).get("features", [])
    rows = []
    for f in feats:
        p = f.get("properties", {})
        rows.append({
            "name":   p.get("name", "?"),
            "score":  p.get("vuln_score", p.get("hazard", 0) * 100),
            "hazard": p.get("hazard", 0),
            "cat":    p.get("vuln_category", ""),
            "pop":    p.get("population_est", 0),
        })
    rows.sort(key=lambda r: r["score"], reverse=True)
    return rows[:top_n]


def build_city_context(result, polygons: dict | None = None, geo: dict | None = None) -> str:
    """
    Rangkai profil kota dari data numerik menjadi teks untuk prompt Gemini.

    Args:
        result:   VulnerabilityResult (punya score, elevation_min, total_population, dll)
        polygons: GeoJSON dari /vulnerability-map (opsional — kecamatan ranking)
        geo:      dict dari engine.wilayah_geo.get_profil (opsional — elevasi/pesisir)

    Returns:
        String multi-baris. Kosong kalau tidak ada data yang bisa dirangkai.
    """
    lines: list[str] = []

    label = getattr(result, "city_label", "") or getattr(result, "city", "")
    lines.append(f"PROFIL WILAYAH {label.upper()} (dirangkai otomatis dari data InaRisk BNPB):")

    # ── Karakteristik geografis dari data elevasi ─────────────────────────────
    elev_min  = getattr(result, "elevation_min", None)
    elev_mean = getattr(result, "elevation_mean", None)
    if elev_min is not None:
        if elev_min < 0:
            lines.append(
                f"- Wilayah pesisir dengan elevasi minimum {elev_min}m (DI BAWAH permukaan laut) "
                f"→ rawan banjir rob/pasang laut, bisa tergenang tanpa hujan."
            )
        elif elev_min < 3:
            lines.append(
                f"- Elevasi minimum {elev_min}m (sangat rendah) → rawan genangan & rob di area pesisir."
            )
        else:
            lines.append(f"- Elevasi minimum {elev_min}m, rata-rata {elev_mean}m.")

    # ── Distribusi risiko antar kecamatan ─────────────────────────────────────
    top = _rank_kecamatan(polygons, top_n=5) if polygons else []
    if top:
        n_awas  = sum(1 for r in top if "AWAS" in r["cat"])
        n_siaga = sum(1 for r in top if "SIAGA" in r["cat"])
        total_kec = len((polygons or {}).get("features", []))

        lines.append(
            f"- Dari {total_kec} kecamatan, yang paling berisiko: " +
            ", ".join(f"{r['name']} (skor {r['score']:.0f})" for r in top[:3]) + "."
        )
        if n_awas or n_siaga:
            lines.append(
                f"- Terdapat {n_awas} kecamatan status AWAS dan {n_siaga} status SIAGA di antara zona teratas — "
                f"prioritaskan kecamatan ini untuk evakuasi & deploy sumber daya."
            )

    # ── Beban populasi rentan ─────────────────────────────────────────────────
    total_pop = getattr(result, "total_population", 0)
    est_vuln  = getattr(result, "est_vulnerable", 0)
    if total_pop:
        lines.append(
            f"- Total populasi {total_pop:,} jiwa, estimasi {est_vuln:,} warga rentan "
            f"(lansia + balita) yang perlu prioritas evakuasi."
        )

    # ── Rekam jejak banjir ────────────────────────────────────────────────────
    hist = getattr(result, "historical_events", 0)
    if hist and hist >= 5:
        lines.append(f"- Rekam jejak {hist} kejadian banjir historis (2000-2018) — area dengan riwayat banjir tinggi.")

    # Kalau cuma header saja (tidak ada data), kembalikan kosong
    if len(lines) <= 1:
        return ""

    return "\n".join(lines)


def build_sop_context(max_chars: int = 6000) -> str:
    """
    Load SOP universal dari knowledge/sop/*.md (berlaku untuk SEMUA kota).
    Ini knowledge yang ditulis sekali, dipakai semua kota — scalable.

    Hanya file SOP inti yang dimuat agar prompt tidak terlalu panjang.
    """
    from pathlib import Path

    sop_dir = Path(__file__).resolve().parents[1] / "knowledge" / "sop"
    if not sop_dir.exists():
        return ""

    # Urutan prioritas — file paling actionable dulu
    priority = [
        "level_siaga_banjir.md",
        "prioritas_evakuasi.md",
        "kebutuhan_resource.md",
    ]

    chunks: list[str] = []
    total = 0
    for fname in priority:
        fpath = sop_dir / fname
        if not fpath.exists():
            continue
        try:
            text = fpath.read_text(encoding="utf-8").strip()
        except Exception as exc:
            logger.warning(f"  Gagal baca SOP {fname}: {exc}")
            continue
        if total + len(text) > max_chars:
            text = text[: max_chars - total]
        chunks.append(f"### {fname}\n{text}")
        total += len(text)
        if total >= max_chars:
            break

    return "\n\n".join(chunks)
