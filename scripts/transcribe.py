#!/usr/bin/env python3
"""Transcribe a source video/audio file to a timestamped JSON + SRT.

Usage:
    python3 scripts/transcribe.py source_videos/lecture1.mp4
    python3 scripts/transcribe.py source_videos/lecture1.mp4 --model small --language en

Output (next to the source file, same basename):
    <name>.transcript.json   list of {id, start, end, text}
    <name>.srt
"""
import argparse
import json
import sys
from pathlib import Path


def format_srt_timestamp(seconds: float) -> str:
    ms = int(round(seconds * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def write_srt(segments, out_path: Path) -> None:
    lines = []
    for i, seg in enumerate(segments, start=1):
        lines.append(str(i))
        lines.append(f"{format_srt_timestamp(seg['start'])} --> {format_srt_timestamp(seg['end'])}")
        lines.append(seg["text"].strip())
        lines.append("")
    out_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", help="Path to source audio/video file")
    parser.add_argument("--model", default="small", help="faster-whisper model size (tiny/base/small/medium/large-v3)")
    parser.add_argument("--language", default=None, help="Force a language code (e.g. en, ar). Default: auto-detect.")
    args = parser.parse_args()

    source = Path(args.source)
    if not source.exists():
        sys.exit(f"Source file not found: {source}")

    from faster_whisper import WhisperModel

    print(f"Loading model '{args.model}' (CPU)...", file=sys.stderr)
    model = WhisperModel(args.model, device="cpu", compute_type="int8")

    print(f"Transcribing {source}...", file=sys.stderr)
    segments_iter, info = model.transcribe(str(source), language=args.language, vad_filter=True)

    segments = []
    for i, seg in enumerate(segments_iter):
        segments.append({"id": i, "start": seg.start, "end": seg.end, "text": seg.text.strip()})
        print(f"  [{seg.start:7.2f} - {seg.end:7.2f}] {seg.text.strip()}", file=sys.stderr)

    out_json = source.with_suffix("").with_suffix(".transcript.json")
    out_srt = source.with_suffix("").with_suffix(".srt")

    out_json.write_text(json.dumps({"language": info.language, "segments": segments}, ensure_ascii=False, indent=2), encoding="utf-8")
    write_srt(segments, out_srt)

    print(f"\nDetected language: {info.language}", file=sys.stderr)
    print(f"Wrote {out_json}", file=sys.stderr)
    print(f"Wrote {out_srt}", file=sys.stderr)


if __name__ == "__main__":
    main()
