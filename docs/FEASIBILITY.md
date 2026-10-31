# GarageBand control — feasibility (researched 2026-10-31)
Constraint: the Grok Bot box is Linux. Anything GarageBand-side runs on the owner's Mac via machine-targeted Shell (`osascript`), each with approval, and needs Accessibility + Automation permission.

| Rank | Option | Feasible? | Notes |
|---|---|---|---|
| 1 | **Analyze on box + guided manual steps** | Yes, robust | Analyzer gives exact Channel EQ / Compressor / Adaptive Limiter values; owner clicks. Zero fragility. |
| 2 | **Offline processing (pedalboard / ffmpeg) then reimport** | Yes | pedalboard has Gain/Compressor/Limiter/filters, loads VST3 (all OS) and Audio Units (macOS only, must be in ~/Library/Audio/Plug-Ins/Components; some AUs fail to scan — VST3 safer). Apple's built-in GB plugins aren't separately loadable this way. Its Limiter isn't true-peak: re-verify. |
| 3 | **Open project / launch (`open -a GarageBand`)** | Yes | Trivial shell. |
| 4 | **UI scripting via System Events (menus, keystrokes)** | Partly | Menu clicks like Share > Export Song to Disk work but break across versions/languages; dialogs need delays and sheet handling. |
| 5 | **UI scripting plugin parameters (knobs in plugin windows)** | Poor | Requires deep AX paths; plugin windows expose little. A community MCP bridge (garageband-llm-bridge) exposes tracks/Smart Controls/menus via AX, not full plugin parameters. |
| 6 | **AppleScript/JXA dictionary** | No | Only `renderPreview` is exposed. |
| 7 | **Logic Pro instead** | Better results, not better scripting | Has Mastering Assistant (auto EQ/loudness/width, Character presets) on Stereo Out; GarageBand does not. Opens GB projects. Scripting still UI-based. |
| 8 | **MIDI control surface / Logic-style control** | Not researched in depth; unverified | GarageBand's control-surface support is limited; treat as experimental. |
| 9 | **AUv3 hosting** | Not a control path | GB hosts 64-bit AUs (32-bit unsupported); a custom AU could do mastering inside GB but is a large build. |

**Targets:** Spotify/YouTube ≈ -14 LUFS integrated, Apple Music ≈ -16 LUFS, true peak ≤ -1 dBTP (references for playback normalization, not hard rules).

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
