# Changelog

## 1
- First release, built on the DOGE v11 foundations: first-run setup skill (`skills/mastering-getting-started`) with Step 0 profile picture, "used before?" handoff, required backup card (GitHub private repo `my-mastering-backup` via `gh` device sign-in, or a weekly file), monthly settings check with one multi-select card, creator feedback.
- Private memory in its own folder (`~/memory/gb/brain.db`, `gbmem` CLI) so it can share a computer with other bots; optional private GitHub backup via `gbmem export`.
- Hive Mind ON by default (`gbhive on --bot gb`), send-only and anonymous, with the plain notice; the "Why leave this on?" card only if you ask to turn it off.
- Records store `records/gb_db.py` with auto-backup and additive restore.
- Mandatory weekly update check from this repo (snapshot, rollback).
