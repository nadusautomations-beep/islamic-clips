# Islamic Clipping — Process & Income Strategy

A practical playbook for running an "Islamic clips" page (short, shareable clips of
Qur'an recitation, du'a, and lecture highlights) across TikTok, YouTube Shorts, and
Instagram Reels, plus the automation pipeline in this repo that speeds up the editing
grind.

## Reality check on "fast"

Be honest with yourself about the timeline before investing real hours:

- **Day 1–14**: $0. You're posting daily and finding your niche/style. No platform
  pays out on raw views before a threshold is hit.
- **TikTok Creator Rewards Program**: needs 10k followers + 100k authentic views in
  the last 30 days before you earn anything.
- **YouTube Shorts (Partner Program)**: needs 1,000 subscribers + 10M public Shorts
  views in 90 days (or the standard 4,000 watch-hours route).
- **Instagram**: no built-in Shorts-style ad payout in most regions; income comes
  from bonuses (where available), brand deals, or driving traffic to something else
  (a product, a bigger channel, affiliate links).
- **Realistic first income**: most accounts that post daily, consistently, with a
  clear niche, start seeing meaningful money in **6–12 weeks**, not days. The fastest
  real path to *income* (not just views) in week 1–2 is usually **not** platform ad
  revenue — it's affiliate links, a digital product (du'a e-book, course), or
  freelance editing for other dawah pages, while the clips account itself compounds
  in the background.

Plan around that, and you won't get discouraged and quit at week 3 right before it
would have turned a corner.

## 1. Rights — don't skip this

This is the single biggest risk to the business, not a footnote:

- **Only clip content you have the right to monetize.** A lecture being public on
  YouTube does not mean you can re-upload and monetize it elsewhere. Platforms
  (especially YouTube Content ID and Instagram's rights-manager) will strike,
  demonetize, or remove monetization eligibility from accounts built on reposted
  copyrighted lectures.
- **Fastest clean paths:**
  1. Record your own content (a local imam, a sheikh who agrees to be filmed, your
     own recitation/reflections).
  2. Get explicit written permission from the scholar/organization to clip and
     monetize their existing lecture catalog — many scholars/orgs are open to this
     if you credit them and/or share revenue; ask before you build a whole page
     around their content.
  3. Use recitations/lectures explicitly released under a permissive license
     (public domain Qur'an recitations, Creative Commons–licensed lecture archives).
- Keep a simple spreadsheet: source, rights status, who gave permission and when.
  If a platform ever asks, you want a one-line answer, not a scramble.

## 2. Pick a narrow niche, not "Islamic content" broadly

Broad = no algorithmic identity. Narrow examples that perform well:
- Du'a for a specific situation (anxiety, gratitude, hardship) — 20–40 sec clips.
- One powerful tafsir insight per clip, same visual template every time.
- "Reminder of the day" — a single ayah + a 10-second reflection.
- Recitation moments (specific reciter, specific surah style) for a recitation-focused page.

Pick one. Nail the format. Expand later once the first format works.

## 3. Production pipeline (where automation helps)

```
source video (rights-cleared)
   -> transcribe                (scripts/transcribe.py, Whisper)
   -> find highlight candidates (scripts/find_highlights.py, Claude)
   -> cut + vertical crop + burn-in captions (scripts/make_clips.py, ffmpeg)
   -> review the 3-6 candidate clips, pick the best, write your own hook/caption
   -> post manually (first few weeks) or via a scheduler once you're consistent
```

This repo's `scripts/` folder automates steps 1–4 so your actual time goes into
picking the best moment and writing a hook, not manual scrubbing/cutting in an
editor. See `README.md` for usage.

## 4. Posting cadence & hook discipline

- 1–3 posts/day, same time window daily, for at least 6 weeks before judging results.
- First 1.5 seconds carries the clip — lead with the ayah/line itself or a text hook,
  not a logo or slow intro.
- Burned-in captions always on (most viewers watch muted).
- Consistent visual template (same font, same lower-third credit to the original
  speaker) — this is also your rights-attribution record.

## 5. What actually seems to perform, based on real research (not guessing)

Checked this rather than assuming. Honest caveat up front: there's no rigorous,
sourced ranking of "top" accounts or a breakdown of exact hook timing/caption
length for this niche — most of what's findable is TikTok's own discovery pages
and a handful of commentary pieces, not analytics. Treat the below as directional,
not proven:

- **Translations seem to matter for reach.** Multiple sources note that pairing
  Arabic with an English translation lets non-Arabic-speaking viewers engage —
  that's a real tension with the "too much text" problem we hit: the fix isn't
  "drop translation," it's "show less at once" (shorter ayah ranges, smaller
  font, or synced per-ayah captions so only one verse's worth of text is ever on
  screen at a time).
- **Thematic series beat one-off posts.** Grouping by theme (du'a for anxiety,
  "ayah that touched you," Friday-specific surahs) gives viewers a reason to
  follow, not just watch once.
- **Reciter + emotional delivery matters as much as visuals.** The examples that
  broke out widest were specifically about a striking reciter (e.g. a child's
  recitation), not the background footage.
- **Reposting other creators' recitations appears to suppress reach** on top of
  the rights risk already covered in section 1 — another reason to prefer your
  own or properly licensed audio over scraping someone else's upload.
- **Hashtag patterns** seen repeatedly: #quranrecitation, #ayatoftheday, #fyp,
  plus a theme-specific tag. Low-effort, worth including, don't expect them to
  carry a weak clip.

## 6. Monetization paths, roughly in order of speed

1. **Affiliate / your own product** (du'a journal, short course, Arabic-learning
   resource) — can start making sales in week 1–2 once you have *any* audience,
   doesn't require hitting a platform payout threshold.
2. **Editing-for-hire** using the same pipeline for other dawah accounts — fastest
   actual cash, and you're already building the tooling.
3. **Platform ad revenue** (TikTok Creator Rewards, YouTube Shorts) — slowest to
   start, but compounds and becomes passive once thresholds are hit.
4. **Brand/organization sponsorships** — once you have a real engaged audience
   (think thousands of followers with real engagement, not just views).

## 7. Weekly checklist

- [ ] 7–21 clips produced and queued
- [ ] Rights log updated for any new source
- [ ] One metric reviewed (which clip format got saves/shares, not just views —
      saves/shares are what the algorithm rewards for reach)
- [ ] One outreach message sent (to a scholar/org for permission, or a potential
      editing-for-hire client)
