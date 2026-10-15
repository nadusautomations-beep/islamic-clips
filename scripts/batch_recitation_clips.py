#!/usr/bin/env python3
"""Render several recitation clips in one run, from a simple CSV job list.

Keeps every clip on the exact same brand template (make_recitation_clip.py's
BRAND_* constants) so a day's worth of uploads look consistent.

Usage:
    python3 scripts/batch_recitation_clips.py jobs.csv
    python3 scripts/batch_recitation_clips.py jobs.csv --fonts-dir Amiri

CSV columns (header row required; only audio/background/reciter are mandatory
per row — everything else is optional and passed straight through to
make_recitation_clip.py when present):
    audio,background,reciter,reference,surah,ayah_start,ayah_end,arabic_text,
    translation,translation_edition,end_time,fade_duration,ayah_times

Leave surah/ayah_start/ayah_end blank if you're passing arabic_text/translation
directly; leave arabic_text/translation blank if you want them auto-fetched
from the surah/ayah fields (requires api.alquran.cloud to be reachable).
Set translation_edition to the literal text NONE to skip translation entirely
for that row (passes --translation-edition "").

--fonts-dir is a command-line flag (not a CSV column) since it's normally the
same folder for every clip in a batch — e.g. wherever you extracted Amiri's
.ttf files.

Example row:
    source_videos/audio/dosari_fatiha.mp3,source_videos/backgrounds/sunset.mp4,Yasser Al-Dosari,Al-Fatihah 1-7,1,1,7,,,,,,

A sample jobs.csv is in this repo's root — copy and edit it for your own batch.
"""
import argparse
import csv
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("jobs_csv")
    parser.add_argument("--fonts-dir", default=None, help="Folder containing font files, applied to every clip in the batch")
    parser.add_argument("--background-pool", default=None, help="Folder of pre-approved background videos to use for any row that leaves its 'background' column blank — one random pick per row. Set this up once (see fetch_broll.py) and never choose a background per clip again.")
    args = parser.parse_args()

    jobs_path = Path(args.jobs_csv)
    if not jobs_path.exists():
        sys.exit(f"Job list not found: {jobs_path}")

    with jobs_path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    if not rows:
        sys.exit("No jobs found in CSV (check the header row).")

    failures = []
    for i, row in enumerate(rows, start=1):
        audio = row.get("audio", "").strip()
        background = row.get("background", "").strip() or args.background_pool
        reciter = row.get("reciter", "").strip()
        if not audio or not background or not reciter:
            print(f"[{i}/{len(rows)}] SKIPPED: audio and reciter are required, and background "
                  f"(either this row's own, or --background-pool)", file=sys.stderr)
            failures.append(i)
            continue

        # Unique per row even if two jobs reuse the same audio file (e.g. a
        # shared intro clip) — otherwise their outputs would overwrite each other.
        out_name = f"{i:02d}_{Path(audio).stem}"

        cmd = [
            sys.executable, str(SCRIPT_DIR / "make_recitation_clip.py"),
            "--audio", audio,
            "--background", background,
            "--reciter", reciter,
            "--out-name", out_name,
        ]
        if row.get("reference", "").strip():
            cmd += ["--reference", row["reference"].strip()]
        if row.get("surah", "").strip():
            cmd += ["--surah", row["surah"].strip()]
        if row.get("ayah_start", "").strip():
            cmd += ["--ayah-start", row["ayah_start"].strip()]
        if row.get("ayah_end", "").strip():
            cmd += ["--ayah-end", row["ayah_end"].strip()]
        if row.get("arabic_text", "").strip():
            cmd += ["--arabic-text", row["arabic_text"].strip()]
        if row.get("translation", "").strip():
            cmd += ["--translation", row["translation"].strip()]
        translation_edition = row.get("translation_edition", "").strip()
        if translation_edition:
            cmd += ["--translation-edition", "" if translation_edition.upper() == "NONE" else translation_edition]
        if row.get("end_time", "").strip():
            cmd += ["--end-time", row["end_time"].strip()]
        if row.get("fade_duration", "").strip():
            cmd += ["--fade-duration", row["fade_duration"].strip()]
        if row.get("ayah_times", "").strip():
            cmd += ["--ayah-times", row["ayah_times"].strip()]
        if args.fonts_dir:
            cmd += ["--fonts-dir", args.fonts_dir]

        print(f"\n[{i}/{len(rows)}] {Path(audio).stem} ...", file=sys.stderr)
        result = subprocess.run(cmd)
        if result.returncode != 0:
            print(f"[{i}/{len(rows)}] FAILED (see ffmpeg/script output above)", file=sys.stderr)
            failures.append(i)

    ok = len(rows) - len(failures)
    print(f"\n{ok}/{len(rows)} clips rendered.", file=sys.stderr)
    if failures:
        print(f"Rows that failed: {failures}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
