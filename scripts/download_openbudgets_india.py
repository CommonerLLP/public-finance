"""
Download state budget PDFs from openbudgetsindia.org via the CKAN API.

Run this from your own terminal (NOT from Claude's sandbox — Cloudflare blocks
automated requests from cloud IPs).

Usage:
    python scripts/download_openbudgets_india.py --out data/openbudgets
    python scripts/download_openbudgets_india.py --out data/openbudgets --dry-run
    python scripts/download_openbudgets_india.py --out data/openbudgets --state gujarat

The script:
  1. Queries /api/3/action/package_search to enumerate all datasets
  2. Filters resources to PDF format only
  3. Downloads each PDF, skipping files already on disk (idempotent)
  4. Writes a manifest.jsonl alongside the downloads

Relevant to Minor Head 2205-105 (public libraries):
  Look for "expenditure" or "detailed demands" volumes in the downloaded files.
  Head 2205 is under "Social Services → Art, Culture and Youth Affairs".
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path
from urllib.parse import urlencode, quote


BASE = "https://openbudgetsindia.org"
API = f"{BASE}/api/3/action"
SLEEP_BETWEEN = 1.5  # seconds between downloads — be polite


# ── CKAN helpers ──────────────────────────────────────────────────────────────

def _ckan_get(endpoint: str, params: dict) -> dict:
    url = f"{API}/{endpoint}?{urlencode(params)}"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "CommonerLLP-budget-research/1.0",
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def list_all_packages() -> list[dict]:
    """Return all package metadata from the CKAN instance."""
    rows = 100
    start = 0
    packages = []
    while True:
        data = _ckan_get("package_search", {"rows": rows, "start": start})
        results = data["result"]["results"]
        packages.extend(results)
        if start + rows >= data["result"]["count"]:
            break
        start += rows
        time.sleep(0.5)
    return packages


# ── filtering ─────────────────────────────────────────────────────────────────

def _slug_state(pkg: dict) -> str:
    """Best-effort state name from a CKAN package."""
    # title often starts with "State Budget <Year> <State>" or "<State> Budget <Year>"
    groups = [g.get("name", "") for g in pkg.get("groups", [])]
    if groups:
        return groups[0].lower()
    return pkg.get("name", "unknown").lower()


def pdf_resources(pkg: dict) -> list[dict]:
    return [
        r for r in pkg.get("resources", [])
        if (r.get("format", "").upper() == "PDF"
            or r.get("url", "").lower().endswith(".pdf"))
    ]


# ── download ──────────────────────────────────────────────────────────────────

def _safe_filename(url: str, title: str) -> str:
    from urllib.parse import urlparse
    name = urlparse(url).path.split("/")[-1]
    if not name.lower().endswith(".pdf"):
        # fall back to slugified title
        name = title.lower().replace(" ", "-")
        name = "".join(c if c.isalnum() or c in "-_." else "-" for c in name)
        name = name.strip("-") + ".pdf"
    return name


def download_pdf(url: str, dest: Path, dry_run: bool) -> str:
    """Download url → dest. Returns 'skipped', 'downloaded', or 'failed'."""
    if dest.exists():
        return "skipped"
    if dry_run:
        print(f"    [dry-run] would download → {dest}")
        return "dry-run"
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "CommonerLLP-budget-research/1.0",
            },
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            dest.write_bytes(resp.read())
        return "downloaded"
    except Exception as exc:
        print(f"    ERROR downloading {url}: {exc}", file=sys.stderr)
        return "failed"


# ── main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--out", required=True, help="Output directory")
    parser.add_argument("--state", default=None, help="Filter by state slug (e.g. gujarat)")
    parser.add_argument("--dry-run", action="store_true", help="List files, don't download")
    parser.add_argument("--manifest", default=None, help="Path to write manifest.jsonl")
    args = parser.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    manifest_path = Path(args.manifest) if args.manifest else out / "manifest.jsonl"

    print("Fetching package list from openbudgetsindia.org …")
    try:
        packages = list_all_packages()
    except urllib.error.HTTPError as exc:
        print(f"HTTP {exc.code} from CKAN API — are you behind Cloudflare? Run from your own terminal.", file=sys.stderr)
        sys.exit(1)

    print(f"  {len(packages)} packages found")

    if args.state:
        packages = [p for p in packages if args.state.lower() in _slug_state(p)]
        print(f"  {len(packages)} packages after filtering for state={args.state!r}")

    manifest_records = []
    stats = {"downloaded": 0, "skipped": 0, "failed": 0, "dry-run": 0}

    for pkg in packages:
        state = _slug_state(pkg)
        title = pkg.get("title", pkg.get("name", "unknown"))
        resources = pdf_resources(pkg)
        if not resources:
            continue

        print(f"\n[{state}] {title} — {len(resources)} PDF(s)")
        state_dir = out / state

        for res in resources:
            url = res.get("url", "")
            rtitle = res.get("name") or res.get("description") or title
            fname = _safe_filename(url, rtitle)
            dest = state_dir / fname

            print(f"  {fname}")
            status = download_pdf(url, dest, args.dry_run)
            stats[status] = stats.get(status, 0) + 1

            manifest_records.append({
                "package_name": pkg.get("name"),
                "package_title": title,
                "state": state,
                "resource_id": res.get("id"),
                "resource_title": rtitle,
                "url": url,
                "dest": str(dest),
                "status": status,
            })

            if status == "downloaded":
                time.sleep(SLEEP_BETWEEN)

    # write manifest
    if not args.dry_run:
        manifest_path.write_text(
            "\n".join(json.dumps(r) for r in manifest_records) + "\n",
            encoding="utf-8",
        )
        print(f"\nManifest written → {manifest_path}")

    print(f"\nDone. downloaded={stats['downloaded']}  skipped={stats['skipped']}  failed={stats['failed']}")


if __name__ == "__main__":
    main()
