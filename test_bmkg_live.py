"""
Quick test: hit BMKG API langsung dan tampilkan hasil real.
Jalankan: python test_bmkg_live.py
"""
import requests
import xmltodict

BMKG_URL = "https://www.bmkg.go.id/alerts/nowcast/id"
FLOOD_KW = ["banjir", "hujan lebat", "hujan sangat lebat", "genangan"]

def run():
    print("=" * 55)
    print("  SIGAP — Test BMKG Live Data")
    print("=" * 55)

    resp = requests.get(BMKG_URL, timeout=15,
                        headers={"User-Agent": "SIGAP/1.0"})
    print(f"\nHTTP Status  : {resp.status_code}")
    print(f"Content size : {len(resp.content):,} bytes")

    data  = xmltodict.parse(resp.content)
    items = data.get("rss", {}).get("channel", {}).get("item", [])
    if isinstance(items, dict):
        items = [items]

    flood = [
        i for i in items
        if any(k in (i.get("description", "") + i.get("title", "")).lower()
               for k in FLOOD_KW)
    ]

    print(f"\nTotal alert aktif : {len(items)}")
    print(f"Alert banjir      : {len(flood)}")

    if flood:
        print("\nAlert banjir aktif saat ini:")
        for a in flood:
            print(f"\n  Judul   : {a.get('title', '')}")
            print(f"  Waktu   : {a.get('pubDate', '')[:30]}")
            desc = a.get("description", "")
            print(f"  Preview : {desc[:120]}...")
    else:
        print("\nTidak ada alert banjir aktif saat ini.")
        print("(Normal di musim kemarau — data tetap real-time dari BMKG)")

    print("\n" + "=" * 55)
    print("BMKG pipeline siap digunakan — tidak butuh setup apapun.")
    print("=" * 55)

if __name__ == "__main__":
    run()
