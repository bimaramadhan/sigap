"""
run_poc.py
──────────
Single entry point untuk SIGAP POC.

Menjalankan seluruh pipeline dan menampilkan summary lengkap:
  1. ✅ BMKG — Peringatan dini cuaca aktif
  2. ✅ Earth Engine — Geospatial features (atau sample data jika belum auth)
  3. ✅ Vulnerability Score — Analisis risiko terbobot
  4. ✅ Narasi AI — Briefing bahasa Indonesia
  5. ✅ API Check — Verifikasi semua endpoints siap

Usage:
  python run_poc.py                   # Default: kota Semarang
  python run_poc.py bekasi            # Kota lain
  python run_poc.py semarang --api    # Jalankan juga FastAPI server

Output: Summary di terminal + file data/poc_result_{city}.json
"""

import sys
import json
import time
import argparse
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from loguru import logger
from rich import print as rprint
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.rule import Rule
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import box

load_dotenv()
console = Console()

CACHE_DIR  = Path("data/cache")
OUTPUT_DIR = Path("data")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ── Step Runners ──────────────────────────────────────────────────────────────
def run_step_bmkg() -> dict:
    """Step 1: Fetch BMKG alerts."""
    from pipeline.bmkg_ingest import fetch_active_alerts, save_alerts_json

    all_alerts   = fetch_active_alerts(flood_only=False)
    flood_alerts = [a for a in all_alerts if a.is_flood]

    save_alerts_json(flood_alerts)

    return {
        "status":        "ok",
        "total_alerts":  len(all_alerts),
        "flood_alerts":  len(flood_alerts),
        "provinces":     list({a.province for a in flood_alerts})[:5],
        "sample_alert":  flood_alerts[0].to_dict() if flood_alerts else None,
    }


def run_step_ee(city: str) -> dict:
    """Step 2: Load Earth Engine features."""
    from pipeline.ee_loader import get_all_features

    features   = get_all_features(city)
    is_sample  = features.get("_is_sample", True)

    return {
        "status":            "ok",
        "is_sample":         is_sample,
        "data_source":       "SAMPLE DATA" if is_sample else "Google Earth Engine (LIVE)",
        "elevation_mean":    features["dem"]["elevation_mean"],
        "elevation_min":     features["dem"]["elevation_min"],
        "flood_ratio_10yr":  features["flood_hazard"]["10yr"]["flood_ratio"],
        "historical_events": features["flood_history"]["historical_events"],
        "total_population":  features["population"]["total_population"],
        "est_vulnerable":    features["population"]["est_vulnerable"],
        "features":          features,
    }


def run_step_vulnerability(city: str, ee_features: dict) -> dict:
    """Step 3: Hitung vulnerability score."""
    from engine.vulnerability import calculate

    result = calculate(city, ee_features)

    return {
        "status":          "ok",
        "score":           result.score,
        "category":        result.category,
        "breakdown":       result.score_breakdown(),
        "priority_actions":result.priority_actions,
        "resource_needs":  result.resource_needs,
        "result_obj":      result,  # Untuk step berikutnya
    }


def run_step_narasi(vuln_result) -> dict:
    """Step 4: Generate narasi AI."""
    from engine.narrator import generate_narasi

    output = generate_narasi(vuln_result, use_gemini=True)

    return {
        "status": "ok",
        "source": output["source"],
        "model":  output["model"],
        "narasi": output["narasi"],
    }


# ── Display Functions ─────────────────────────────────────────────────────────
def display_header(city: str):
    rprint(Panel.fit(
        "[bold blue]SIGAP[/bold blue] — "
        "Sistem Integrasi Geospasial Aksi Penanggulangan Bencana\n"
        f"[dim]POC Data Validation | Kota: {city.upper()} | "
        f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}[/dim]",
        border_style="blue",
    ))


def display_bmkg(result: dict):
    rprint(Rule("[bold cyan]STEP 1 — BMKG Peringatan Dini Cuaca[/bold cyan]"))

    status_icon = "✅" if result["status"] == "ok" else "❌"
    rprint(f"\n{status_icon} Status: [green]OK[/green]")
    rprint(f"   Total alert aktif : [cyan]{result['total_alerts']}[/cyan]")
    rprint(f"   Alert banjir      : [red]{result['flood_alerts']}[/red]")

    if result["provinces"]:
        rprint(f"   Provinsi terdampak: {', '.join(result['provinces'])}")

    if result["sample_alert"]:
        a = result["sample_alert"]
        rprint(Panel.fit(
            f"[bold]{a['title']}[/bold]\n"
            f"Severity : {a.get('severity', 'N/A')}\n"
            f"Kecamatan: {len(a.get('kecamatan_list', []))} wilayah\n"
            f"Berlaku  : {a.get('effective', 'N/A')[:16]}\n"
            f"Berakhir : {a.get('expires', 'N/A')[:16]}",
            title="Contoh Alert Banjir",
            border_style="yellow",
        ))
    else:
        rprint("   [dim]Tidak ada alert banjir aktif saat ini "
               "(normal di musim kemarau)[/dim]")

    rprint(f"   📁 Cache: [dim]data/cache/bmkg_alerts_latest.json[/dim]\n")


