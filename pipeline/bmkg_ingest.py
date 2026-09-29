"""
pipeline/bmkg_ingest.py
───────────────────────
Mengambil peringatan dini cuaca dari BMKG Open Data API (CAP/XML).
Output: list alert yang relevan (potensi banjir) dengan detail kecamatan
        terdampak dan polygon wilayah.

Docs: https://data.bmkg.go.id/peringatan-dini-cuaca/
Rate limit: 60 req/menit per IP
"""

import os
import json
import time
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import requests
import xmltodict
from dotenv import load_dotenv
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────────
BMKG_RSS_URL   = os.getenv("BMKG_RSS_URL", "https://www.bmkg.go.id/alerts/nowcast/id")
CACHE_DIR      = Path(os.getenv("CACHE_DIR", "data/cache"))
CACHE_TTL_MIN  = int(os.getenv("CACHE_TTL_MINUTES", "30"))

# Mapping kota → provinsi (untuk filter alert per kota)
CITY_PROVINCE_MAP = {
    "semarang": "Jawa Tengah",
    "bekasi":   "Jawa Barat",
    "jakarta":  "DKI Jakarta",
    "bandung":  "Jawa Barat",
}

# Kata kunci yang menandakan potensi banjir di deskripsi BMKG
FLOOD_KEYWORDS = ["banjir", "genangan", "hujan lebat", "hujan sangat lebat"]

HEADERS = {
    "User-Agent": "SIGAP-FloodResponseSystem/1.0 (hackathon@sigap.id)"
}


# ── Data Models (sederhana, tanpa library tambahan) ───────────────────────────
class BMKGAlert:
    """Representasi satu peringatan dini cuaca dari BMKG."""

    def __init__(self, raw: dict):
        self.id          = raw.get("guid", {}).get("#text", "") if isinstance(raw.get("guid"), dict) else raw.get("guid", "")
        self.title       = raw.get("title", "")
        self.description = raw.get("description", "")
        self.pub_date    = raw.get("pubDate", "")
        self.cap_url     = raw.get("link", "")
        self.province    = self._extract_province()
        self.is_flood    = self._check_flood_relevance()

        # Diisi setelah fetch CAP detail
        self.kecamatan_list: list[str] = []
        self.polygons:       list[str] = []
        self.event_type:     str       = ""
        self.effective:      str       = ""
        self.expires:        str       = ""
        self.severity:       str       = ""  # Minor / Moderate / Severe / Extreme
        self.certainty:      str       = ""  # Observed / Likely / Possible

    def _extract_province(self) -> str:
        """Ekstrak nama provinsi dari judul alert."""
        # Format title: "Hujan Lebat disertai Petir di Jawa Tengah"
        if " di " in self.title:
            return self.title.split(" di ", 1)[-1].strip()
        return "Unknown"

    def _check_flood_relevance(self) -> bool:
        """Cek apakah alert ini relevan untuk risiko banjir."""
        text = (self.title + " " + self.description).lower()
        return any(kw in text for kw in FLOOD_KEYWORDS)

    def to_dict(self) -> dict:
        return {
            "id":              self.id,
            "title":           self.title,
            "province":        self.province,
            "description":     self.description,
            "pub_date":        self.pub_date,
            "cap_url":         self.cap_url,
            "is_flood":        self.is_flood,
            "event_type":      self.event_type,
            "effective":       self.effective,
            "expires":         self.expires,
            "severity":        self.severity,
            "certainty":       self.certainty,
            "kecamatan_list":  self.kecamatan_list,
            "polygons":        self.polygons,
        }

    def __repr__(self):
        return (
            f"BMKGAlert(province='{self.province}', "
            f"is_flood={self.is_flood}, "
            f"kecamatan={len(self.kecamatan_list)})"
        )


# ── Cache Helper ──────────────────────────────────────────────────────────────
def _cache_path(key: str) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    safe_key = hashlib.md5(key.encode()).hexdigest()[:12]
    return CACHE_DIR / f"bmkg_{safe_key}.json"


def _load_cache(key: str) -> Optional[dict]:
    path = _cache_path(key)
    if not path.exists():
        return None
    age_minutes = (time.time() - path.stat().st_mtime) / 60
    if age_minutes > CACHE_TTL_MIN:
        logger.debug(f"Cache expired ({age_minutes:.1f} min): {path.name}")
        return None
    with open(path) as f:
        return json.load(f)


