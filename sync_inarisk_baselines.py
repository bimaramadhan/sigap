#!/usr/bin/env python3
"""
sync_inarisk_baselines.py
─────────────────────────
Script untuk iterasi seluruh kota/kabupaten di Indonesia, mengambil data risiko
dan baseline dari InaRisk BNPB GIS service, lalu menyimpannya ke database PostgreSQL
pada tabel inarisk_baselines (dan view inarisk_baseline).

Kredensial Default PostgreSQL:
  postgresql://sigap:sigap@localhost:5432/sigap

Contoh Penggunaan:
  # 1. Jalankan untuk semua kota (otomatis skip yang sudah tersimpan):
  .venv/bin/python sync_inarisk_baselines.py

  # 2. Jalankan hanya untuk 5 kota pertama (uji coba):
  .venv/bin/python sync_inarisk_baselines.py --limit 5

  # 3. Jalankan untuk provinsi tertentu:
  .venv/bin/python sync_inarisk_baselines.py --province "DKI Jakarta"

  # 4. Jalankan untuk satu kota tertentu dengan kode Kemendagri:
  .venv/bin/python sync_inarisk_baselines.py --city 33.74

  # 5. Force update meskipun sudah ada di database:
  .venv/bin/python sync_inarisk_baselines.py --force

  # 6. Lewati polygon kecamatan (jika hanya butuh skor & fitur InaRisk lebih cepat):
  .venv/bin/python sync_inarisk_baselines.py --skip-polygons
"""

import argparse
import os
import sys
import time
from datetime import datetime, timezone

# ── Argument Parsing ──────────────────────────────────────────────────────────
parser = argparse.ArgumentParser(
    description="Sinkronisasi baseline InaRisk BNPB ke PostgreSQL untuk semua kab/kota"
)
parser.add_argument(
    "--db",
    default=os.getenv("DATABASE_URL", "postgresql://sigap:sigap@localhost:5432/sigap"),
    help="PostgreSQL connection string (default: postgresql://sigap:sigap@localhost:5432/sigap)",
)
parser.add_argument(
    "--limit",
    type=int,
    default=None,
    help="Batasi jumlah kab/kota yang diproses",
)
parser.add_argument(
    "--province",
    type=str,
    default=None,
    help="Filter berdasarkan nama provinsi (misal: 'Jawa Tengah', 'DKI Jakarta')",
)
parser.add_argument(
    "--city",
    type=str,
    default=None,
    help="Proses hanya satu kab/kota berdasarkan kode (misal: '33.74') atau nama",
)
parser.add_argument(
    "--force",
    action="store_true",
    help="Paksa ambil ulang data meskipun sudah ada di database",
)
parser.add_argument(
    "--skip-polygons",
    action="store_true",
    help="Lewati pengambilan polygon kecamatan agar proses jauh lebih cepat",
)
parser.add_argument(
    "--delay",
    type=float,
    default=1.0,
    help="Jeda waktu antar kota dalam detik agar tidak membebani server InaRisk (default: 1.0)",
)

args = parser.parse_args()

# Set environment variable agar module engine.db menggunakan URL yang diberikan
os.environ["DATABASE_URL"] = args.db

from loguru import logger

# Konfigurasi log format yang bersih
logger.remove()
logger.add(
    sys.stdout,
    colorize=True,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}",
)

from engine.db import connect, init_db, save_baseline
from engine.places import resolve_bbox
from engine.vulnerability import calculate
from engine.wilayah import list_kabupaten, lookup_kab
from pipeline.inarisk_loader import get_all_features, to_vulnerability_format


def prepare_database():
    """Pastikan schema tabel dan view inarisk_baseline tersedia."""
    logger.info("Menghubungkan ke database dan memeriksa tabel...")
    init_db()

    with connect() as conn:
        # Buat view inarisk_baseline sebagai alias untuk inarisk_baselines
        conn.execute(
            "CREATE OR REPLACE VIEW inarisk_baseline AS SELECT * FROM inarisk_baselines;"
        )
        conn.commit()

        # Ambil daftar kab_kode yang sudah tersimpan
        rows = conn.execute("SELECT kab_kode FROM inarisk_baselines").fetchall()
        existing_kodes = {r["kab_kode"] for r in rows}

    logger.info(
        f"Database siap. Total data yang sudah ada di inarisk_baselines: {len(existing_kodes)}"
    )
    return existing_kodes