def display_ee(result: dict):
    rprint(Rule("[bold cyan]STEP 2 — Earth Engine Geospatial Data[/bold cyan]"))

    source_label = (
        "[yellow]⚠️  SAMPLE DATA[/yellow] (EE belum authenticated)"
        if result["is_sample"]
        else "[green]✅ LIVE Earth Engine[/green]"
    )

    rprint(f"\n{source_label}")

    tbl = Table(box=box.SIMPLE, show_header=True, header_style="bold cyan")
    tbl.add_column("Dataset",    style="cyan", min_width=25)
    tbl.add_column("Nilai",      justify="right", style="white")
    tbl.add_column("Satuan",     style="dim")
    tbl.add_column("Source",     style="dim")

    tbl.add_row("Elevasi rata-rata",     str(result["elevation_mean"]),       "meter",    "SRTM 30m")
    tbl.add_row("Elevasi minimum",       str(result["elevation_min"]),        "meter",    "SRTM 30m")
    tbl.add_row("Flood ratio (10yr RP)", f"{result['flood_ratio_10yr']:.1%}", "% area",  "JRC GloFAS")
    tbl.add_row("Banjir historis",       str(result["historical_events"]),    "events",   "GFD 2000-2018")
    tbl.add_row("Total populasi",        f"{result['total_population']:,}",   "jiwa",     "WorldPop")
    tbl.add_row("Est. populasi rentan",  f"{result['est_vulnerable']:,}",     "jiwa",     "WorldPop + BPS")

    rprint(tbl)

    if result["is_sample"]:
        rprint("   [yellow]→ Untuk data real: jalankan 'earthengine authenticate'[/yellow]")
    rprint(f"   📁 Cache: [dim]data/cache/ee_semarang_all_features.json[/dim]\n")


def display_vulnerability(result: dict):
    rprint(Rule("[bold cyan]STEP 3 — Vulnerability Score[/bold cyan]"))

    score  = result["score"]
    cat    = result["category"]
    color  = "red" if score >= 75 else "yellow" if score >= 50 else "cyan" if score >= 25 else "green"

    bar_len = 35
    filled  = round(score / 100 * bar_len)
    bar     = "█" * filled + "░" * (bar_len - filled)

    rprint(f"\n[{color}]{bar}[/{color}]  [{color}][bold]{score}/100[/bold][/{color}]")
    rprint(f"[bold]{cat}[/bold]\n")

    # Breakdown
    bd = result["breakdown"]
    tbl = Table(box=box.SIMPLE, show_header=True, header_style="bold cyan")
    tbl.add_column("Komponen",   style="cyan", min_width=20)
    tbl.add_column("Kontribusi", justify="right", style="yellow")
    tbl.add_column("Bar",        min_width=15)

    for name, key in [
        ("Flood Hazard",   "hazard"),
        ("Pop. Exposure",  "exposure"),
        ("Pop. Rentan",    "vulnerable"),
        ("Hist. Banjir",   "history"),
        ("Low Elevation",  "elevation"),
    ]:
        val    = bd.get(key, 0)
        b_len  = 15
        b_fill = round(val / 30 * b_len)   # max kontribusi ~30 poin
        bar_s  = "▓" * b_fill + "░" * (b_len - b_fill)
        tbl.add_row(name, f"+{val}", bar_s)

    rprint(tbl)
    rprint(f"   📁 Score tersimpan di output file\n")


def display_narasi(result: dict, city_label: str):
    rprint(Rule("[bold cyan]STEP 4 — Narasi AI Bahasa Indonesia[/bold cyan]"))

    source_label = (
        f"[green]Gemini {result['model']}[/green]"
        if result["source"] == "gemini"
        else "[yellow]Template Engine (Gemini belum aktif)[/yellow]"
    )
    rprint(f"\nGenerated via: {source_label}\n")

    rprint(Panel(
        result["narasi"],
        title=f"[bold]Briefing Situasi — {city_label}[/bold]",
        border_style="blue",
        padding=(1, 2),
    ))


