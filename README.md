# islamic-clips

Two automation pipelines for short-form Islamic video content, plus the
business playbook in `STRATEGY.md`. **Read `STRATEGY.md` first** — especially
the rights section before you feed either pipeline audio/video you don't have
clear permission to post and monetize.

1. **Recitation over scenery** (`make_recitation_clip.py`) — a recitation
   audio clip + a looping nature/landscape background + the ayah text and
   translation burned in. This is the workflow for a "Qur'an recitation"
   page posting several times a day.
2. **Lecture highlight clipping** (`transcribe.py` → `find_highlights.py` →
   `make_clips.py`) — for turning a long lecture recording into several
   short highlight clips automatically. Use this instead if your content is
   spoken lectures/reminders rather than recitation.

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...   # only needed for find_highlights.py
```

Requires `ffmpeg` on PATH (already present in this environment).

## Workflow 1: recitation over scenery (5-a-day format)

```bash
# 1. Put a recitation audio file + a looping nature/landscape background video here.
#    You source these yourself — see STRATEGY.md for where it's actually safe
#    to get both (recitation rights are real; most "free" recitation audio is
#    licensed for non-commercial use only, not for a monetized page).
cp /path/to/recitation.mp3 source_videos/audio/
cp /path/to/sunset_clouds.mp4 source_videos/backgrounds/

# 2a. With internet access to api.alquran.cloud (works on your own machine;
#     blocked in some sandboxed dev environments), auto-fetch the ayah text:
python3 scripts/make_recitation_clip.py \
    --audio source_videos/audio/recitation.mp3 \
    --background source_videos/backgrounds/sunset_clouds.mp4 \
    --reciter "Yasser Al-Dosari" \
    --surah 1 --ayah-start 1 --ayah-end 7

# 2b. Or type the Arabic/translation yourself (works fully offline):
python3 scripts/make_recitation_clip.py \
    --audio source_videos/audio/recitation.mp3 \
    --background source_videos/backgrounds/sunset_clouds.mp4 \
    --reciter "Yasser Al-Dosari" \
    --reference "Al-Fatihah 1-7" \
    --arabic-text "بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ ..." \
    --translation "In the name of Allah, the Most Gracious, the Most Merciful ..."

#   -> clips/recitation.mp4  (1080x1920, looped/cropped background, ayah + translation
#      burned in at the bottom, reciter credited top-right)
#   -> clips/recitation.txt (caption/hashtags/rights-note sidecar)
```

Run it once per audio+background pair. For 5 uploads a day, pair 5 different
recitation clips with a small rotating set of background videos (3-5 good
backgrounds reused across many clips is normal and looks fine — the audio and
ayah text are what's different each time).

## Workflow 2: lecture highlight clipping

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
STRATEGY.md               Business playbook: rights, niche, cadence, monetization timeline
source_videos/
  audio/                   Recitation audio files you've sourced (Workflow 1)
  backgrounds/             Looping nature/landscape background videos (Workflow 1)
  (lecture videos)         Long lecture recordings (Workflow 2)
scripts/
  make_recitation_clip.py  Workflow 1: audio + background + ayah text -> vertical clip
  transcribe.py            Workflow 2: source video -> timestamped transcript (faster-whisper)
  find_highlights.py       Workflow 2: transcript -> candidate highlight timestamps + hooks (Claude)
  make_clips.py            Workflow 2: highlights -> vertical clips with burned-in captions (ffmpeg)
clips/                     Output: ready-to-review vertical clips + caption sidecars
```
