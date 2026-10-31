# Feasibility (v2): doing the mastering on the owner's Mac

GarageBand has **no real scripting API**. Its AppleScript dictionary exposes almost nothing useful (no tracks, plug-ins or parameters). So v2 drives the GarageBand UI like a person would, through Grok Bot's machine-targeted Shell on the owner's Mac (ListMachines → machineId; **the owner approves each command**).

| Step | How | Reliability | Verification / fallback |
|---|---|---|---|
| Find projects, copy `.band` | `mdfind`/`find`, `ditto` to `~/MusicMastering/copies/<song> - master <ts>.band`, refuse if it exists, compare file counts | **High** (plain files) | `COPY_OK`; the original is never opened |
| Inspect `.band` | read-only `find` / `plutil -p` on metadata plists, list Media | High (read-only) | `projectData` is private binary: **never edited** |
| Open copy, confirm it's the copy | `open -a GarageBand`, read the front window title | High | `FRONT_OK` gate before every edit/save |
| Menus (Show Master Track, Export) | System Events menu clicks, prefix match (`…` vs `...`), ⌘⇧M | Medium-high (names vary by version and language) | `menus` discovery first, `CLICKED:` marker, screenshot |
| Insert plug-ins into slots | AX clicks on slot buttons and pop-up menus from `ax-dump` | **Low-medium** (unlabeled buttons, layout changes between versions) | screenshot after each; retry once, then the owner clicks (guided) |
| Set plug-in parameters | AX sliders in the plug-in's generic **Controls** view, `ax-act set`, read back value | **Low/unverified** (custom plug-in UIs often expose no AX sliders; Channel EQ graphic view is not scriptable) | read-back value + screenshot; else guided values |
| Export Song to Disk | Share menu, sheet text field + Export button, wait for a stable file | Medium (sheet layout varies; format pop-up) | first run: screenshot the sheet; `EXPORT_FILE=` or timeout |
| Measure | CopyToBox then `analyze.py` (pyloudnorm, 4× true peak) on the bot's computer; optional `ffmpeg ebur128` on the Mac | **High** | `genre_presets.py check` pass/fail |
| Youlean Loudness Meter 2 (free AU) | inserted last on the Master Track, played through, screenshot read | Medium (UI may not show in GarageBand until a preference is changed; needs playback) | cross-check only; the box measurement decides |
| Screenshots | `screencapture -x` | High once Screen Recording is granted | wallpaper-only image = permission missing |
| Offline fallback | `offline_master` (pedalboard gain + limiter + true-peak trim, 24-bit) then reimport into the copy | High | re-analyze; owner drags in for A/B |
| Release help | browser, owner's distributor account | Medium | approval at every submit; tax/banking/payments only with explicit yes |

**Permissions needed on the Mac:** Accessibility (UI scripting), Automation (prompt: control System Events/GarageBand), Screen Recording (screenshots), all for the app that runs Grok Bot's commands. Python on the Mac is **not** required (a bare Mac can pop up an Xcode tools prompt), so commands are pure shell + osascript.

**Untested so far (needs a real Mac):** every osascript/System Events step, AX element names and slider exposure, the export sheet, screencapture, Youlean inside GarageBand, `ditto` copy and `.band` inspection on current GarageBand, and the release flow. The skill asks the bot to record what worked per GarageBand version in memory and Hive Mind lessons so this hardens over time.

## Sources (fetched via search this session)
- https://github.com/extao15/garageband-llm-bridge — only `renderPreview` in dictionary; needs Automation + Accessibility
- https://glama.ai/mcp/servers/extao15/garageband-llm-bridge/schema — AX-based tool list
- https://developer.apple.com/library/archive/documentation/LanguagesUtilities/Conceptual/MacAutomationScriptingGuide/AutomatetheUserInterface.html
- https://www.macscripter.net/t/automating-batch-export-of-large-projects-from-garageband-6-0-5/66792 — Export Song to Disk script
- https://www.macscripter.net/t/gui-scripting-with-garageband-x-cant-identify-button/69153
- https://support.apple.com/guide/garageband/add-and-edit-effect-plug-ins-gbndac55f7f8/10.4.7/mac/11.5
- https://support.apple.com/en-us/101846 — 64-bit AU only
- https://support.apple.com/guide/logicpro/mastering-assistant-overview-lgcp7f94da0b/mac
- https://support.apple.com/en-us/108294 — Mastering Assistant use
- https://spotify.github.io/pedalboard/reference/pedalboard.html ; https://github.com/spotify/pedalboard/ ; https://github.com/spotify/pedalboard/issues/477 ; https://github.com/spotify/pedalboard/issues/277
- https://mastering.com/loudness-streaming-lufs/ ; https://stitosmastering.com/en/blog/lufs-spotify-apple-music/ ; https://edcabrera.com/en/blog/lufs-spotify-youtube-mastering-guide
