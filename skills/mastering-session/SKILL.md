---
name: mastering-session
description: >-
  Master a song for the owner in GarageBand on their own Mac: ask the genre, copy
  the .band project (never touching the original), open the copy, set up vocal,
  track and Master Track plug-ins from a genre preset, meter with the free Youlean
  Loudness Meter, export, measure, iterate, have the owner listen and give notes,
  then hand back the finished track (and optionally help distribute it). Falls back
  to guided clicks or offline processing when UI scripting fails. Use whenever the
  owner sends a song or project, asks to master a song, or asks why a master sounds off.
---
# Mastering session (v4: I do the work on your Mac, with "ears")

**Tools on this bot's computer:** `A=/workspace/mastering/.venv/bin/python`, `T=/workspace/mastering/tools`
- analyzer `$A $T/analyze.py`
- genre presets `$A $T/genre_presets.py`
- Mac command builder `python3 $T/gb_control.py <cmd> ...` (prints a shell command)
- records `python3 /workspace/mastering/gb_db.py`
Read preferences first: `gbmem boot`, `gb_db.py history --limit 5`, and the saved Mac (`gbmem` fact `owner mac_machine_id`).

**How Mac control works (be honest about it):** GarageBand has no real scripting API. I drive it like a person would: macOS UI scripting (System Events), keyboard shortcuts and menus, and screenshots to check my work. Every command runs through a machine-targeted Shell (`ListMachines` → `machineId`) and **the owner approves each one**. Build each command with `gb_control.py`, then run its printed output with `Shell(machineId=<mac>, command=<printed>)`. Never run anything on the Mac the owner didn't approve. UI scripting is fragile (menu names, dialog layouts and plug-in windows differ by GarageBand version and language), so:
- **Discover before acting:** run `menus` once per session and `ax-dump` before touching a window you haven't seen this session.
- **Verify every step:** after each action, check the returned marker (`CLICKED:`, `ACT_OK:`, `FRONT_OK:`, `EXPORT_FILE=`) and take a `screenshot <name>`, CopyToBox it and look at it with Read.
- **Retry once** (after `key escape` and a fresh `ax-dump`). If it fails a second time, switch that step to **guided mode**: tell the owner exactly what to click, wait for "done", screenshot to confirm. If guided can't get there either, use **offline mode** (section 9).
- Record what failed and what worked with `gbhive lesson add "garageband-ui: <topic>" "<avoid>" "<do instead>"`, using generic words only.

Tone: warm, plain words, never shame a mix. Numbers first, then what they mean. Small moves with a one-line why.

## 0. Preconditions
- Mac helper on and a Mac saved? If not, offer to set it up (getting-started steps M1–M4). If they say no, run the same session in **guided mode** (they click, I measure and verify) or **offline mode**.
- Run `preflight`. You need `Accessibility: OK`. If Youlean is `MISSING`, offer the free install (getting-started step M4). It's optional; the box analyzer is the source of truth either way.

## 1. Intake: genre, target, project
1. **Genre (always ask first).** Show tap buttons: Pop · Hip-hop/Rap · R&B · Rock · EDM · Country · Acoustic/Folk · Jazz · Lo-fi · Classical · Spoken/Podcast · Other (type it). Map the answer with `genre_presets.py list` (aliases like trap, metal, singer-songwriter and podcast work). Unknown genre: pick the closest one and say which you picked.
2. **Platform:** their `default_target` pref unless they say otherwise. Spotify/YouTube -14 LUFS, Apple Music -16 LUFS, true peak ≤ -1 dBTP. Quiet genres (acoustic, jazz, spoken -16; classical -18) keep their dynamics: target = the quieter of the two. Say so in one line.
3. **Project:** `find-projects` lists their .band files. Let them pick with tap buttons, by name only. Ask them to **save and close the song in GarageBand** first.
4. **Copy it:** `copy-project "<path>"`. It needs `COPY_OK` and gives a `COPY_PATH` inside `~/MusicMastering/copies/` named "<song> - master <timestamp>.band". **Never open, edit, save or export from the original.** If it says `EXISTS` or `COPY_MISMATCH`, stop and tell them.
5. Optional read-only look: `inspect-band "<copy>"` (track/media count, sample rate). Never edit files inside a .band package; `projectData` is a private binary format.
6. Records: `gb_db.py add-session --project "<copy name>" --target <t>` and set the genre with `gb_db.py set-pref last_genre <g>`.

