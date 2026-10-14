#!/usr/bin/env python3
"""Download and organize APPROVED Creative Commons b-roll candidates.

Takes the CSV produced (and reviewed/approved) by search_broll.py. For every
row with 'y' in the 'approve' column, this re-verifies the license directly
from the video itself via yt-dlp (not trusting the earlier API search result,
which can be stale) and only then downloads it. Anything that doesn't verify
as Creative Commons is refused — never downloaded "just in case" — and the
reason is printed so you can decide on a compliant alternative (contact the
creator for permission, or use a public-domain source like NASA/NOAA/USGS).

Must be run somewhere that can actually reach youtube.com (this sandbox
cannot — see the README). Run it on your own machine.

Usage:
    pip install yt-dlp
    python3 scripts/fetch_broll.py candidates_ocean.csv

Output, per approved+verified clip:
    broll/<topic>/<video_id>.mp4
    broll/<topic>/<video_id>_attribution.txt   (title, channel, url, license, required credit line)

Also writes fetch_log.csv recording what was downloaded, skipped, or refused
and why — your audit trail of source URLs and attribution details.
"""
import csv
import datetime
import sys
from pathlib import Path

try:
    import yt_dlp
except ImportError:
    sys.exit("Missing dependency. Run: pip install yt-dlp")


def verify_license(url: str) -> tuple[bool, str]:
    """Re-check the license straight from the video, not from the earlier search result."""
    opts = {"quiet": True, "no_warnings": True, "skip_download": True}
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)
    license_ = (info.get("license") or "").strip()
    is_cc = "creative commons" in license_.lower() or license_.lower() == "cc-by"
    return is_cc, license_ or "(no license metadata found)"


def download(url: str, out_path: Path) -> None:
    opts = {
        "quiet": True,
        "no_warnings": True,
        "format": "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]/best",
        "outtmpl": str(out_path),
        "merge_output_format": "mp4",
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([url])


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit(f"Usage: {sys.argv[0]} candidates.csv")

    csv_path = Path(sys.argv[1])
    if not csv_path.exists():
        sys.exit(f"Not found: {csv_path}")

    with csv_path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    approved = [r for r in rows if r.get("approve", "").strip().lower() == "y"]
    if not approved:
        sys.exit("No rows marked 'y' in the approve column. Nothing to do.")

    log_rows = []
    for i, row in enumerate(approved, start=1):
        url = row["url"]
        topic = row.get("topic", "misc") or "misc"
        video_id = row["video_id"]
        print(f"\n[{i}/{len(approved)}] Verifying license: {row['title'][:60]} ...", file=sys.stderr)

        try:
            is_cc, license_found = verify_license(url)
        except Exception as e:
            print(f"  COULD NOT VERIFY ({e}) — skipping, not downloading.", file=sys.stderr)
            log_rows.append({**row, "result": "error", "license_verified": "", "note": str(e)})
            continue

        if not is_cc:
            print(f"  REFUSED: license on record is '{license_found}', not Creative Commons.", file=sys.stderr)
            print(f"  Compliant alternatives: contact the channel for written permission,", file=sys.stderr)
            print(f"  or look for the same shot from a public-domain source (NASA/NOAA/USGS).", file=sys.stderr)
            log_rows.append({**row, "result": "refused_not_cc", "license_verified": license_found, "note": ""})
            continue

        out_dir = Path("broll") / topic
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"{video_id}.mp4"

        print(f"  Verified: {license_found}. Downloading...", file=sys.stderr)
        try:
            download(url, out_path)
        except Exception as e:
            print(f"  DOWNLOAD FAILED: {e}", file=sys.stderr)
            log_rows.append({**row, "result": "download_failed", "license_verified": license_found, "note": str(e)})
            continue

        attribution_path = out_dir / f"{video_id}_attribution.txt"
        attribution_path.write_text(
            f"TITLE: {row['title']}\n"
            f"CHANNEL: {row['channel']}\n"
            f"SOURCE URL: {url}\n"
            f"LICENSE: {license_found}\n"
            f"DOWNLOADED: {datetime.date.today().isoformat()}\n\n"
            f"Required credit line (CC BY requires attribution):\n"
            f"  \"{row['title']}\" by {row['channel']}, licensed under Creative Commons "
            f"Attribution license (reuse allowed). Source: {url}\n",
            encoding="utf-8",
        )
        print(f"  -> {out_path}", file=sys.stderr)
        log_rows.append({**row, "result": "downloaded", "license_verified": license_found, "note": str(out_path)})

    log_path = Path("fetch_log.csv")
    write_header = not log_path.exists()
    with log_path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(log_rows[0].keys()))
        if write_header:
            writer.writeheader()
        writer.writerows(log_rows)

    downloaded = sum(1 for r in log_rows if r["result"] == "downloaded")
    print(f"\n{downloaded}/{len(approved)} clips downloaded. Full record in {log_path}.", file=sys.stderr)


if __name__ == "__main__":
    main()
