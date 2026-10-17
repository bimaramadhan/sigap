"""
engine/db.py
────────────
Koneksi Postgres untuk katalog wilayah, laporan lapangan, dan cache baseline.

Lokal memakai Docker Compose. Produksi memakai Cloud SQL lewat DATABASE_URL
yang sama. Tidak ada penyimpanan JSON sebagai sumber data laporan.
"""

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import psycopg
from dotenv import load_dotenv
from loguru import logger
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

load_dotenv()

SCHEMA_PATH = Path(__file__).resolve().parents[1] / "db" / "schema.sql"
DEFAULT_URL = "postgresql://sigap:sigap@localhost:5432/sigap"
WEATHER_TTL = timedelta(hours=6)
BASELINE_TTL = timedelta(days=7)


def database_url() -> str:
    base = os.getenv("DATABASE_URL", DEFAULT_URL)
    # Tambahkan connect_timeout=3 agar gagal cepat jika Postgres tidak ada
    if "connect_timeout" not in base:
        sep = "&" if "?" in base else "?"
        base = f"{base}{sep}connect_timeout=3"
    return base


def connect():
    return psycopg.connect(database_url(), row_factory=dict_row)


_DB_AVAILABLE: bool = False


def db_available() -> bool:
    return _DB_AVAILABLE


def init_db() -> None:
    """Buat tabel dan isi wilayah sekali jika belum lengkap."""
    global _DB_AVAILABLE
    schema = SCHEMA_PATH.read_text(encoding="utf-8")
    statements = [part.strip() for part in schema.split(";") if part.strip()]
    with connect() as conn:
        for statement in statements:
            conn.execute(statement)
        conn.commit()
        _seed_wilayah(conn)
        _seed_wilayah_profil(conn)
        _import_legacy_reports(conn)
        conn.commit()
    _DB_AVAILABLE = True
    logger.info("Database siap")


def _seed_wilayah(conn) -> None:
    from engine.wilayah import all_rows

    rows = all_rows()
    if not rows:
        logger.warning("Katalog wilayah kosong — seed dilewati")
        return

    current = conn.execute("SELECT COUNT(*) AS n FROM wilayah").fetchone()["n"]
    if current == len(rows):
        logger.info(f"Wilayah sudah ada di database ({current} kode)")
        return

    logger.info(f"Mengisi wilayah: {current} baris di database, {len(rows)} di katalog")
    conn.execute("TRUNCATE wilayah")
    with conn.cursor() as cur:
        with cur.copy("COPY wilayah (kode, nama) FROM STDIN") as copy:
            for kode, nama in rows:
                copy.write_row((kode, nama))
    logger.success(f"Wilayah tersimpan: {len(rows)} kode")


def _seed_wilayah_profil(conn) -> None:
    """Simpan pusat, elevasi, dan bbox. Garis batas tidak disimpan."""
    from engine.wilayah_geo import all_profil

    rows = all_profil()
    if not rows:
        logger.warning("Profil wilayah kosong — seed dilewati")
        return

    current = conn.execute("SELECT COUNT(*) AS n FROM wilayah_profil").fetchone()["n"]
    if current == len(rows):
        logger.info(f"Profil wilayah sudah ada di database ({current} kode)")
        return

    logger.info(f"Mengisi profil wilayah: {current} baris di database, {len(rows)} di katalog")
    conn.execute("TRUNCATE wilayah_profil")
    with conn.cursor() as cur:
        with cur.copy(
            "COPY wilayah_profil "
            "(kode, nama, ibukota, lat, lng, elv, tz, luas, penduduk, "
            "bbox_west, bbox_south, bbox_east, bbox_north) FROM STDIN"
        ) as copy:
            for row in rows:
                west, south, east, north = row["bbox"]
                copy.write_row((
                    row["kode"],
                    row["nama"],
                    row["ibukota"],
                    row["lat"],
                    row["lng"],
                    row["elv"],
                    row["tz"],
                    row["luas"],
                    row["penduduk"],
                    west,
                    south,
                    east,
                    north,
                ))
    logger.success(f"Profil wilayah tersimpan: {len(rows)} kode")


def _import_legacy_reports(conn) -> None:
    """Pindahkan data/flood_reports.json sekali, kalau tabel masih kosong."""
    from engine.wilayah import canonical_kab

    existing = conn.execute("SELECT COUNT(*) AS n FROM flood_reports").fetchone()["n"]
    if existing:
        return

    path = Path("data") / "flood_reports.json"
    if not path.exists():
        return

    try:
        blob = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning(f"Lewati impor laporan lama: {exc}")
        return

    inserted = 0
    for raw_city, reports in blob.items():
        kab = canonical_kab(str(raw_city))
        if not kab or not isinstance(reports, list):
            continue
        for report in reports:
            desa_kode = report.get("desa_kode") or ""
            if not desa_kode:
                continue
            reported_at = report.get("reported_at")
            if not reported_at:
                continue
            conn.execute(
                """
                INSERT INTO flood_reports (
                    id, kab_kode, desa_kode, desa_name, kecamatan_kode, kecamatan,
                    flood_level, boost_score, boost_breakdown, reporter, notes,
                    reported_at, base_score_at_report
                ) VALUES (
                    %(id)s, %(kab_kode)s, %(desa_kode)s, %(desa_name)s, %(kecamatan_kode)s,
                    %(kecamatan)s, %(flood_level)s, %(boost_score)s, %(boost_breakdown)s,
                    %(reporter)s, %(notes)s, %(reported_at)s, NULL
                )
                ON CONFLICT (id) DO NOTHING
                """,
                {
                    "id": report.get("id") or f"{kab}_{inserted}",
                    "kab_kode": kab,
                    "desa_kode": desa_kode,
                    "desa_name": report.get("desa_name") or "",
                    "kecamatan_kode": report.get("kecamatan_kode") or "",
                    "kecamatan": report.get("kecamatan") or "",
                    "flood_level": report.get("flood_level") or "normal",
                    "boost_score": float(report.get("boost_score") or 0),
                    "boost_breakdown": Jsonb(report.get("boost_breakdown") or {}),
                    "reporter": report.get("reporter") or "Koordinator BPBD",
                    "notes": report.get("notes") or "",
                    "reported_at": reported_at,
                },
            )
            inserted += 1
    if inserted:
        logger.info(f"Impor {inserted} laporan dari flood_reports.json")


