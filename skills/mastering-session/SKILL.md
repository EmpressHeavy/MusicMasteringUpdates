---
name: mastering-session
description: >-
  Run a GarageBand mastering session for the owner: analyze the mix, explain it,
  recommend Master Track settings, guide them click by click (or process a copy
  outside GarageBand and guide the reimport), verify, and record. Use whenever
  the owner sends a mix, asks to master a song, or asks why a master sounds off.
---
# Mastering session
Tools: `A=/workspace/mastering/.venv/bin/python`, analyzer `/workspace/mastering/tools/analyze.py`, records `python3 /workspace/mastering/gb_db.py`, offline helper `/workspace/mastering/tools/gb_control.py`. Read preferences first: `gbmem boot` and `gb_db.py history --limit 5`.
Tone: warm, plain words, never shame a mix. Numbers first, then what they mean ("-9 LUFS is louder than Spotify plays; it'll be turned down about 5 dB"). Small moves (±1–2 dB), each with a one-line why. Be honest that GarageBand has no real scripting, so the owner does the clicking.

## 1. Intake
- Ask for the mix as a file (WAV or AIFF, 24-bit if possible) with **all Master Track effects off**. How to export it: in GarageBand, **Share > Export Song to Disk…**, choose **WAV** (or AIFF), quality **24-bit**, click **Export**. On older versions the format may be "Uncompressed".
- Get it onto the box: they attach it in chat, or (Mac helper on, with approval) CopyToBox from their Mac. Save under /workspace/mastering/in/. Never modify that file.
- Platform target: their `default_target` pref unless they say otherwise. Spotify/YouTube -14 LUFS, Apple Music -16 LUFS, peaks -1 dBTP.
- Make a project copy first: tell them **File > Save As…**, add " - master" to the name. All moves happen in that copy.

## 2. Analyze
`$A analyze.py in/<file> --target <t> --out /workspace/mastering/pre.json`, then `gb_db.py add-session --project "<copy name>" --target <t>` and `gb_db.py add-track-analysis --session <id> --title "<title>" --json pre.json --stage pre`. (Song titles stay in their private records only.)

## 3. Explain (in this order)
1. Clipping or headroom: if `clipped_samples` > 0 or sample peak ≥ 0 dBFS, the fix is in the mix (pull the loudest track's volume down a few dB and re-export) before mastering.
2. Loudness vs target: integrated LUFS and how far from target. If it's already louder than target, say so: don't add limiter gain; lowering the Master Volume is optional since platforms turn it down anyway.
3. Tone: the band-energy numbers compared with a typical balance (muddy low-mids, harsh high-mids, missing air).
4. Dynamics: crest factor and LRA (very squashed, or very dynamic).
5. Width: stereo correlation (below ~0.2 risks mono problems; suggest checking on one speaker).

## 4. Recommend and guide, click by click (default)
Give one numbered step per message chunk and wait for "done" before the next block. Use the owner's GarageBand version from memory; if a menu name doesn't match, ask what they see and adapt (record a lesson).
1. **Show the Master Track:** **Track > Show Master Track** (shortcut **⌘⇧M**). A "Master" track appears at the bottom. Select it.
2. **Open its controls:** press **B** (Smart Controls), then click **Master** at the top of the Smart Controls area, and turn on **Plug-ins** (the Plug-ins section of the inspector). If a master preset is loaded, set it to **No Effects** first.
3. **Channel EQ** (first empty slot > EQ > Channel EQ): give exact band moves from the analysis, e.g. "Click the 300 Hz point and drag down to -1.5 dB, Q around 1.0: clears mud so the vocal sits forward." Low-cut below ~30 Hz if `sub` is loud. Keep each move within ±2 dB.
4. **Compressor** (next slot > Dynamics > Compressor): gentle glue: Ratio 1.5:1–2:1, Attack ~30 ms, Release Auto, Threshold so the gain-reduction meter shows 1–2 dB on loud parts. Skip it if crest factor is already low (squashed).
5. **Adaptive Limiter** (next slot > Dynamics > Adaptive Limiter): **Out Ceiling -1.0 dB**, **Gain** = the analyzer's suggested gain (never above what it suggests; if the suggestion is negative, leave Gain at 0 dB). Turn on true-peak detection if the version shows it.
6. **Check:** play the loudest section; the limiter should only be touching peaks. Compare by toggling the plug-in power buttons.
7. **Export the master:** **Share > Export Song to Disk…**, WAV, 24-bit, name it "<song> - master v1".
Mastering Assistant is Logic Pro only; mention it only if they say they have Logic.
Record each plug-in with `gb_db.py add-settings-applied --track <id> --plugin "Channel EQ" --params '<json>' --by owner --reason "<why>"`.

### Optional Mac helper (only if the owner allowed it at setup; ask before EACH run)
With their Mac connected (ListMachines), print the command from `gb_control.py` (`open_project`, `list_menus` first to discover menu names, `show_master_track`, `export_song_to_disk`) and run it with a machine-targeted Shell only after their yes for that run. These need macOS Accessibility and Automation permission for the app running osascript. Plug-in knobs are never scripted; keep guiding those. If a script fails, stop scripting for the session and guide instead.

## 5. Fallback: process outside GarageBand and reimport
Use when guided moves can't reach the target cleanly (for example the limiter keeps pumping or the owner prefers it) and the owner said yes to the offline fallback (ask again for this song).
1. Run on the box (never on their original file): `$A -c "import sys; sys.path.insert(0,'/workspace/mastering/tools'); import gb_control as g; print(g.offline_master('in/<file>', '/workspace/mastering/out/<song> - master v1.wav', <gain_db>, -1.0))"` with the analyzer's suggested gain. It prints the final true peak; it never overwrites the input and trims itself so the true peak stays at or below the ceiling. If pedalboard isn't installed, install it in the venv; if that fails, say so and stay with guided steps.
2. Re-analyze the output (step 6) before sending it.
3. Send the file to the owner (attach in chat, or CopyFromBox to their Mac with approval).
4. **Reimport for A/B:** in the " - master" project copy, drag the file from Finder into an empty area below the tracks (or **Track > New Track > Audio**, then drag it in), line it up at bar 1, and turn off the Master Track plug-ins. Solo/mute to compare it with the original track at matched volume. Export the version they prefer.
Record with `--by offline_render`.

## 6. Verify
Analyze the exported master: `$A analyze.py <master> --target <t> --out post.json`, `gb_db.py add-track-analysis --session <id> --track <id> --title "<title>" --json post.json --stage post`. Report pre → post (LUFS, true peak, clipping) against the target in one short table. If true peak > -1.0 dBTP or clipped samples > 0, lower the limiter Gain by 0.5–1 dB and re-export. Iterate with small moves only.

## 7. Record and learn
- Save stated preferences: `gb_db.py set-pref <key> <value>` (e.g. `brightness lighter-touch`), and notable facts with `gbmem`.
- If a menu path was wrong for their version or a step failed and something else worked, `gbhive lesson add "garageband-steps: <topic>" "<avoid>" "<do instead>"` (generic wording only: no song titles, file names, artist names, or audio).