def _save_cache(key: str, data: dict) -> None:
    with open(_cache_path(key), "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ── HTTP Helpers ──────────────────────────────────────────────────────────────
@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
def _get_xml(url: str) -> dict:
    """Fetch XML dari URL dan parse ke dict. Retry otomatis jika gagal."""
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    return xmltodict.parse(resp.content)


# ── CAP Detail Parser ─────────────────────────────────────────────────────────
def _fetch_cap_detail(alert: BMKGAlert) -> BMKGAlert:
    """
    Fetch detail CAP XML per provinsi.
    Mengisi: kecamatan_list, polygons, event_type, effective, expires,
             severity, certainty.
    """
    if not alert.cap_url:
        return alert

    cached = _load_cache(alert.cap_url)
    if cached:
        logger.debug(f"CAP cache hit: {alert.province}")
        alert.kecamatan_list = cached.get("kecamatan_list", [])
        alert.polygons       = cached.get("polygons", [])
        alert.event_type     = cached.get("event_type", "")
        alert.effective      = cached.get("effective", "")
        alert.expires        = cached.get("expires", "")
        alert.severity       = cached.get("severity", "")
        alert.certainty      = cached.get("certainty", "")
        return alert

    try:
        data = _get_xml(alert.cap_url)
        time.sleep(0.1)  # Gentle rate limiting — jangan spam BMKG

        # CAP XML bisa punya satu atau banyak <info> block
        alert_root = data.get("alert", {})
        info_block = alert_root.get("info", {})

        # Handle multiple info blocks (list) vs single (dict)
        if isinstance(info_block, list):
            # Ambil yang bahasa Indonesia
            info = next(
                (i for i in info_block if i.get("language", "").lower() in ("id", "id-id")),
                info_block[0]
            )
        else:
            info = info_block

        # Extract fields
        alert.event_type = info.get("event", "")
        alert.effective  = info.get("effective", "")
        alert.expires    = info.get("expires", "")
        alert.severity   = info.get("severity", "")
        alert.certainty  = info.get("certainty", "")

        # Extract area info (kecamatan dan polygon)
        area_block = info.get("area", [])
        if isinstance(area_block, dict):
            area_block = [area_block]

        kecamatan_list = []
        polygons       = []

        for area in area_block:
            area_desc = area.get("areaDesc", "")
            if area_desc:
                # BMKG menulis kecamatan sebagai nama KAPITAL, pisah koma
                kecamatan_list.extend(
                    [k.strip() for k in area_desc.split(",") if k.strip()]
                )
            polygon = area.get("polygon", "")
            if polygon:
                polygons.append(polygon)

        alert.kecamatan_list = kecamatan_list
        alert.polygons       = polygons

        # Save to cache
        _save_cache(alert.cap_url, {
            "kecamatan_list": kecamatan_list,
            "polygons":       polygons,
            "event_type":     alert.event_type,
            "effective":      alert.effective,
            "expires":        alert.expires,
            "severity":       alert.severity,
            "certainty":      alert.certainty,
        })

    except Exception as e:
        logger.warning(f"Gagal fetch CAP detail untuk {alert.province}: {e}")

    return alert


# ── Main Functions ────────────────────────────────────────────────────────────
def fetch_active_alerts(flood_only: bool = True) -> list[BMKGAlert]:
    """
    Fetch semua alert aktif dari BMKG RSS feed.

    Args:
        flood_only: Jika True, hanya return alert yang berpotensi banjir.

    Returns:
        List BMKGAlert, sudah diisi detail CAP.
    """
    logger.info("Fetching BMKG RSS feed...")

    cached = _load_cache("rss_feed")
    if cached:
        logger.info(f"RSS feed dari cache ({len(cached.get('items', []))} items)")
        raw_items = cached["items"]
    else:
        try:
            data      = _get_xml(BMKG_RSS_URL)
            channel   = data.get("rss", {}).get("channel", {})
            raw_items = channel.get("item", [])
            if isinstance(raw_items, dict):
                raw_items = [raw_items]  # Satu item → bungkus jadi list
            _save_cache("rss_feed", {"items": raw_items, "fetched_at": datetime.now(timezone.utc).isoformat()})
            logger.success(f"RSS feed: {len(raw_items)} alert ditemukan")
        except Exception as e:
            logger.error(f"Gagal fetch BMKG RSS: {e}")
            return []

    # Parse ke BMKGAlert objects
    alerts = [BMKGAlert(item) for item in raw_items]

    if flood_only:
        alerts = [a for a in alerts if a.is_flood]
        logger.info(f"Flood-relevant alerts: {len(alerts)}")

    # Fetch CAP detail untuk tiap alert
    logger.info("Fetching CAP detail per provinsi...")
    for i, alert in enumerate(alerts):
        logger.debug(f"  [{i+1}/{len(alerts)}] {alert.province}")
        _fetch_cap_detail(alert)

    return alerts


def get_alerts_for_province(province_keyword: str) -> list[BMKGAlert]:
    """
    Filter alert untuk provinsi tertentu.

    Args:
        province_keyword: Nama provinsi, case-insensitive.
                          Contoh: "jawa tengah", "jawa barat"

    Returns:
        List BMKGAlert untuk provinsi tersebut.
    """
    all_alerts = fetch_active_alerts(flood_only=True)
    keyword    = province_keyword.lower()
    return [a for a in all_alerts if keyword in a.province.lower()]


def save_alerts_json(alerts: list[BMKGAlert], path: Optional[str] = None) -> str:
    """Simpan alerts ke JSON file."""
    output_path = Path(path) if path else CACHE_DIR / "bmkg_alerts_latest.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "total":      len(alerts),
        "alerts":     [a.to_dict() for a in alerts],
    }
    with open(output_path, "w") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    logger.success(f"Saved {len(alerts)} alerts → {output_path}")
    return str(output_path)


# ── CLI Entry Point ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    from rich import print as rprint
    from rich.table import Table
    from rich import box

    logger.info("=== SIGAP — BMKG Ingest Pipeline ===")

    alerts = fetch_active_alerts(flood_only=True)

    if not alerts:
        logger.warning("Tidak ada alert banjir aktif saat ini.")
        logger.info("Tip: Coba jalankan di saat hujan musim — atau set DEMO_MODE=true")
    else:
        # Pretty print summary
        table = Table(title=f"BMKG Flood Alerts Aktif ({len(alerts)})", box=box.ROUNDED)
        table.add_column("Provinsi",   style="cyan",   no_wrap=True)
        table.add_column("Event",      style="yellow")
        table.add_column("Severity",   style="red")
        table.add_column("Kecamatan",  style="green",  justify="right")
        table.add_column("Expires",    style="white")

        for a in alerts:
            table.add_row(
                a.province,
                a.event_type or a.title[:40],
                a.severity or "N/A",
                str(len(a.kecamatan_list)),
                a.expires[:16] if a.expires else a.pub_date[:16],
            )

        rprint(table)

        # Save ke file
        out = save_alerts_json(alerts)
        rprint(f"\n[bold green]Output:[/bold green] {out}")
