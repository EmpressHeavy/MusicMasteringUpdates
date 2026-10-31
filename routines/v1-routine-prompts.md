# v1 routine prompts and schedules
Schedules are cron in the owner's time zone ({{OWNER_TIME_ZONE}}). "Flexible ±15" means the run may drift up to 15 minutes. Placeholders: {{OWNER_NAME}}, {{OWNER_TIME_ZONE}}, {{OWNER_GITHUB}}. Records CLI: `python3 /workspace/mastering/gb_db.py`.
Order matches the routines created at the end of setup in skills/mastering-getting-started/SKILL.md.

## 1. Monthly settings check: `0 10 1 * *`, flexible ±15
Monthly settings check for {{OWNER_NAME}}, warm and brief. (1) Backup health: confirm /workspace/mastering/gb.db exists and the chosen backup is healthy (for GitHub: {{OWNER_GITHUB}}/my-mastering-backup is still private and its latest commit is recent); fix the push or tell them; weekly-file owners get an offer to switch to GitHub. (2) Tools: run the analyzer smoke test from the setup skill (make_test_signal + analyze.py must print integrated_lufs); reinstall the venv packages if it fails. (3) Recent work: `python3 /workspace/mastering/gb_db.py history --limit 5`, one line each (target hit or not). (4) Settings: show all their settings plus Hive Mind status from `gbhive status` with one line: it shares only anonymized lessons about what worked and what didn't, never personal info or songs, about once a week, so future versions improve. Then send ONE multi-select card listing every setting (Mac helper, offline fallback, sending messages for you, web research, Hive Mind, default loudness target) with its current state; change only what they pick (Hive Mind on: `gbhive on --bot gb` + recreate the weekly share routine; off: `gbhive off` + delete it). No "Why leave this on?" nudge here. (5) Updates: make sure the mandatory "Music Mastering weekly update check" routine exists and re-create it silently from routines/weekly-update-check.md if missing. If VERSION in https://raw.githubusercontent.com/EmpressHeavy/MusicMasteringUpdates/main/VERSION is newer than installed and the weekly check hasn't applied it, apply it now per UPGRADE.md section A. Add tap-button choices (Change settings, Master a song, All good). Change nothing without their yes.

## 2. Weekly file backup (only if the owner chose "Send me the file weekly"): weekly
Send the owner a fresh copy of /workspace/mastering/gb.db plus a zip of `gb_db.py export-all <tmp dir>` to keep. Silent otherwise.

## 3. Hive Mind weekly share (on by default; only while Hive Mind is on): weekly
Run `gbhive auto`. Stay silent unless it fails.

## 4. Music Mastering weekly update check (mandatory, always on): `0 10 * * 0`, flexible ±15
See routines/weekly-update-check.md. Created on every install and upgrade, re-created by the monthly check if missing; applies newer versions automatically and sends a short "Music Mastering updated to vN, here's what's new" note.
