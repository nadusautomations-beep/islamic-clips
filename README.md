# islamic-clips

Automation pipeline for turning a long lecture/recitation recording into a batch
of ready-to-post vertical clips with burned-in captions, plus the business
playbook in `STRATEGY.md`. **Read `STRATEGY.md` first** — especially the rights
section before you feed it any source video you didn't record yourself or get
explicit permission for.

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...   # only needed for find_highlights.py
```

Requires `ffmpeg` on PATH (already present in this environment).

## Pipeline

```bash
# 1. Put your rights-cleared source video here
cp /path/to/lecture.mp4 source_videos/

# 2. Transcribe with timestamps
python3 scripts/transcribe.py source_videos/lecture.mp4
#   -> source_videos/lecture.transcript.json, lecture.srt

# 3. Ask Claude to pick 6 standalone highlight moments
python3 scripts/find_highlights.py source_videos/lecture.transcript.json --count 6
#   -> source_videos/lecture.highlights.json
#   Open this file and check the timestamps/hooks before cutting —
#   nudge a boundary by hand if it clips mid-sentence.

# 4. Cut vertical clips with burned-in captions
python3 scripts/make_clips.py source_videos/lecture.mp4 \
    --highlights source_videos/lecture.highlights.json \
    --transcript source_videos/lecture.transcript.json \
    --source-credit "Sheikh X, [org], used with permission granted 2026-01-10"
#   -> clips/lecture_01.mp4 ... clips/lecture_06.mp4 (1080x1920, captions burned in)
#   -> clips/lecture_01.txt ... matching caption/hashtags/rights note for each
```

Watch every clip before posting. This pipeline picks boundaries and drafts a
caption; it does not touch the religious content itself, and it does not
auto-post anywhere — there's no reliable, ToS-safe way to auto-post video to
TikTok/Instagram/YouTube Shorts without going through each platform's own app
review, so the first several weeks should be manual uploads while you learn
what performs. Once cadence is established, a paid scheduler (Metricool,
Buffer, Later) can take over the posting step — none of those are wired up
here.

## Project layout

```
STRATEGY.md         Business playbook: rights, niche, cadence, monetization timeline
source_videos/       Your rights-cleared source recordings + generated transcripts
scripts/
  transcribe.py      Source video -> timestamped transcript (faster-whisper)
  find_highlights.py Transcript -> candidate highlight timestamps + hooks (Claude)
  make_clips.py       Highlights -> vertical clips with burned-in captions (ffmpeg)
clips/               Output: ready-to-review vertical clips + caption sidecars
```