## 2. Baseline measurement
1. `open "<copy>"` must return `FRONT_OK`. If it says `FRONT_NOT_COPY`, stop and close nothing; ask the owner to bring the copy to the front.
2. Make sure the Master Track has no effects (or record what's there). Then **export the raw mix**: `export "<song> - master v0"`, which waits for `EXPORT_FILE=`. The first time, screenshot the export sheet and check the format is **WAV** (or AIFF/Uncompressed), **24-bit**. If not, set it via `ax-dump` + `ax-act` on the pop-up, or ask the owner to pick it once.
3. CopyToBox the exported file into /workspace/mastering/in/, then `$A $T/analyze.py in/<file> --target <t> --out pre.json` and `gb_db.py add-track-analysis --session <id> --title "<title>" --json pre.json --stage pre`.
4. If `clipped_samples` > 0 or the sample peak ≥ 0 dBFS, the fix is in the mix: lower the loudest track's volume (guided or via `ax-act` on that track's volume slider) and re-export v0.

## 2b. Ears: headspace, reference match, beat study (v4)
I can't hear, so I measure and look. If `tools/headspace.py` is missing deps, run `.venv/bin/pip install -r tools/requirements.txt` (about 150 MB, CPU only).
- **Run headspace** on the baseline bounce, on every export in step 6, and whenever the owner says something about space ("vocal buried", "too wide", "muddy", "sounds weird on my phone"): `.venv/bin/python tools/headspace.py FILE --outdir out/NAME_headspace`. Read the summary lines and open `pan_map.png`, `midside.png` and `correlation.png` before suggesting width, pan or reverb changes. Flag a wide bass/sub, low-correlation bands, and out-of-phase stretches. Treat depth/reverb as a rough hint only.
- **References (study only).** The owner can give a reference as (a) a WAV/MP3/other audio file they have, or (b) a public link (YouTube etc.). It's for studying and dissecting only: analysis plus matching the tone, loudness and width of the owner's own mix. Never copy, upload, release or hand back the reference audio. For links, the tools fetch audio-only with yt-dlp into a temp folder (no playlists, 10 min max). The decoded reference audio is deleted right after analysis and only numbers and images are kept. The owner's own reference file is never modified or deleted. Tell the owner in one line: "I'll use this reference only to study it; I delete its audio after analysis and keep just the numbers and pictures."
- **Run reference match** when the owner wants their mix to sound "like" a reference: `.venv/bin/python tools/reference_match.py MIX REF_FILE_OR_LINK --out out/NAME_matched.wav`. Share the before/after lines, offer the matched WAV as an option (not the default), and say it copies tone, loudness and width, not taste. If the matched true peak is above -1 dBTP, limit it before handing it back.
- **Run beat study** when the owner wants to build a beat inspired by a reference: `.venv/bin/python tools/beat_study.py REF_FILE_OR_LINK --outdir out/NAME_beat`. It gives tempo, key, time signature, swing, a typical 16-step drum bar (kick/snare/hats), sound palette (808/sub, pads, plucks, brightness), section structure, and GarageBand build notes (kit, BPM, and Piano Roll steps: a drum kit track, a one-bar MIDI region, Cycle on, 1/16 grid. GarageBand for Mac has no Step Sequencer, so never tell the owner to use one). Open `drum_grid.png` and `structure.png` before you explain it. Results are solid on clean loops and rough on dense full mixes, so say so.
- **Inspiration, not copying.** Borrow the feel, groove, tempo, palette and arrangement shape. Never recreate the reference's melody, vocal hook, lyrics or samples note-for-note. Suggest changing some drum steps and sounds so the beat is the owner's own.
- All three tools only read inputs and write new files under `out/`. Never overwrite the owner's audio.

## 3. Plan from the genre preset
`$A $T/genre_presets.py plan <genre> pre.json --platform <t> --out plan.json`. It gives:
- `track_chains`: lead_vocal, backing_vocals, bass, drums, other, with GarageBand's own plug-ins (Channel EQ, Compressor, DeEsser 2, etc.) and starting values.
- `master_chain`: Channel EQ moves (at most a low cut plus 3 tone moves, ±2.5 dB max) → Compressor (skipped for classical) → Adaptive Limiter (Gain, Out Ceiling -1.0) → Youlean Loudness Meter 2, which only meters.
Explain the plan in 3–5 short lines (what each move does and why), then ask "Shall I set this up on your Mac?" with tap buttons: **Go ahead** · **Show me first** · **Guide me instead**.

## 4. Apply the plug-ins in the copy
For each track the owner points out as the lead vocal, backing vocals, bass or drums (ask once; save the mapping to memory for this song), then the Master Track:
1. **Select the track:** click its header (`ax-dump`, find the track name, `ax-act <i> "<name>" click`), or ask the owner to click it.
2. **Open plug-ins:** press `key b` (Smart Controls), then the Plug-ins area. For the master: `click-menu Track "Show Master Track"` (or `key m command,shift`) and select the Master track.
3. **Insert a plug-in:** click an empty plug-in slot, then the category menu, then the plug-in (for example Dynamics > Compressor). Use `ax-dump` to find the slot buttons; menus that pop up appear as `menu` elements. Screenshot after inserting.
4. **Set values:** a plug-in opens in its own window (`windows` lists it). Look for a **Controls** view (a generic slider view, if the version has one) and `ax-dump` its sliders. Then `ax-act <i> "<param>" set <value>` and confirm with the `ACT_OK` value. If the plug-in only offers its graphic view (common for Channel EQ), sliders may not be exposed: guide the owner for that plug-in ("drag the 300 Hz point down to -1.5 dB") and confirm with a screenshot.
5. Close each plug-in window (`key w command`) after its values are confirmed.
6. Record each plug-in: `gb_db.py add-settings-applied --track <id> --plugin "<name>" --params '<json>' --by ui_script|owner --reason "<why>"`.
7. When everything is in, `save-copy` (it refuses unless the front window is the copy).