def peek_base_score(kab_kode: str) -> float | None:
    with connect() as conn:
        row = conn.execute(
            "SELECT base_score FROM inarisk_baselines WHERE kab_kode = %s",
            (kab_kode,),
        ).fetchone()
    if not row:
        return None
    return float(row["base_score"])


def load_baseline(kab_kode: str, with_polygons: bool = False) -> dict | None:
    columns = "kab_kode, features_json, base_score, fetched_at, source"
    if with_polygons:
        columns += ", polygons_json"
    with connect() as conn:
        return conn.execute(
            f"SELECT {columns} FROM inarisk_baselines WHERE kab_kode = %s",
            (kab_kode,),
        ).fetchone()


def save_baseline(
    kab_kode: str,
    features: dict,
    base_score: float,
    polygons: dict | None,
    source: str,
) -> dict:
    now = datetime.now(timezone.utc)
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO inarisk_baselines (
                kab_kode, features_json, base_score, polygons_json, fetched_at, source
            ) VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (kab_kode) DO UPDATE SET
                features_json = EXCLUDED.features_json,
                base_score = EXCLUDED.base_score,
                polygons_json = COALESCE(EXCLUDED.polygons_json, inarisk_baselines.polygons_json),
                fetched_at = EXCLUDED.fetched_at,
                source = EXCLUDED.source
            """,
            (
                kab_kode,
                Jsonb(features),
                base_score,
                Jsonb(polygons) if polygons is not None else None,
                now,
                source,
            ),
        )
        conn.commit()
    return {
        "kab_kode": kab_kode,
        "features_json": features,
        "base_score": base_score,
        "polygons_json": polygons,
        "fetched_at": now,
        "source": source,
    }


def save_polygons(kab_kode: str, polygons: dict) -> None:
    """
    Simpan atau perbarui data polygon GeoJSON ke inarisk_baselines.
    Jika baris kab_kode belum ada, dibuat baris baru.
    Jika sudah ada, kolom polygons_json diperbarui tanpa merusak features_json / base_score.
    """
    from engine.wilayah import canonical_kab

    kab = canonical_kab(kab_kode) or kab_kode
    now = datetime.now(timezone.utc)
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO inarisk_baselines (
                kab_kode, features_json, base_score, polygons_json, fetched_at, source
            ) VALUES (%s, '{}'::jsonb, 0.0, %s, %s, 'InaRisk BNPB GIS Service')
            ON CONFLICT (kab_kode) DO UPDATE SET
                polygons_json = EXCLUDED.polygons_json
            """,
            (kab, Jsonb(polygons), now),
        )
        conn.commit()
    logger.success(f"Polygon {kab} berhasil disimpan ke database inarisk_baselines")


def list_stale_baselines(limit: int) -> list[str]:
    cutoff = datetime.now(timezone.utc) - BASELINE_TTL
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT kab_kode FROM inarisk_baselines
            WHERE fetched_at < %s
            ORDER BY fetched_at ASC
            LIMIT %s
            """,
            (cutoff, limit),
        ).fetchall()
    return [row["kab_kode"] for row in rows]


def baseline_is_fresh(fetched_at: datetime) -> bool:
    if fetched_at.tzinfo is None:
        fetched_at = fetched_at.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) - fetched_at < BASELINE_TTL


def load_weather(kab_kode: str) -> dict | None:
    with connect() as conn:
        row = conn.execute(
            "SELECT payload_json, fetched_at FROM weather_cache WHERE kab_kode = %s",
            (kab_kode,),
        ).fetchone()
    if not row:
        return None
    fetched_at = row["fetched_at"]
    if fetched_at.tzinfo is None:
        fetched_at = fetched_at.replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc) - fetched_at > WEATHER_TTL:
        return None
    return row["payload_json"]


def save_weather(kab_kode: str, payload: dict) -> None:
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO weather_cache (kab_kode, payload_json, fetched_at)
            VALUES (%s, %s, %s)
            ON CONFLICT (kab_kode) DO UPDATE SET
                payload_json = EXCLUDED.payload_json,
                fetched_at = EXCLUDED.fetched_at
            """,
            (kab_kode, Jsonb(payload), datetime.now(timezone.utc)),
        )
        conn.commit()
