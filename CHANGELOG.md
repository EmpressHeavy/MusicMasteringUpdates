# Changelog

## 2
- **Does the work on your Mac now.** The session asks the genre, copies your GarageBand project (the original is never touched), opens the copy, and sets up GarageBand's own plug-ins: vocal and track chains (Channel EQ, Compressor, DeEsser 2) plus the Master Track (Channel EQ → Compressor → Adaptive Limiter at -1 dBTP → Youlean meter). Then it exports, measures, and iterates until the master passes.
- New `analysis/genre_presets.py`: 11 genres plus aliases, platform/genre loudness targets (quieter for jazz, acoustic, spoken and classical), EQ/compressor/limiter plans, and a pass/fail `check`.
- New `garageband/gb_control.py`:
  - preflight (Accessibility, Youlean, ffmpeg)
  - find-projects, copy-project (ditto, never overwrites), inspect-band (read-only)
  - copy-gated open/save, menu discovery and clicks, keys
  - AX dump/act with stale-index guard, screenshots
  - export with wait, ffmpeg measure, offline_master
- Free Youlean Loudness Meter install guidance and metering step.
- Listen-and-revise loop with tap-button notes, then hand-back of the final 24-bit WAV.
- New optional `music-distribution` skill: release checklist and guided or in-account upload, with approval at every submit step and no tax, banking or payments without an explicit yes.
- Setup: pick the Mac via ListMachines, permission checks (Accessibility, Automation, Screen Recording), Youlean check, and default genre.
- Updated: profile title and description, persona, safety, FEASIBILITY (honest fragility table), PARITY, UPGRADE (v1→v2 notes; the new Mac and release settings are offered off by default to existing owners), monthly settings list.

## 1
- First release, built on the DOGE v11 foundations: first-run setup skill (`skills/mastering-getting-started`) with Step 0 profile picture, "used before?" handoff, required backup card (GitHub private repo `my-mastering-backup` via `gh` device sign-in, or a weekly file), monthly settings check with one multi-select card, creator feedback.
- Private memory in its own folder (`~/memory/gb/brain.db`, `gbmem` CLI) so it can share a computer with other bots; optional private GitHub backup via `gbmem export`.
- Hive Mind ON by default (`gbhive on --bot gb`), send-only and anonymous, with the plain notice; the "Why leave this on?" card only if you ask to turn it off.
- Records store `records/gb_db.py` with auto-backup and additive restore.
- Mandatory weekly update check from this repo (snapshot, rollback).
