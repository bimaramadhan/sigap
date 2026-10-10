"""
engine/wilayah.py
─────────────────
Indeks kode wilayah Kemendagri dari knowledge/geografi/wilayah.sql.

Tingkat wilayah = jumlah bagian kode yang dipisah titik:
  33            provinsi
  33.74         kab/kota
  33.74.02      kecamatan
  33.74.02.1001 desa/kelurahan

Tidak memakai database. File SQL dibaca sekali saat modul diimpor.
"""

import re
from pathlib import Path

from loguru import logger

SQL_PATH = Path(__file__).resolve().parents[1] / "knowledge" / "geografi" / "wilayah.sql"

# Slug analitik SIGAP → prefix kode kab/kota di wilayah.sql
CITY_WILAYAH_PREFIXES: dict[str, list[str]] = {
    "semarang": ["33.74"],
    "bekasi":   ["32.75"],
    "jakarta":  ["31.71", "31.72", "31.73", "31.74", "31.75"],
    "surabaya": ["35.78"],
}

_ROW_RE = re.compile(r"\('([^']*)','((?:[^']|'')*)'\)")

# kode → nama (sudah di-trim)
_by_kode: dict[str, str] = {}
# prefix kab/kota → daftar desa
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
    logger.info(f"Wilayah loaded: {len(by_kode)} kode, {sum(len(v) for v in villages_by_kab.values())} desa/kelurahan")


_load()


class VillageNotInCity(ValueError):
    """Kode desa tidak ada di bawah prefix kab/kota untuk slug tersebut."""


def get_villages(city: str) -> list[dict]:
    """
    Desa/kelurahan untuk satu slug kota, dikelompokkan per kecamatan.

    Tiap grup:
      kecamatan, kecamatan_kode, kota_administrasi,
      villages: [{kode, nama}, ...]
    """
    prefixes = CITY_WILAYAH_PREFIXES.get(city.lower(), [])
    groups: dict[str, dict] = {}

    for prefix in prefixes:
        for village in _villages_by_kab.get(prefix, []):
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

    ordered = sorted(groups.values(), key=lambda g: (g["kecamatan"].lower(), g["kecamatan_kode"]))
    return ordered


def resolve_village(city: str, desa_kode: str) -> dict:
    """
    Selesaikan desa ke kecamatan induk.

    Raises VillageNotInCity jika kode bukan desa di prefix kota itu.
    """
    city = city.lower()
    desa_kode = (desa_kode or "").strip()
    prefixes = CITY_WILAYAH_PREFIXES.get(city, [])
    parts = desa_kode.split(".")

    in_city = any(desa_kode.startswith(prefix + ".") for prefix in prefixes)
    if len(parts) != 4 or not in_city or desa_kode not in _by_kode:
        raise VillageNotInCity(
            f"Kode desa '{desa_kode}' tidak termasuk wilayah {city}"
        )

    kec_kode = ".".join(parts[:3])
    kab_kode = ".".join(parts[:2])
    return {
        "kode":              desa_kode,
        "nama":              _by_kode[desa_kode],
        "kecamatan_kode":    kec_kode,
        "kecamatan":         _by_kode.get(kec_kode, ""),
        "kota_administrasi": _by_kode.get(kab_kode, ""),
    }