Mastering Assistant is Logic Pro only. Mention it only if they say they have Logic.

## 5. Youlean Loudness Meter check (if installed)
- It goes last on the Master Track (Audio Units > Youlean > Youlean Loudness Meter 2). It only meters and never changes the sound.
- Before playing, ask the owner to start playback from the beginning (or send `key return` then `key space`) and let the song play through once. The free version shows **Integrated LUFS** and **True Peak** (enable True Peak if it's off).
- When it ends, screenshot the Youlean window and read Integrated and True Peak from it. This is a cross-check only: the exported file measured on the box decides pass or fail.
- Known issues: in GarageBand the interface may not show until a GarageBand preference is changed (Youlean's "Common issues" docs: https://docs.youlean.co/youlean-loudness-meter/introduction/installation-macos and the troubleshooting pages). It measures nothing while playback is stopped. If it misbehaves, skip it and rely on the box measurement.

## 6. Export, measure, iterate (max 3 rounds)
1. `export "<song> - master v1"` (then v2, v3; never reuse a name), wait for `EXPORT_FILE=`, CopyToBox, then `analyze.py ... --out post.json`.
2. `$A $T/genre_presets.py check post.json plan.json` gives pass/fail (±1 LU of target, true peak ≤ -1.0 dBTP, no clipping) plus `next_moves`.
3. Not passing: apply only the next moves (usually Adaptive Limiter Gain ±0.5–3 dB), export the next version, and measure again. After 3 rounds without a pass, explain why (for example the mix is too dynamic) and offer the offline fallback.
4. Quick Mac-side check when ffmpeg exists: `measure "<file>"`.
5. Record: `gb_db.py add-track-analysis ... --stage post`. Report pre → post in one short table (LUFS, true peak, clipping, target).

## 7. Listen and revise (the owner decides)
- Send the passing master: CopyFromBox to `~/MusicMastering/exports/`, attach it in chat, or `open -R` it on the Mac. Ask them to listen on headphones **and** phone or laptop speakers, and compare it with v0 at matched loudness. (The master is louder, so matched comparison avoids "louder sounds better".)
- Ask for revision notes, with tap-button starters: **Sounds great** · **Too harsh/bright** · **Too dull/dark** · **Vocal too quiet** · **Vocal too loud** · **Too squashed** · **Bass too much/little** · **Other (type it)**.
- Turn each note into one small move: harsh means DeEsser up or a -1 dB high-mid cut; vocal quiet means +1 dB on the vocal track; squashed means less limiter Gain or a lighter compressor. Re-export as the next version and re-check the target, then ask again. Save their taste to prefs (`gb_db.py set-pref brightness lighter-touch`).

## 8. Hand back
When they say it's done:
- Final WAV in `~/MusicMastering/exports/` (24-bit WAV, the master), plus the measurement card (LUFS, true peak, target, genre).
- The project copy keeps all settings for future edits. Their original project is untouched; say so.
- Offer: **Done for now** · **Help me release it** (start the music-distribution skill) · **Make an MP3 for sharing too** (`afconvert` on the Mac or ffmpeg; the master stays WAV).

## 9. Fallbacks
- **Guided mode** (UI scripting blocked or failing): same plan, but the owner clicks. One numbered step per message. Wait for "done", screenshot to confirm when the Mac is connected, and measure exports exactly the same way.
- **Offline mode** (the plug-ins can't reach the target cleanly, or there's no Mac access; ask first): `$A -c "import sys; sys.path.insert(0,'$T'); import gb_control as g; print(g.offline_master('in/<v0>', '/workspace/mastering/out/<song> - master offline v1.wav', <limiter_gain_db>, -1.0))"`. It never overwrites the input and trims to keep true peak ≤ ceiling. Re-analyze it, then put it on the Mac and `import-audio` it into the copy for an A/B (the owner drags it in at bar 1 and mutes the other tracks). Record with `--by offline_render`.

## 10. Record and learn
- Preferences go to `gb_db.py set-pref`; facts go to `gbmem`.
- UI lessons (menu names, AX element names that worked, which plug-ins expose sliders on their version) go to `gbmem fact garageband <topic> <value>` so next time is faster, and to Hive Mind with generic words only. Never song titles, file names, artist names, or audio.
