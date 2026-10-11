#!/usr/bin/env python3
"""Combine a recitation audio file with a looping scenic background video,
crop to vertical 1080x1920, and burn in the ayah text + translation.

This is for the "recitation over beautiful scenery" format (not the lecture
highlight-clipping workflow in transcribe.py/find_highlights.py/make_clips.py).

Usage (manual caption text, works fully offline):
    python3 scripts/make_recitation_clip.py \\
        --audio source_videos/audio/dosari_fatiha.mp3 \\
        --background source_videos/backgrounds/sunset_clouds.mp4 \\
        --reciter "Yasser Al-Dosari" \\
        --reference "Al-Fatihah 1-7" \\
        --arabic-text "بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ" \\
        --translation "In the name of Allah, the Most Gracious, the Most Merciful"

Usage (auto-fetch ayah text + translation from api.alquran.cloud — needs
internet access to that host, which this sandbox's network policy blocks,
but will work on a normal machine/CI runner):
    python3 scripts/make_recitation_clip.py \\
        --audio source_videos/audio/dosari_fatiha.mp3 \\
        --background source_videos/backgrounds/sunset_clouds.mp4 \\
        --reciter "Yasser Al-Dosari" \\
        --surah 1 --ayah-start 1 --ayah-end 7

Output: clips/<audio-basename>.mp4 + a .txt sidecar with caption/hashtags/credit.

Brand template (same on every clip, so the page looks consistent):
  - Ayah text:    Amiri (apt install fonts-hosny-amiri if missing — NOTE: use the
                  plain "Amiri" family, not "Amiri Quran": that variant only
                  shapes correctly with the exact Tanzil Uthmani Unicode source
                  text and renders as broken/disconnected glyphs on anything else)
  - Translation:  Inter
  - Credit:       Inter SemiBold, top-right corner
See the BRAND_* constants below to change any of this in one place.
"""
import argparse
import json
import subprocess
import sys
import urllib.request
import urllib.error
from pathlib import Path

ALQURAN_API = "https://api.alquran.cloud/v1/surah/{surah}/{edition}"

# --- Brand template: change these to restyle every clip consistently ---
BRAND_ARABIC_FONT = "Amiri"
BRAND_ARABIC_SIZE = 64
BRAND_TRANSLATION_FONT = "Inter"
BRAND_TRANSLATION_SIZE = 40
BRAND_CREDIT_FONTFILE = "/usr/share/fonts/opentype/inter/Inter-SemiBold.otf"
BRAND_CREDIT_SIZE = 26
BRAND_VIDEO_W = 1080
BRAND_VIDEO_H = 1920


def escape_for_filter(text: str) -> str:
    return text.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")


def ffprobe_duration(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, check=True,
    )
    return float(out.stdout.strip())


def fetch_ayah_range(surah: int, ayah_start: int, ayah_end: int, edition: str, timeout: int = 10) -> str:
    url = ALQURAN_API.format(surah=surah, edition=edition)
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    ayahs = data["data"]["ayahs"]
    picked = [a["text"] for a in ayahs if ayah_start <= a["numberInSurah"] <= ayah_end]
    if not picked:
        raise ValueError(f"No ayahs {ayah_start}-{ayah_end} found in surah {surah} (edition {edition})")
    return " ".join(picked)


def _ass_timestamp(seconds: float) -> str:
    cs = int(round(seconds * 100))
    h, cs = divmod(cs, 360000)
    m, cs = divmod(cs, 6000)
    s, cs = divmod(cs, 100)
    return f"{h:d}:{m:02d}:{s:02d}.{cs:02d}"


def _ass_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("\n", "\\N").replace("{", "(").replace("}", ")")


