# Changelog — Voice Master

Design decisions, user prompts, and engineering rationale are recorded here
alongside version history for future reference and case study use.

---

## [Unreleased] — v1.1.0

_In progress — Recording type presets_

---

## [1.0.1] — 2026-05-06

### Fixed
- M4A / MP3 loading: switched from `soundfile` (libsndfile, no AAC) to
  `pedalboard.io.AudioFile` with an `ffmpeg` subprocess fallback for any
  codec the pedalboard reader doesn't support on the current platform
- Page scroll: `height: 100%` on `html, body` capped the page at viewport
  height preventing overflow; removed in favour of `min-height: 100vh`
- Content clipping: `overflow: hidden` on `.card` was clipping the spectrogram
  image; removed
- Layout: user requested flat, unboxed page — removed card wrapper entirely,
  replaced with a centred `.col` column at max-width 680px

### User prompts
> Error opening '.../input.m4a': Format not recognised. fix pls

> Are you sure? Still does not work for me. Redo the layout, do not box it,
> just give me scrollable page

---

## [1.0.0] — 2026-05-06

### Added
- Python CLI (`master_voice.py`): full mastering pipeline for spoken voice
- Effects chain: noise reduction → high-pass filter → parametric EQ →
  compression → limiter → integrated loudness normalisation
- Before / after spectrogram output saved as PNG (matplotlib, inferno colourmap)
- All 20+ parameters overridable via CLI flags; sensible voice defaults baked in
- Flask web app (`app.py`) on port 5001; auto-opens browser on launch
- Drag-and-drop file upload accepting WAV, FLAC, MP3, AIFF, M4A, OGG
- Server-Sent Events stream for real-time step-by-step status in the browser
- Flat dark-themed HTML / CSS / JS UI — zero external dependencies

### User prompt
> Build a Python CLI that masters a voice recording. Use pedalboard for the
> effects chain (high-pass, parametric EQ, compressor, limiter), noisereduce
> for noise reduction with a configurable noise sample range, and pyloudnorm
> to hit −16 LUFS. Output the processed file plus before/after spectrograms.
> Sensible defaults for spoken voice, all parameters overridable via flags.

> Can you give me that in an app form? simple interface to drop file, press
> button to proceed, status of actions and output with waveform (spectrogram)

### Design thinking

**Stack choices**
- `pedalboard` over raw scipy filters — battle-tested DSP at native speed,
  consistent API across filter types, works on (channels × samples) arrays
- `pyloudnorm` for LUFS — implements ITU-R BS.1770-4 correctly including the
  K-weighting filter and gating; simpler alternatives get this wrong
- `noisereduce` — spectral gating approach; works well on stationary and
  semi-stationary noise (HVAC, hiss, fan) which covers most voice contexts
- Flask + SSE over WebSockets — SSE is one-directional (server → client),
  which is all we need; no JS library required; generators are cheap
- No external JS or CSS frameworks — keeps the app self-contained,
  fast-loading, and easy to embed or adapt

**Default values (voice mastering)**
- High-pass 80 Hz: removes handling noise and low-frequency rumble without
  touching voice fundamentals (male voice sits ~85–180 Hz, female ~165–255 Hz)
- Low shelf −3 dB @ 200 Hz: addresses the typical room build-up in the
  low-mid region without hollowing out the voice
- Mid cut −3 dB @ 400 Hz Q 1.0: reduces the "boxy" or "cardboard" quality
  common in untreated rooms
- Presence +2.5 dB @ 4 kHz Q 0.8: adds intelligibility and cuts through
  without the harshness of boosting at 5–6 kHz
- Air +1.5 dB @ 10 kHz: openness without sibilance
- Compressor −18 dB / 3:1 / 8 ms attack / 120 ms release: moderate dynamic
  control; 8 ms attack lets transients through for naturalness
- Limiter −1 dBFS: leaves 1 dB of headroom for inter-sample peaks
- Target −16 LUFS: EBU R128 podcast/streaming standard

---

## [1.1.0] — 2026-05-06

### Added
- Recording type preset selector (8 scenarios) shown before mastering
- Each preset configures the full effects chain: NR strength, HP cutoff,
  EQ shape, compression settings, and LUFS target
- "Room recording" pre-selected by default; all other presets accessible
  via an expand / collapse grid ("on demand" pattern)
- Processing step accordion: basic status visible by default, full technical
  parameters (frequencies, dB values, ratios) under a `<details>` element
- `presets.py` module with all preset definitions and audio parameters
- CHANGELOG.md (this file)