def sync_city(kab: dict, skip_polygons: bool = False) -> tuple[bool, str, float | None]:
    """
    Hit API InaRisk untuk satu kab/kota dan simpan ke database.
    Mengembalikan (success, message, base_score).
    """
    kab_kode = kab["kode"]
    label = kab["label"]
    province = kab["province"]

    bbox = resolve_bbox(kab_kode)
    if not bbox or len(bbox) != 4:
        return False, f"Batas peta (bbox) untuk {label} ({kab_kode}) tidak ditemukan", None

    # 1. Fetch data fitur dari InaRisk BNPB GIS Service
    raw = get_all_features(
        kab_kode,
        force_refresh=True,
        bbox=bbox,
        label=label,
        province=province,
    )
    features = to_vulnerability_format(kab_kode, raw)
    features["config"] = {
        "label": label,
        "province": province,
        "bbox": bbox,
    }

    # 2. Hitung base score
    base = calculate(kab_kode, features)
    source = (
        "fallback"
        if features.get("_is_sample")
        else (features.get("_source") or "InaRisk BNPB GIS Service")
    )

    # 3. Ambil polygon kecamatan jika tidak di-skip
    polygons = None
    if not skip_polygons:
        try:
            from pipeline.inarisk_polygon import get_flood_polygons

            polygons = get_flood_polygons(kab_kode, force_refresh=True, bbox=bbox)
        except Exception as exc:
            logger.warning(f"  [{kab_kode}] Polygon gagal, fitur & skor tetap disimpan: {exc}")

    # 4. Simpan ke database PostgreSQL (tabel inarisk_baselines)
    save_baseline(
        kab_kode=kab_kode,
        features=features,
        base_score=base.score,
        polygons=polygons,
        source=source,
    )

    return True, f"Tersimpan (source: {source})", base.score


def main():
    logger.info("=== SINKRONISASI INARISK BASELINE KE POSTGRESQL ===")
    logger.info(f"Target DB: {args.db}")

    existing_kodes = prepare_database()

    # Ambil semua kabupaten/kota dari katalog Kemendagri
    cities = list_kabupaten()
    total_in_catalog = len(cities)
    logger.info(f"Total kab/kota di katalog wilayah: {total_in_catalog}")

    # Saring berdasarkan argumen
    if args.province:
        cities = [
            c for c in cities if args.province.lower() in c.get("province", "").lower()
        ]
        logger.info(f"Setelah filter provinsi '{args.province}': {len(cities)} kab/kota")

    if args.city:
        target = args.city.lower().strip()
        cities = [
            c
            for c in cities
            if target == c.get("kode", "").lower()
            or target in c.get("label", "").lower()
        ]
        logger.info(f"Setelah filter kota '{args.city}': {len(cities)} kab/kota")

    if args.limit:
        cities = cities[: args.limit]
        logger.info(f"Dibatasi ke {args.limit} kab/kota pertama")

    if not cities:
        logger.warning("Tidak ada kab/kota yang memenuhi kriteria filter.")
        return

    # Tracking statistik
    total_to_process = len(cities)
    success_count = 0
    skip_count = 0
    failed_count = 0
    failed_items = []

    start_time = time.time()
    logger.info(f"Memulai iterasi untuk {total_to_process} kab/kota...\n")

    for idx, kab in enumerate(cities, start=1):
        kab_kode = kab["kode"]
        label = kab["label"]
        province = kab["province"]

        # Cek apakah sudah ada di DB
        if not args.force and kab_kode in existing_kodes:
            logger.info(
                f"[{idx}/{total_to_process}] (SKIP) {label} ({kab_kode}) sudah ada di database."
            )
            skip_count += 1
            continue

        logger.info(
            f"[{idx}/{total_to_process}] (SYNC) Mengambil InaRisk untuk {label} ({kab_kode}), {province}..."
        )
        t0 = time.time()

        try:
            ok, msg, score = sync_city(kab, skip_polygons=args.skip_polygons)
            elapsed = time.time() - t0
            if ok:
                success_count += 1
                existing_kodes.add(kab_kode)
                logger.success(
                    f"[{idx}/{total_to_process}] (OK) {label} | Base Score: {score} | Waktu: {elapsed:.1f}s | {msg}"
                )
            else:
                failed_count += 1
                failed_items.append({"kode": kab_kode, "label": label, "error": msg})
                logger.error(f"[{idx}/{total_to_process}] (FAIL) {label} | Error: {msg}")

        except Exception as exc:
            failed_count += 1
            failed_items.append({"kode": kab_kode, "label": label, "error": str(exc)})
            logger.error(
                f"[{idx}/{total_to_process}] (ERROR) {label} ({kab_kode}) gagal: {exc}"
            )

        # Jeda antar request jika diperlukan
        if args.delay > 0 and idx < total_to_process:
            time.sleep(args.delay)

    total_time = time.time() - start_time
    logger.info("\n" + "=" * 50)
    logger.info("RINGKASAN SINKRONISASI")
    logger.info("=" * 50)
    logger.info(f"Total diproses    : {total_to_process}")
    logger.info(f"Berhasil          : {success_count}")
    logger.info(f"Dilewati (cached) : {skip_count}")
    logger.info(f"Gagal             : {failed_count}")
    logger.info(f"Total Waktu       : {total_time/60:.2f} menit")

    if failed_items:
        logger.warning("\nDaftar yang gagal:")
        for f in failed_items:
            logger.warning(f"  - [{f['kode']}] {f['label']}: {f['error']}")

    logger.info("Selesai.\n")


if __name__ == "__main__":
    main()
