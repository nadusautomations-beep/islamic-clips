#!/usr/bin/env python3
"""Cut highlight clips from a source video: vertical crop + burned-in captions.

Usage:
    python3 scripts/make_clips.py source_videos/lecture1.mp4 \\
        --highlights source_videos/lecture1.highlights.json \\
        --transcript source_videos/lecture1.transcript.json \\
        --source-credit "Sheikh X — used with permission"

For each highlight, writes to clips/:
    <name>_01.mp4   vertical 1080x1920, captions burned in
    <name>_01.txt   suggested caption + hashtags + rights-credit line

Requires ffmpeg on PATH (with libass for subtitle burn-in).
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path


def format_srt_timestamp(seconds: float) -> str:
    ms = int(round(seconds * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def segments_in_range(segments, start, end):
    """Segments overlapping [start, end), re-timed to start at 0 for the clip's own SRT."""
    out = []
    for seg in segments:
        if seg["end"] <= start or seg["start"] >= end:
            continue
        out.append({
            "start": max(seg["start"], start) - start,
            "end": min(seg["end"], end) - start,
            "text": seg["text"],
        })
    return out


def escape_for_filter(path: str) -> str:
    """Escape a path for use inside an ffmpeg -vf filter argument."""
    return path.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")


def write_clip_srt(segments, out_path: Path) -> None:
    lines = []
    for i, seg in enumerate(segments, start=1):
        lines.append(str(i))
        lines.append(f"{format_srt_timestamp(seg['start'])} --> {format_srt_timestamp(seg['end'])}")
        lines.append(seg["text"].strip())
        lines.append("")
    out_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", help="Path to source video file")
    parser.add_argument("--highlights", required=True, help="Path to *.highlights.json")
    parser.add_argument("--transcript", required=True, help="Path to *.transcript.json (for captions)")
    parser.add_argument("--out-dir", default="clips", help="Output directory")
    parser.add_argument("--source-credit", required=True, help="Attribution line for the rights log, e.g. 'Sheikh X — used with permission'")
    args = parser.parse_args()

    source = Path(args.source)
    if not source.exists():
        sys.exit(f"Source file not found: {source}")

    highlights = json.loads(Path(args.highlights).read_text(encoding="utf-8"))
    transcript = json.loads(Path(args.transcript).read_text(encoding="utf-8"))["segments"]

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    base = source.stem

    for i, clip in enumerate(highlights, start=1):
        start, end = float(clip["start"]), float(clip["end"])
        clip_segments = segments_in_range(transcript, start, end)

        srt_path = out_dir / f"{base}_{i:02d}.srt"
        mp4_path = out_dir / f"{base}_{i:02d}.mp4"
        txt_path = out_dir / f"{base}_{i:02d}.txt"

        write_clip_srt(clip_segments, srt_path)

        vf = f"scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,subtitles='{escape_for_filter(str(srt_path))}'"
        cmd = [
            "ffmpeg", "-y",
            "-ss", str(start), "-to", str(end),
            "-i", str(source),
            "-vf", vf,
            "-c:v", "libx264", "-preset", "medium", "-crf", "20",
            "-c:a", "aac", "-b:a", "128k",
            str(mp4_path),
        ]
        print(f"[{i}/{len(highlights)}] Cutting {start:.1f}s-{end:.1f}s -> {mp4_path}", file=sys.stderr)
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(result.stderr[-2000:], file=sys.stderr)
            sys.exit(f"ffmpeg failed on clip {i}")

        hashtags = " ".join(clip.get("hashtags", []))
        txt_path.write_text(
            f"HOOK: {clip.get('hook', '')}\n\n"
            f"CAPTION: {clip.get('caption', '')}\n"
            f"{hashtags}\n\n"
            f"SOURCE/RIGHTS: {args.source_credit}\n",
            encoding="utf-8",
        )

    print(f"\nDone. {len(highlights)} clips in {out_dir}/", file=sys.stderr)
    print("Review each one before posting — trim/re-cut by hand if a boundary is awkward.", file=sys.stderr)


if __name__ == "__main__":
    main()