### User prompts (PRD session)
> I need to add "type of recording" select pre-mastering (suggest best UX
> pattern for it). For the test file you boosted background noise. My aim is
> for the user to decide, whether the file needs background noise removed or
> not, if it comes from poor headset, recorded from afar, multiple people or
> just one voice isolated, etc. Plan this as PRD and ask me questions before
> acting if something is unclear. Let's milestone it and keep track of versions.

Clarifications received in follow-up:
1. Full chain (NR + EQ + compression + limiter + LUFS) per preset, not NR only
2. Expand scenarios — add "Zoom recording" and "outdoor recording"
3. Default = Room recording (low NR, 1 speaker); other options on demand
4. Output as much data as possible, basics first, pro data under accordion
   (progressive enhancement philosophy)
5. Semver versioning, keep changelog with prompts and thinking for case study

### Design thinking

**UX pattern selection**
Four patterns were considered:

| Pattern | Rejected because |
|---|---|
| Dropdown select | Non-visual; user must read each option carefully; no room for description |
| "How noisy?" slider | Too reductive — the problem is recording context, not just noise level |
| Step-by-step questionnaire | Too much friction for a one-shot tool; over-engineers the decision |
| **Scenario cards (chosen)** | Scannable, visual, one-tap selection, maps 1:1 to preset configs |

Cards also make it obvious that the choice is mutually exclusive and exhaustive,
and they scale gracefully when new scenarios are added.

**"On demand" pattern**
The user explicitly asked for the default to be pre-selected and alternatives
accessible on demand. The implementation: selected preset always shows as a
compact summary row (icon + label + NR intensity + "Change ▾"). Clicking
expands a 2-column card grid. Selecting any card collapses the grid and
updates the summary. This avoids overwhelming a first-time user while keeping
all options one tap away.

**Progressive disclosure for step data**
Each step shows label + status icon by default. Technical parameters live in
a native HTML `<details>` / `<summary>` accordion with no JS required.
Rationale: the accordion is the right pattern here because the data is
supplementary, not primary — it answers "what exactly was done?" for
engineers and curious users without cluttering the default view.
A separate "advanced settings" panel was considered but rejected: users
don't need to configure parameters, they need to understand what was applied.

**Preset audio engineering rationale**

*Studio mic — skip NR entirely*
Running noisereduce on a clean recording introduces spectral artefacts
(musical noise) with no benefit. The prop_decrease parameter cannot eliminate
this when there is no noise profile to subtract.

*Headset / Earbuds — moderate NR (0.65), cut 500 Hz*
Consumer headsets (Apple EarPods, Jabra) tend to exhibit a nasal honk around
400–600 Hz caused by the resonance of the boom mic housing. A −5 dB cut at
500 Hz Q 1.0 addresses this without touching fundamentals.

*Room recording — default (NR 0.40)*
Low noise reduction preserves room character. 0.40 prop_decrease is enough
to reduce HVAC hiss and gentle fan noise without artefacts. This preset uses
the current defaults, which were validated on test files.

*Interview (1-on-1) — lighter compression (2.5:1, −22 dB threshold)*
Two voices in close proximity often have level differences of 6–10 dB.
Aggressive compression (3:1, −18 dB) would push the louder speaker into
obvious pumping while barely touching the quieter one. Backing off to 2.5:1
at −22 dB provides gentle dynamic control across both voices.

*Multiple speakers — gentlest compression (2:1, −22 dB)*
Same rationale as interview but more extreme. Roundtable / panel recordings
often have 3–6 speakers with widely varying levels; heavy compression destroys
the natural hierarchy of who is speaking and how emphatically.

*Zoom / Remote call — very low NR (0.25), strong presence + air boost*
Zoom applies its own noise suppression and compression before recording.
Additional NR creates double-processing artefacts. The codec (Opus at 32 kbps
for audio-only) rolls off above ~16 kHz and compresses 3–8 kHz. Boosting
+4 dB at 3.5 kHz and +3.5 dB shelf at 8 kHz partially compensates for
this frequency damage.

*Phone / Mobile — high HP (120 Hz), aggressive NR (0.80)*
GSM and LTE voice telephony has a pass-band of roughly 200–3400 Hz (narrowband)
or 50–7000 Hz (wideband HD Voice). Recording a phone call typically captures
below 200 Hz as handling/device noise rather than voice content, so the HP
cutoff is raised to 120 Hz. The presence boost targets 3 kHz where phone
systems preserve most intelligibility.

*Outdoor — HP at 150 Hz, highest NR (0.88)*
Wind noise is predominantly low-frequency (below 200 Hz) and wideband
broadband noise. A 150 Hz HP cutoff removes the worst of the wind rumble.
NR at 0.88 is the highest setting used; going to 1.0 tends to create
obvious spectral holes in the signal.
