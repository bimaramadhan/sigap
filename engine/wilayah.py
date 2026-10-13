"""
engine/wilayah.py
─────────────────
Indeks kode wilayah Kemendagri dari knowledge/geografi/wilayah.sql.

Tingkat wilayah = jumlah bagian kode yang dipisah titik:
  33            provinsi
  33.74         kab/kota
  33.74.02      kecamatan
  33.74.02.1001 desa/kelurahan

Indeks dibaca sekali saat modul diimpor. Database diisi dari indeks yang sama.
"""

import re
from pathlib import Path

from loguru import logger

SQL_PATH = Path(__file__).resolve().parents[1] / "knowledge" / "geografi" / "wilayah.sql"

# Slug lama tetap mengarah ke satu kab/kota. Jakarta tidak lagi digabung.
LEGACY_SLUGS: dict[str, str] = {
    "semarang": "33.74",
    "bekasi":   "32.75",
    "jakarta":  "31.71",
    "surabaya": "35.78",
}

_ROW_RE = re.compile(r"\('([^']*)','((?:[^']|'')*)'\)")

_by_kode: dict[str, str] = {}
_villages_by_kab: dict[str, list[dict]] = {}


def _load() -> None:
    """Parse INSERT wilayah menjadi indeks kode dan daftar desa per kab/kota."""
    global _by_kode, _villages_by_kab
    if not SQL_PATH.exists():
        logger.warning(f"wilayah.sql tidak ditemukan: {SQL_PATH}")
        _by_kode = {}
        _villages_by_kab = {}
        return

    text = SQL_PATH.read_text(encoding="utf-8")
    by_kode: dict[str, str] = {}
    for kode, nama in _ROW_RE.findall(text):
        by_kode[kode] = nama.replace("''", "'").strip()

    villages_by_kab: dict[str, list[dict]] = {}
    for kode, nama in by_kode.items():
        parts = kode.split(".")
        if len(parts) != 4:
            continue
        kab_kode = ".".join(parts[:2])
        kec_kode = ".".join(parts[:3])
        villages_by_kab.setdefault(kab_kode, []).append({
            "kode":               kode,
            "nama":               nama,
            "kecamatan_kode":     kec_kode,
            "kecamatan":          by_kode.get(kec_kode, ""),
            "kota_administrasi":  by_kode.get(kab_kode, ""),
        })

    for rows in villages_by_kab.values():
        rows.sort(key=lambda v: (v["kecamatan"].lower(), v["nama"].lower(), v["kode"]))

    _by_kode = by_kode
    _villages_by_kab = villages_by_kab
    logger.info(
        f"Wilayah loaded: {len(by_kode)} kode, "
        f"{sum(len(v) for v in villages_by_kab.values())} desa/kelurahan"
    )


_load()


class VillageNotInCity(ValueError):
    """Kode desa tidak ada di bawah kab/kota yang dipilih."""


def all_rows() -> list[tuple[str, str]]:
    """Seluruh pasangan kode-nama untuk seed database."""
    return list(_by_kode.items())


def canonical_kab(value: str) -> str | None:
    """
    Terima kode kab/kota (33.74) atau slug lama (semarang).
    Return None jika bukan kab/kota di katalog.
    """
    raw = (value or "").strip()
    if not raw:
        return None
    legacy = LEGACY_SLUGS.get(raw.lower())
    if legacy:
        return legacy
    if raw.count(".") == 1 and raw in _by_kode:
        return raw
    return None


def province_of(kab_kode: str) -> str:
    kab = canonical_kab(kab_kode)
    if not kab:
        return ""
    return _by_kode.get(kab.split(".")[0], "")


def province_matches(alert_province: str, wilayah_province: str) -> bool:
    """Cocokkan nama provinsi BMKG dengan nama Kemendagri."""
    alert = (alert_province or "").lower()
    wilayah = (wilayah_province or "").lower()
    if not alert or not wilayah:
        return False
    if wilayah in alert or alert in wilayah:
        return True
    if "jakarta" in wilayah and "jakarta" in alert:
        return True
    return False


