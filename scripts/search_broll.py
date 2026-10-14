#!/usr/bin/env python3
"""Search YouTube for background b-roll footage, filtered to the ONLY license
YouTube itself recognizes as reusable: Creative Commons Attribution (CC BY 3.0).

Uses the official YouTube Data API v3 (videoLicense=creativeCommon) rather than
trusting the website's search filter or an uploader's description text — the
API's `license` field is what YouTube actually has on record for the video,
which is what matters for whether reuse is authorized.

This does NOT download anything. It just finds and lists candidates for you
(or Claude) to review, then you put the ones you approve into a CSV for
fetch_broll.py to verify-and-download.

Setup (one-time):
    1. console.cloud.google.com -> new project -> enable "YouTube Data API v3"
    2. Create an API key (APIs & Services -> Credentials)
    3. export YOUTUBE_API_KEY=your_key_here

Usage:
    python3 scripts/search_broll.py "ocean waves" --topic ocean --max-results 10
    python3 scripts/search_broll.py "mountain sunrise drone" --topic mountains

Output: candidates_<topic>.csv — review it, delete rows you don't want, then
hand the file to fetch_broll.py.

Important: even "Creative Commons" on YouTube means CC BY — attribution to the
original creator is still required, not a license-free free-for-all. Always
also open the video page yourself and confirm the license shown in the
description before using a clip (API data can be stale).
"""
import argparse
import csv
import os
import sys
import urllib.parse
import urllib.request
import json

API_BASE = "https://www.googleapis.com/youtube/v3"


def api_get(endpoint: str, params: dict) -> dict:
    url = f"{API_BASE}/{endpoint}?{urllib.parse.urlencode(params)}"
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        sys.exit(f"YouTube API error {e.code}: {body[:500]}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("query", help="Search keywords, e.g. 'ocean waves drone'")
    parser.add_argument("--topic", default=None, help="Topic label for the output filename/folder (default: derived from query)")
    parser.add_argument("--max-results", type=int, default=10, help="Max candidates to fetch (API default page size, max 50)")
    args = parser.parse_args()

    api_key = os.environ.get("YOUTUBE_API_KEY")
    if not api_key:
        sys.exit("Set YOUTUBE_API_KEY first (see this script's docstring for setup steps).")

    topic = args.topic or args.query.split()[0].lower()

    search_data = api_get("search", {
        "key": api_key,
        "part": "snippet",
        "q": args.query,
        "type": "video",
        "videoLicense": "creativeCommon",
        "maxResults": min(args.max_results, 50),
    })

    items = search_data.get("items", [])
    if not items:
        print("No Creative Commons results found for that query. Try different keywords,", file=sys.stderr)
        print("or check NASA/NOAA/USGS channels directly — US government footage is public", file=sys.stderr)
        print("domain regardless of YouTube's CC tag.", file=sys.stderr)
        return

    video_ids = [item["id"]["videoId"] for item in items]
    details_data = api_get("videos", {
        "key": api_key,
        "part": "snippet,contentDetails,status",
        "id": ",".join(video_ids),
    })
    details_by_id = {v["id"]: v for v in details_data.get("items", [])}

    rows = []
    for item in items:
        vid = item["id"]["videoId"]
        details = details_by_id.get(vid, {})
        license_ = details.get("status", {}).get("license", "unknown")
        snippet = details.get("snippet", item["snippet"])
        rows.append({
            "approve": "",  # you fill this in with "y" for clips you want fetch_broll.py to download
            "video_id": vid,
            "url": f"https://www.youtube.com/watch?v={vid}",
            "title": snippet.get("title", ""),
            "channel": snippet.get("channelTitle", ""),
            "license": license_,
            "duration": details.get("contentDetails", {}).get("duration", ""),
            "topic": topic,
            "notes": "",
        })

    out_path = f"candidates_{topic}.csv"
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    print(f"Found {len(rows)} Creative Commons candidates -> {out_path}", file=sys.stderr)
    for r in rows:
        flag = "" if r["license"] == "creativeCommon" else "  <-- license field doesn't say CC, double-check before approving!"
        print(f"  [{r['license']:14s}] {r['title'][:60]:60s} {r['url']}{flag}", file=sys.stderr)
    print(f"\nOpen {out_path}, watch the candidates, and put 'y' in the 'approve' column", file=sys.stderr)
    print("for the ones you want, then run fetch_broll.py on this file.", file=sys.stderr)


if __name__ == "__main__":
    main()