def display_summary(steps: dict, city: str, output_file: str):
    rprint(Rule("[bold green]SUMMARY[/bold green]"))

    tbl = Table(box=box.ROUNDED, show_header=True, header_style="bold")
    tbl.add_column("Step",     style="cyan", min_width=30)
    tbl.add_column("Status",   justify="center")
    tbl.add_column("Keterangan", style="dim")

    rows = [
        ("BMKG Alerts",           steps["bmkg"]["status"],
         f"{steps['bmkg']['flood_alerts']} alert banjir aktif"),

        ("Earth Engine Features", steps["ee"]["status"],
         steps["ee"]["data_source"]),

        ("Vulnerability Score",   steps["vuln"]["status"],
         f"{steps['vuln']['score']}/100 — {steps['vuln']['category']}"),

        ("Narasi AI",             steps["narasi"]["status"],
         f"via {steps['narasi']['source']} ({steps['narasi']['model']})"),
    ]

    for step_name, status, note in rows:
        icon = "✅" if status == "ok" else "❌"
        tbl.add_row(step_name, icon, note)

    rprint(tbl)
    rprint(f"\n📁 Full output: [bold]{output_file}[/bold]")
    rprint(f"\n[bold green]POC selesai![/bold green] Semua data tersedia.\n")

    # Next steps hint
    is_sample = steps["ee"]["is_sample"]
    gemini_ok = steps["narasi"]["source"] == "gemini"

    if is_sample or not gemini_ok:
        rprint("[bold yellow]Langkah berikutnya:[/bold yellow]")
        if is_sample:
            rprint("  1. Daftar Earth Engine: [link]https://code.earthengine.google.com/register[/link]")
            rprint("     Lalu jalankan: [bold]earthengine authenticate[/bold]")
            rprint("     Set [bold]GCP_PROJECT_ID[/bold] di file .env")
        if not gemini_ok:
            rprint("  2. Aktifkan Gemini:")
            rprint("     [bold]gcloud auth application-default login[/bold]")
            rprint("     Set [bold]GCP_PROJECT_ID[/bold] di file .env")


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="SIGAP POC Runner")
    parser.add_argument("city", nargs="?", default="semarang",
                        help="Kota target (semarang/bekasi/jakarta)")
    parser.add_argument("--api", action="store_true",
                        help="Jalankan FastAPI server setelah POC selesai")
    args   = parser.parse_args()
    city   = args.city.lower()

    display_header(city)

    steps   = {}
    vuln_r  = None
    label   = city.title()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
        console=console,
    ) as progress:

        # ── Step 1: BMKG ─────────────────────────────────────────────────────
        task = progress.add_task("Fetching BMKG alerts...", total=None)
        try:
            steps["bmkg"] = run_step_bmkg()
        except Exception as e:
            logger.error(f"BMKG step failed: {e}")
            steps["bmkg"] = {"status": "error", "error": str(e),
                              "total_alerts": 0, "flood_alerts": 0,
                              "provinces": [], "sample_alert": None}
        progress.remove_task(task)
        display_bmkg(steps["bmkg"])

        # ── Step 2: Earth Engine ─────────────────────────────────────────────
        task = progress.add_task("Loading Earth Engine data...", total=None)
        try:
            steps["ee"] = run_step_ee(city)
            label = (steps["ee"]["features"].get("config", {})
                     .get("label", city.title()))
        except Exception as e:
            logger.error(f"EE step failed: {e}")
            steps["ee"] = {"status": "error", "error": str(e),
                           "is_sample": True, "data_source": "ERROR",
                           "elevation_mean": 0, "elevation_min": 0,
                           "flood_ratio_10yr": 0, "historical_events": 0,
                           "total_population": 0, "est_vulnerable": 0,
                           "features": {}}
        progress.remove_task(task)
        display_ee(steps["ee"])

        # ── Step 3: Vulnerability ────────────────────────────────────────────
        task = progress.add_task("Calculating vulnerability score...", total=None)
        try:
            steps["vuln"] = run_step_vulnerability(city, steps["ee"]["features"])
            vuln_r = steps["vuln"]["result_obj"]
        except Exception as e:
            logger.error(f"Vulnerability step failed: {e}")
            steps["vuln"] = {"status": "error", "error": str(e),
                             "score": 0, "category": "ERROR",
                             "breakdown": {}, "priority_actions": [],
                             "resource_needs": {}, "result_obj": None}
        progress.remove_task(task)
        if steps["vuln"]["status"] == "ok":
            display_vulnerability(steps["vuln"])

        # ── Step 4: Narasi ───────────────────────────────────────────────────
        task = progress.add_task("Generating narasi AI...", total=None)
        try:
            if vuln_r:
                steps["narasi"] = run_step_narasi(vuln_r)
            else:
                steps["narasi"] = {"status": "skip", "source": "none",
                                   "model": "none", "narasi": "Skipped (vuln error)"}
        except Exception as e:
            logger.error(f"Narasi step failed: {e}")
            steps["narasi"] = {"status": "error", "error": str(e),
                                "source": "none", "model": "none",
                                "narasi": f"Error: {e}"}
        progress.remove_task(task)
        if steps["narasi"].get("status") == "ok":
            display_narasi(steps["narasi"], label)

    # ── Save output ───────────────────────────────────────────────────────────
    output = {
        "city":         city,
        "city_label":   label,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "bmkg": {k: v for k, v in steps["bmkg"].items() if k != "sample_alert"},
        "ee":   {k: v for k, v in steps["ee"].items()   if k != "features"},
        "vulnerability": {k: v for k, v in steps["vuln"].items()  if k != "result_obj"},
        "narasi": steps["narasi"],
    }
    out_path = OUTPUT_DIR / f"poc_result_{city}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    display_summary(steps, city, str(out_path))

    # ── Optional: jalankan API ────────────────────────────────────────────────
    if args.api:
        rprint("\n[bold]Menjalankan FastAPI server...[/bold]")
        rprint("Buka: [link]http://localhost:8080/docs[/link]\n")
        subprocess.run([
            sys.executable, "-m", "uvicorn",
            "api.main:app", "--reload", "--port", "8080"
        ])


if __name__ == "__main__":
    main()