def _city_record(kode: str, nama: str, prov: str) -> dict:
    from engine.wilayah_geo import get_profil
    profil = get_profil(kode) or {}
    return {
        "id":       kode,
        "kode":     kode,
        "label":    nama,
        "province": prov,
        "bbox":     profil.get("bbox"),
        "lat":      profil.get("lat"),
        "lng":      profil.get("lng"),
    }


def lookup_kab(kab_kode: str) -> dict | None:
    kab = canonical_kab(kab_kode)
    if not kab:
        return None
    return _city_record(kab, _by_kode[kab], province_of(kab))


def list_kabupaten(query: str = "") -> list[dict]:
    """Semua kab/kota, opsional disaring nama, provinsi, atau kode."""
    q = (query or "").lower().strip()
    rows = []
    for kode, nama in _by_kode.items():
        if kode.count(".") != 1:
            continue
        prov = _by_kode.get(kode.split(".")[0], "")
        if q and q not in nama.lower() and q not in prov.lower() and q not in kode:
            continue
        rows.append(_city_record(kode, nama, prov))
    rows.sort(key=lambda row: (row["province"].lower(), row["label"].lower(), row["kode"]))
    return rows


def _group_villages(kab_kode: str) -> list[dict]:
    groups: dict[str, dict] = {}
    for village in _villages_by_kab.get(kab_kode, []):
        kec_kode = village["kecamatan_kode"]
        group = groups.get(kec_kode)
        if group is None:
            group = {
                "kecamatan":         village["kecamatan"],
                "kecamatan_kode":    kec_kode,
                "kota_administrasi": village["kota_administrasi"],
                "villages":          [],
            }
            groups[kec_kode] = group
        group["villages"].append({
            "kode": village["kode"],
            "nama": village["nama"],
        })
    return sorted(groups.values(), key=lambda g: (g["kecamatan"].lower(), g["kecamatan_kode"]))


def get_villages(kab_kode: str) -> list[dict]:
    """
    Desa/kelurahan untuk satu kab/kota, dikelompokkan per kecamatan.

    Tiap grup:
      kecamatan, kecamatan_kode, kota_administrasi,
      villages: [{kode, nama}, ...]
    """
    kab = canonical_kab(kab_kode)
    if not kab:
        return []
    return _group_villages(kab)


def sample_adm4(kab_kode: str, limit: int = 16) -> list[dict]:
    """Satu desa per kecamatan, paling banyak `limit`, tersebar merata."""
    kab = canonical_kab(kab_kode)
    if not kab:
        return []

    by_kec: dict[str, dict] = {}
    for village in _villages_by_kab.get(kab, []):
        by_kec.setdefault(village["kecamatan_kode"], village)
    kecs = [by_kec[kode] for kode in sorted(by_kec)]
    if not kecs:
        return []

    if len(kecs) > limit:
        step = len(kecs) / limit
        picked = [kecs[min(len(kecs) - 1, int(i * step))] for i in range(limit)]
    else:
        picked = kecs

    return [
        {"adm4": row["kode"], "kecamatan": row["kecamatan"], "area": row["nama"]}
        for row in picked
    ]


def resolve_village(kab_kode: str, desa_kode: str) -> dict:
    """
    Selesaikan desa ke kecamatan induk.

    Raises VillageNotInCity jika kode bukan desa di kab/kota itu.
    """
    kab = canonical_kab(kab_kode)
    desa_kode = (desa_kode or "").strip()
    parts = desa_kode.split(".")
    in_city = bool(kab) and desa_kode.startswith(kab + ".")
    if not kab or len(parts) != 4 or not in_city or desa_kode not in _by_kode:
        raise VillageNotInCity(
            f"Kode desa '{desa_kode}' tidak termasuk wilayah {kab_kode}"
        )

    kec_kode = ".".join(parts[:3])
    return {
        "kode":              desa_kode,
        "nama":              _by_kode[desa_kode],
        "kecamatan_kode":    kec_kode,
        "kecamatan":         _by_kode.get(kec_kode, ""),
        "kota_administrasi": _by_kode.get(kab, ""),
        "kab_kode":          kab,
    }
