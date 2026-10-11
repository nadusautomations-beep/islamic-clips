#!/usr/bin/env python3
"""Ask Claude to pick the best short, self-contained highlight moments from a transcript.

Usage:
    export ANTHROPIC_API_KEY=...
    python3 scripts/find_highlights.py source_videos/lecture1.transcript.json --count 6

Output: <name>.highlights.json — a list of candidate clips:
    [{"start": 12.4, "end": 41.0, "hook": "...", "caption": "...", "hashtags": [...]}]

Review this file before cutting — merge/trim timestamps by hand if Claude's
boundaries clip a sentence awkwardly. This script never auto-posts anything.
"""
import argparse
import json
import os
import sys
from pathlib import Path

SYSTEM_PROMPT = """You help produce short-form Islamic content clips (TikTok/Shorts/Reels, 15-60 seconds \
each) from longer lecture or recitation transcripts. Given a timestamped transcript, pick the \
best standalone moments: self-contained (makes sense with zero context), emotionally or \
intellectually striking in the first sentence, and naturally 15-60 seconds long. Respect the \
original speaker's words and meaning exactly; your job is to pick boundaries and write a \
companion hook/caption, not to alter the religious content.

Return ONLY a JSON array (no prose, no markdown fences). Each item:
{"start": <float seconds, from transcript>, "end": <float seconds, from transcript>,
 "hook": "<first on-screen text, <=8 words, what stops the scroll>",
 "caption": "<1-2 sentence social caption, no hashtags>",
 "hashtags": ["#..."]}
Pick timestamps that align to the start/end of actual transcript segments so the cut doesn't \
clip mid-sentence."""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("transcript_json", help="Path to *.transcript.json produced by transcribe.py")
    parser.add_argument("--count", type=int, default=6, help="How many highlight candidates to request")
    parser.add_argument("--model", default="claude-sonnet-5-5")
    args = parser.parse_args()

    transcript_path = Path(args.transcript_json)
    if not transcript_path.exists():
        sys.exit(f"Transcript not found: {transcript_path}")

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        sys.exit("Set ANTHROPIC_API_KEY in your environment first.")

    import anthropic

    data = json.loads(transcript_path.read_text(encoding="utf-8"))
    segments = data["segments"]
    transcript_text = "\n".join(f"[{s['start']:.1f}-{s['end']:.1f}] {s['text']}" for s in segments)

    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model=args.model,
        max_tokens=4000,
        system=SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "content": f"Pick the best {args.count} highlight candidates from this transcript:\n\n{transcript_text}",
        }],
    )

    raw = "".join(block.text for block in message.content if block.type == "text").strip()
    try:
        highlights = json.loads(raw)
    except json.JSONDecodeError:
        sys.exit(f"Model did not return clean JSON. Raw output:\n{raw}")

    out_path = Path(str(transcript_path).replace(".transcript.json", ".highlights.json"))
    out_path.write_text(json.dumps(highlights, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Wrote {len(highlights)} candidates to {out_path}", file=sys.stderr)
    for h in highlights:
        print(f"  [{h['start']:7.1f} - {h['end']:7.1f}] {h['hook']}", file=sys.stderr)
    print("\nReview/edit this file before running make_clips.py.", file=sys.stderr)


if __name__ == "__main__":
    main()