def write_ass(arabic_text: str, translation: str | None, duration: float, out_path: Path) -> None:
    """Two independently-styled lines (brand-consistent fonts/sizes), stacked
    bottom-up so they never overlap regardless of how many lines each wraps to."""
    end = _ass_timestamp(duration)
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {BRAND_VIDEO_W}
PlayResY: {BRAND_VIDEO_H}
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Arabic,{BRAND_ARABIC_FONT},{BRAND_ARABIC_SIZE},&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,3,1,2,60,60,{300 if translation else 160},1
Style: Translation,{BRAND_TRANSLATION_FONT},{BRAND_TRANSLATION_SIZE},&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,1,2,80,80,150,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = [f"Dialogue: 0,0:00:00.00,{end},Arabic,,0,0,0,,{_ass_escape(arabic_text)}"]
    if translation:
        events.append(f"Dialogue: 0,0:00:00.00,{end},Translation,,0,0,0,,{_ass_escape(translation)}")
    out_path.write_text(header + "\n".join(events) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--audio", required=True, help="Path to recitation audio file")
    parser.add_argument("--background", required=True, help="Path to looping scenic background video (any length; it's looped/trimmed to match the audio)")
    parser.add_argument("--reciter", required=True, help="Reciter name, for the credit overlay and rights sidecar")
    parser.add_argument("--reference", default=None, help="Human-readable reference for the sidecar, e.g. 'Al-Fatihah 1-7' (defaults to surah:ayah if given)")
    parser.add_argument("--surah", type=int, default=None, help="Surah number, to auto-fetch ayah text (needs api.alquran.cloud reachable)")
    parser.add_argument("--ayah-start", type=int, default=None)
    parser.add_argument("--ayah-end", type=int, default=None)
    parser.add_argument("--arabic-edition", default="quran-uthmani", help="alquran.cloud edition id for Arabic text")
    parser.add_argument("--translation-edition", default="en.sahih", help="alquran.cloud edition id for translation (set to '' to skip translation line)")
    parser.add_argument("--arabic-text", default=None, help="Manual Arabic caption text (skips the API call)")
    parser.add_argument("--translation", default=None, help="Manual translation caption text (skips the API call)")
    parser.add_argument("--out-dir", default="clips", help="Output directory")
    parser.add_argument("--out-name", default=None, help="Output basename, no extension (default: the audio file's basename — pass this explicitly when batching multiple clips that reuse the same audio file, so outputs don't overwrite each other)")
    args = parser.parse_args()

    audio = Path(args.audio)
    background = Path(args.background)
    if not audio.exists():
        sys.exit(f"Audio file not found: {audio}")
    if not background.exists():
        sys.exit(f"Background video not found: {background}")

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    arabic_text = args.arabic_text
    translation = args.translation

    if arabic_text is None and args.surah is not None and args.ayah_start is not None:
        ayah_end = args.ayah_end or args.ayah_start
        try:
            arabic_text = fetch_ayah_range(args.surah, args.ayah_start, ayah_end, args.arabic_edition)
            print(f"Fetched Arabic text for surah {args.surah}:{args.ayah_start}-{ayah_end}", file=sys.stderr)
        except Exception as e:
            print(f"WARNING: could not fetch Arabic text ({e}). Proceeding without burned-in ayah text.", file=sys.stderr)

        if translation is None and args.translation_edition:
            try:
                translation = fetch_ayah_range(args.surah, args.ayah_start, ayah_end, args.translation_edition)
            except Exception as e:
                print(f"WARNING: could not fetch translation ({e}). Proceeding without translation line.", file=sys.stderr)

    reference = args.reference
    if reference is None and args.surah is not None and args.ayah_start is not None:
        ayah_end = args.ayah_end or args.ayah_start
        reference = f"Surah {args.surah}:{args.ayah_start}-{ayah_end}"
    reference = reference or "Reference not provided"

    duration = ffprobe_duration(audio)
    base = args.out_name or audio.stem
    mp4_path = out_dir / f"{base}.mp4"
    txt_path = out_dir / f"{base}.txt"

    vf_parts = [
        f"scale={BRAND_VIDEO_W}:{BRAND_VIDEO_H}:force_original_aspect_ratio=increase",
        f"crop={BRAND_VIDEO_W}:{BRAND_VIDEO_H}",
    ]

    if arabic_text:
        ass_path = out_dir / f"{base}.ass"
        write_ass(arabic_text, translation, duration, ass_path)
        vf_parts.append(f"subtitles='{escape_for_filter(str(ass_path))}'")

    # Credit sits in the top corner, clear of the bottom-anchored captions
    # regardless of how many lines the ayah/translation text wraps to.
    credit_text = escape_for_filter(f"{args.reciter}")
    vf_parts.append(
        f"drawtext=fontfile={BRAND_CREDIT_FONTFILE}:"
        f"text='{credit_text}':fontcolor=white:fontsize={BRAND_CREDIT_SIZE}:box=1:boxcolor=black@0.4:boxborderw=8:"
        "x=w-text_w-30:y=50"
    )

    cmd = [
        "ffmpeg", "-y",
        "-stream_loop", "-1", "-i", str(background),
        "-i", str(audio),
        "-map", "0:v", "-map", "1:a",
        "-shortest",
        "-vf", ",".join(vf_parts),
        "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-c:a", "aac", "-b:a", "128k",
        str(mp4_path),
    ]
    print(f"Rendering {mp4_path} ({duration:.1f}s)...", file=sys.stderr)
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(result.stderr[-2000:], file=sys.stderr)
        sys.exit("ffmpeg failed")

    txt_path.write_text(
        f"REFERENCE: {reference}\n"
        f"RECITER: {args.reciter}\n\n"
        f"CAPTION: {reference} — recited by {args.reciter}\n"
        "#quran #recitation #islam #reminder\n\n"
        f"RIGHTS NOTE: confirm you have permission to post/monetize {args.reciter}'s recitation "
        "before publishing this clip. See STRATEGY.md.\n",
        encoding="utf-8",
    )

    print(f"\nDone. {mp4_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
