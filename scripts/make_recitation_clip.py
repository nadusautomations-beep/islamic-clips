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


def fetch_surah_ayahs(surah: int, edition: str, timeout: int = 10) -> dict[int, str]:
    """Returns {numberInSurah: text} for every ayah in the surah, one API call."""
    url = ALQURAN_API.format(surah=surah, edition=edition)
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return {a["numberInSurah"]: a["text"] for a in data["data"]["ayahs"]}


def fetch_ayah_range(surah: int, ayah_start: int, ayah_end: int, edition: str, timeout: int = 10) -> str:
    ayahs = fetch_surah_ayahs(surah, edition, timeout)
    picked = [text for num, text in sorted(ayahs.items()) if ayah_start <= num <= ayah_end]
    if not picked:
        raise ValueError(f"No ayahs {ayah_start}-{ayah_end} found in surah {surah} (edition {edition})")
    return " ".join(picked)


def parse_ayah_times(spec: str) -> list[tuple[int, float]]:
    """Parse '35:0,36:8.5,37:17,38:25' -> [(35, 0.0), (36, 8.5), (37, 17.0), (38, 25.0)], sorted by time."""
    pairs = []
    for chunk in spec.split(","):
        ayah_str, time_str = chunk.split(":")
        pairs.append((int(ayah_str.strip()), float(time_str.strip())))
    pairs.sort(key=lambda p: p[1])
    return pairs


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


def write_ass_timed(segments: list[tuple[str, float, float]], duration: float, out_path: Path) -> None:
    """One ayah on screen at a time: each segment's text shows only for its
    own [start, end) window, so the caption goes in and out with the audio
    instead of dumping the whole passage on screen at once."""
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {BRAND_VIDEO_W}
PlayResY: {BRAND_VIDEO_H}
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Arabic,{BRAND_ARABIC_FONT},{BRAND_ARABIC_SIZE},&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,3,1,2,60,60,160,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []
    for text, start, end in segments:
        start = max(0.0, min(start, duration))
        end = max(start, min(end, duration))
        if end <= start:
            continue
        events.append(
            f"Dialogue: 0,{_ass_timestamp(start)},{_ass_timestamp(end)},Arabic,,0,0,0,,{_ass_escape(text)}"
        )
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
    parser.add_argument("--end-time", type=float, default=None, help="Cut the clip at this many seconds instead of running the full audio length (e.g. 32.5)")
    parser.add_argument("--fade-duration", type=float, default=1.5, help="Length in seconds of the audio+video fade-out at the end (default 1.5s)")
    parser.add_argument("--ayah-times", default=None, help="Sync each ayah to when it's actually recited: 'ayah:seconds,ayah:seconds,...' e.g. '35:0,36:8.5,37:17,38:25' — each ayah's text shows only until the next one's start time. Requires --surah. Overrides the static whole-passage caption.")
    parser.add_argument("--fonts-dir", default=None, help="Folder containing font files (e.g. the extracted Amiri .ttf files). Points ffmpeg straight at them, bypassing the OS font install/cache — the reliable fix when an installed font (esp. on Windows) isn't being picked up.")
    parser.add_argument("--credit-fontfile", default=None, help="Override the font file used for the reciter-credit text (default: the BRAND_CREDIT_FONTFILE constant, a Linux path — set this on Windows/Mac).")
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
    timed_segments = None  # list of (text, start, end), set below if --ayah-times is used

    if args.ayah_times:
        if not args.surah:
            sys.exit("--ayah-times requires --surah (to know which surah's text to fetch)")
        ayah_time_pairs = parse_ayah_times(args.ayah_times)
        try:
            ayah_texts = fetch_surah_ayahs(args.surah, args.arabic_edition)
        except Exception as e:
            sys.exit(f"Could not fetch Arabic text for --ayah-times ({e}). Can't build synced captions without it.")
        timed_segments = []
        for i, (ayah_num, start) in enumerate(ayah_time_pairs):
            if ayah_num not in ayah_texts:
                sys.exit(f"Ayah {ayah_num} not found in surah {args.surah}")
            end = ayah_time_pairs[i + 1][1] if i + 1 < len(ayah_time_pairs) else None  # filled in once duration is known
            timed_segments.append((ayah_texts[ayah_num], start, end))
        print(f"Fetched {len(timed_segments)} synced ayah captions for surah {args.surah}", file=sys.stderr)
        if args.ayah_start is None:
            args.ayah_start = min(n for n, _ in ayah_time_pairs)
        if args.ayah_end is None:
            args.ayah_end = max(n for n, _ in ayah_time_pairs)

    elif arabic_text is None and args.surah is not None and args.ayah_start is not None:
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

    full_duration = ffprobe_duration(audio)
    duration = min(args.end_time, full_duration) if args.end_time else full_duration
    base = args.out_name or audio.stem
    mp4_path = out_dir / f"{base}.mp4"
    txt_path = out_dir / f"{base}.txt"

    vf_parts = [
        f"scale={BRAND_VIDEO_W}:{BRAND_VIDEO_H}:force_original_aspect_ratio=increase",
        f"crop={BRAND_VIDEO_W}:{BRAND_VIDEO_H}",
    ]

    fontsdir_clause = f":fontsdir='{escape_for_filter(args.fonts_dir)}'" if args.fonts_dir else ""

    if timed_segments:
        # Fill in the last segment's open-ended "end" now that we know duration.
        timed_segments = [
            (text, start, end if end is not None else duration)
            for text, start, end in timed_segments
        ]
        ass_path = out_dir / f"{base}.ass"
        write_ass_timed(timed_segments, duration, ass_path)
        vf_parts.append(f"subtitles='{escape_for_filter(str(ass_path))}'{fontsdir_clause}")
    elif arabic_text:
        ass_path = out_dir / f"{base}.ass"
        write_ass(arabic_text, translation, duration, ass_path)
        vf_parts.append(f"subtitles='{escape_for_filter(str(ass_path))}'{fontsdir_clause}")

    # Credit sits in the top corner, clear of the bottom-anchored captions
    # regardless of how many lines the ayah/translation text wraps to.
    credit_text = escape_for_filter(f"{args.reciter}")
    credit_fontfile = args.credit_fontfile or BRAND_CREDIT_FONTFILE
    vf_parts.append(
        f"drawtext=fontfile={credit_fontfile}:"
        f"text='{credit_text}':fontcolor=white:fontsize={BRAND_CREDIT_SIZE}:box=1:boxcolor=black@0.4:boxborderw=8:"
        "x=w-text_w-30:y=50"
    )

    fade_duration = min(args.fade_duration, duration)
    fade_start = max(0.0, duration - fade_duration)
    vf_parts.append(f"fade=t=out:st={fade_start:.3f}:d={fade_duration:.3f}")
    af = f"afade=t=out:st={fade_start:.3f}:d={fade_duration:.3f}"

    cmd = [
        "ffmpeg", "-y",
        "-stream_loop", "-1", "-i", str(background),
        "-i", str(audio),
        "-map", "0:v", "-map", "1:a",
        "-t", f"{duration:.3f}",
        "-vf", ",".join(vf_parts),
        "-af", af,
        "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-c:a", "aac", "-b:a", "128k",
        str(mp4_path),
    ]
    print(f"Rendering {mp4_path} ({duration:.1f}s, fade-out last {fade_duration:.1f}s)...", file=sys.stderr)
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
