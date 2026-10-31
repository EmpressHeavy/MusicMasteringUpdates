#!/usr/bin/env python3
"""Music Mastering for GarageBand v2: Mac control layer.

GarageBand has no real scripting API (its AppleScript dictionary exposes almost nothing), so this drives it the way a
person would: macOS UI scripting (osascript + System Events), keyboard shortcuts, screenshots (screencapture) to verify,
plus safe read-only inspection of the .band package and file-level copying.

WHERE IT RUNS: on the OWNER'S Mac, through Grok Bot's machine-targeted Shell (ListMachines -> machineId). Every command
needs the owner's local-tool approval. The bot builds each command on its own (Linux) computer with
    python3 gb_control.py <command> [args]          # on Linux this only PRINTS the shell command to send to the Mac
and runs the printed command with Shell(machineId=...). On a Mac, add --run to execute directly (only if python3 there
works; a bare Mac may pop up an Xcode tools installer for python3, so the printed pure-shell form is the default).

SAFETY: never writes inside the owner's original project. copy-project makes a timestamped copy and refuses to overwrite.
Saving (Cmd-S) is only ever sent after verify-front-project confirms the front window is the COPY.
Fragile parts (menu names, dialog layout, plug-in windows) change across GarageBand versions and languages: always run
`menus` / `ax-dump` discovery first, verify every step with a screenshot or `ax-dump`, retry once, then fall back to
asking the owner to click, then to offline processing (offline_master)."""
import argparse, os, shlex, subprocess, sys, time, json

Q = shlex.quote
GB = "GarageBand"
WORK = "$HOME/MusicMastering"          # all bot files on the Mac live here (copies, exports, screenshots)

def osa(script):
    """Shell command running an AppleScript via osascript (multi-line safe)."""
    return "osascript " + " ".join("-e " + Q(l) for l in script.strip().splitlines() if l.strip())

def se(body):
    """Wrap body in a System Events block targeting GarageBand's process."""
    return osa(f'''tell application "{GB}" to activate
delay 0.5
tell application "System Events" to tell process "{GB}"
set frontmost to true
{body}
end tell''')

# ---------- checks ----------
def preflight():
    """One read-only command: macOS + GarageBand version, Accessibility permission, Youlean, ffmpeg, python3, disk space."""
    return " ; ".join([
        'echo "macOS: $(sw_vers -productVersion)"',
        f'echo "GarageBand: $(defaults read /Applications/{GB}.app/Contents/Info CFBundleShortVersionString 2>/dev/null || echo NOT_INSTALLED)"',
        f'(osascript -e \'tell application "System Events" to get name of first process\' >/dev/null 2>&1 && echo "Accessibility: OK") || echo "Accessibility: MISSING (System Settings > Privacy & Security > Accessibility: turn on the app that runs Grok Bot commands)"',
        'Y=$(ls /Library/Audio/Plug-Ins/Components ~/Library/Audio/Plug-Ins/Components 2>/dev/null | grep -i youlean | head -1); echo "Youlean AU: ${Y:-MISSING}"',
        '(auval -a 2>/dev/null | grep -i youlean | head -1 | sed "s/^/Youlean auval: /") || true',
        'echo "ffmpeg: $(command -v ffmpeg || echo none)"',
        'echo "python3+numpy: $( (xcode-select -p >/dev/null 2>&1 && python3 -c "import numpy" 2>/dev/null && echo yes) || echo no)"',
        'echo "free disk: $(df -h "$HOME" | awk \'NR==2{print $4}\')"',
        f'mkdir -p {WORK}/copies {WORK}/exports {WORK}/shots {WORK}/tools && echo "workdir: {WORK}"',
    ])

def find_projects():
    """List the owner's GarageBand projects (read-only), newest first."""
    return ('mdfind "kMDItemContentTypeTree == com.apple.garageband.project" 2>/dev/null | head -50; '
            'find "$HOME/Music/GarageBand" "$HOME/Desktop" "$HOME/Documents" -maxdepth 3 -name "*.band" 2>/dev/null | head -50')

# ---------- project copy and inspection ----------
def copy_project(src, label="master"):
    """Copy the .band bundle (ditto keeps metadata and resource forks). Never overwrites; verifies file counts match."""
    s = Q(src)
    return (f'set -e; SRC={s}; [ -d "$SRC" ] || {{ echo "NOT_FOUND: $SRC"; exit 2; }}; '
            f'pgrep -x {GB} >/dev/null && echo "NOTE: GarageBand is running; ask the owner to save and close the original first" ; '
            f'B=$(basename "$SRC" .band); D="{WORK}/copies/$B - {label} $(date +%Y%m%d-%H%M%S).band"; '
            '[ -e "$D" ] && { echo "EXISTS: $D"; exit 3; }; '
            'ditto "$SRC" "$D"; '
            'A=$(find "$SRC" -type f | wc -l | tr -d " "); C=$(find "$D" -type f | wc -l | tr -d " "); '
            '[ "$A" = "$C" ] && echo "COPY_OK files=$C" || { echo "COPY_MISMATCH src=$A copy=$C"; exit 4; }; '
            'echo "COPY_PATH=$D"')

def inspect_band(path):
    """Read-only look inside a .band package. projectData is a private binary format: NEVER edit it.
    Safe to read: Info/metadata plists (tempo, key, sample rate, track count hints), Media/ (recorded audio files),
    Output/ (GarageBand's own preview mixdown, if any). Editing anything in the package is unsupported."""
    p = Q(path)
    return (f'P={p}; echo "== tree"; find "$P" -maxdepth 3 | sed "s|$P|.|" | head -80; '
            'echo "== plists"; for f in $(find "$P" -maxdepth 3 -name "*.plist" | head -10); do echo "-- $f"; plutil -p "$f" 2>/dev/null | head -60; done; '
            'echo "== media"; find "$P" -path "*Media*" -type f \\( -iname "*.aif*" -o -iname "*.wav" -o -iname "*.caf" -o -iname "*.m4a" \\) | head -40; '
            'echo "== size"; du -sh "$P"')

# ---------- app control ----------
def open_project(path):
    return f'open -a {GB} {Q(path)} && sleep 8 && ' + verify_front_project()

def verify_front_project(expect_substr="master"):
    """Prints the front window title; the bot must see the COPY's name (contains the label) before any edit or save."""
    return osa(f'''tell application "System Events" to tell process "{GB}"
set t to name of front window
if t contains "{expect_substr}" then
return "FRONT_OK: " & t
else
return "FRONT_NOT_COPY: " & t
end if
end tell''')

def save_copy():
    """Cmd-S, only after verify_front_project said FRONT_OK (the command re-checks and refuses otherwise)."""
    return osa(f'''tell application "System Events" to tell process "{GB}"
set t to name of front window
if t does not contain "master" then return "REFUSED_NOT_COPY: " & t
set frontmost to true
keystroke "s" using command down
return "SAVED: " & t
end tell''')

def menus():
    """Discovery: top menu names and every item of each menu (names differ by version/language; '…' vs '...')."""
    return se('''set out to ""
repeat with m in menu bar items of menu bar 1
set out to out & (name of m) & ": "
try
set out to out & ((name of menu items of menu 1 of m) as text)
end try
set out to out & linefeed
end repeat
return out''')

def click_menu(*path):
    """click_menu('Track','Show Master Track') or ('Share','Export Song to Disk…'). Items are matched by prefix so '…'/'...' both work."""
    top, *rest = path
    if not rest: raise SystemExit("need menu and item")
    body = f'set m to menu 1 of menu bar item "{top}" of menu bar 1\n'
    for i, item in enumerate(rest):
        last = i == len(rest) - 1
        body += (f'set mi to first menu item of m whose name starts with "{item.rstrip(".…")}"\n' +
                 ('click mi\nreturn "CLICKED: " & name of mi\n' if last else 'set m to menu 1 of mi\n'))
    return se(body)

def key(k, mods=""):
    """key('m','command,shift'). Common: Cmd-Shift-M = Show Master Track; B = Smart Controls; P = Plug-ins? (verify); Space = play/stop."""
    using = ""
    if mods:
        ms = ", ".join(f"{m.strip()} down" for m in mods.split(","))
        using = f" using {{{ms}}}"
    special = {"space": "keystroke space", "return": "key code 36", "escape": "key code 53", "tab": "key code 48"}
    act = special.get(k, f'keystroke "{k}"') + using
    return se(f'{act}\nreturn "KEY_SENT"')

def screenshot(name):
    """Silent screenshot of the whole screen to ~/MusicMastering/shots/<name>.png; the bot then CopyToBox's it and LOOKS at it."""
    return f'mkdir -p {WORK}/shots && screencapture -x {WORK}/shots/{Q(name)}.png && echo "SHOT={WORK}/shots/{name}.png"'

def ax_dump(limit=400):
    """Numbered list of UI elements in GarageBand's front window: index|role|name|description|value.
    Slow on big projects (can take 10-60 s). Indexes are only valid until the UI changes: use them immediately."""
    return se(f'''set out to ""
set els to entire contents of front window
set n to count of els
if n > {limit} then set n to {limit}
repeat with i from 1 to n
set e to item i of els
set r to "" & i & "|"
try
set r to r & (role of e)
end try
set r to r & "|"
try
set r to r & (name of e)
end try
set r to r & "|"
try
set r to r & (description of e)
end try
set r to r & "|"
try
set r to r & (value of e)
end try
set out to out & r & linefeed
end repeat
return out''')

def ax_act(index, expect, action="click", value=None):
    """Act on element <index> from the last ax_dump, ONLY if its name/description still contains <expect> (guards stale indexes).
    action: click | set (value) | press (AXPress) | increment | decrement."""
    v = "" if value is None else str(value).replace('"', '')
    do = {"click": "click e", "press": 'perform action "AXPress" of e', "set": f'set value of e to "{v}"',
          "increment": 'perform action "AXIncrement" of e', "decrement": 'perform action "AXDecrement" of e'}[action]
    return se(f'''set e to item {int(index)} of (entire contents of front window)
set d to ""
try
set d to d & (name of e)
end try
try
set d to d & " " & (description of e)
end try
if d does not contain "{expect}" then return "STALE_INDEX: found [" & d & "]"
{do}
delay 0.4
set after to ""
try
set after to "" & (value of e)
end try
return "ACT_OK: " & d & " -> " & after''')

def window_list():
    """Names of all GarageBand windows (plug-in windows open as separate windows named after the plug-in)."""
    return se('return (name of every window) as text')

def export_song(name):
    """Share > Export Song to Disk…, set the file name, keep the format the bot set (WAV/AIFF 24-bit; verify via screenshot),
    click Export, auto-confirm Replace only inside ~/MusicMastering/exports names this bot created (names end in '- master vN').
    Then wait for the file. Fragile: sheet layout differs by version, so the bot screenshots the sheet the first time."""
    n = name.replace('"', '')
    return ('touch /tmp/mm_export_marker && ' + click_menu("Share", "Export Song to Disk") + ' && sleep 2 && ' + se(f'''set w to front window
set s to sheet 1 of w
set value of text field 1 of s to "{n}"
delay 0.3
click (first button of s whose name is "Export")
delay 1
try
if exists sheet 1 of sheet 1 of w then
if "{n}" contains "- master v" then click (first button of sheet 1 of sheet 1 of w whose name is "Replace")
end if
end try
return "EXPORT_STARTED"''') + ' && ' + wait_export(n))

def wait_export(name, timeout=600):
    """Waits until a file named <name>.(wav|aif|aiff|m4a|mp3) newer than the marker appears and stops growing."""
    n = Q(name)
    return (f'N={n}; T=0; F=""; while [ $T -lt {timeout} ]; do '
            'F=$(find "$HOME/Music" "$HOME/Desktop" "$HOME/Documents" "$HOME/MusicMastering" -maxdepth 4 -newer /tmp/mm_export_marker '
            '\\( -name "$N.wav" -o -name "$N.aif" -o -name "$N.aiff" -o -name "$N.m4a" -o -name "$N.mp3" \\) 2>/dev/null | head -1); '
            'if [ -n "$F" ]; then S1=$(stat -f %z "$F"); sleep 3; S2=$(stat -f %z "$F"); [ "$S1" = "$S2" ] && [ "$S2" -gt 0 ] && break; fi; '
            'sleep 3; T=$((T+3)); done; [ -n "$F" ] && echo "EXPORT_FILE=$F" || echo "EXPORT_TIMEOUT"')

def measure(path):
    """Loudness check ON THE MAC when ffmpeg exists (EBU R128 integrated LUFS + true peak). Primary path is still:
    CopyToBox the export and run analysis/analyze.py on the bot's computer."""
    return (f'command -v ffmpeg >/dev/null || {{ echo "NO_FFMPEG"; exit 5; }}; ffmpeg -nostats -hide_banner -i {Q(path)} '
            '-filter_complex ebur128=peak=true -f null - 2>&1 | grep -E "^ *(I:|LRA:|Peak:)" | tail -3')

def youlean_install_help():
    """Free Youlean Loudness Meter 2 install (owner runs the installer; it asks for their Mac password, which they type, never the bot)."""
    return ('open "https://youlean.co/youlean-loudness-meter/" ; echo "Download the FREE macOS installer (no serial needed), open the .dmg, run the installer, then quit and reopen GarageBand. '
            'AU installs to /Library/Audio/Plug-Ins/Components. Never buy PRO without approval."')

def offline_master(in_path, out_path, gain_db, ceiling_db=-1.0):
    """Fallback path: render outside GarageBand (pedalboard on the bot's computer or the Mac), then import the result into
    the project copy for A/B. Never overwrites in_path. Returns the final true peak (dBTP).
    pedalboard's Limiter is not true-peak, so a final 4x-oversampled check trims the whole file until the true
    peak sits at or below ceiling_db (no clipping). Always re-check with analysis/analyze.py afterwards."""
    import numpy as np
    from scipy.signal import resample_poly
    from pedalboard import Pedalboard, Gain, Limiter  # pip install pedalboard
    from pedalboard.io import AudioFile
    if os.path.abspath(in_path) == os.path.abspath(out_path):
        raise ValueError("out_path must be a new file; never overwrite the original")
    with AudioFile(in_path) as f: x, sr = f.read(f.frames), f.samplerate
    y = Pedalboard([Gain(gain_db), Limiter(threshold_db=ceiling_db - 0.5)])(x, sr)
    tp = lambda a: 20 * np.log10(max(np.max(np.abs(resample_poly(a, 4, 1, axis=1))), 1e-12))
    peak = tp(y)
    if peak > ceiling_db:
        y = y * 10 ** ((ceiling_db - 0.05 - peak) / 20); peak = tp(y)
    with AudioFile(out_path, "w", sr, y.shape[0], bit_depth=24) as f: f.write(y)
    return round(float(peak), 2)

def import_audio(path):
    """Brings a processed file into the open project copy as a new audio track: Finder-free route via 'open -a GarageBand'
    is NOT used (it would create a new project). Instead: reveal the file and the bot asks the owner to drag it in, OR
    UI-script Track > New Track then drag is not scriptable reliably -> guided step. Returns the reveal command."""
    return f'open -R {Q(path)} && echo "Drag this file under the last track in the project copy, at bar 1."'

COMMANDS = {
    "preflight": (preflight, []), "find-projects": (find_projects, []), "copy-project": (copy_project, ["src", "?label"]),
    "inspect-band": (inspect_band, ["path"]), "open": (open_project, ["path"]), "verify-front": (verify_front_project, ["?expect"]),
    "save-copy": (save_copy, []), "menus": (menus, []), "click-menu": (click_menu, ["*path"]), "key": (key, ["k", "?mods"]),
    "screenshot": (screenshot, ["name"]), "ax-dump": (ax_dump, ["?limit"]), "ax-act": (ax_act, ["index", "expect", "?action", "?value"]),
    "windows": (window_list, []), "export": (export_song, ["name"]), "wait-export": (wait_export, ["name"]), "measure": (measure, ["path"]),
    "youlean-install": (youlean_install_help, []), "import-audio": (import_audio, ["path"]),
}

def main(argv=None):
    ap = argparse.ArgumentParser(description="Build (or on macOS with --run, execute) GarageBand control commands.")
    ap.add_argument("--run", action="store_true", help="execute (macOS only); default prints the shell command")
    ap.add_argument("cmd", choices=sorted(COMMANDS)); ap.add_argument("args", nargs="*")
    a = ap.parse_args(argv)
    fn, spec = COMMANDS[a.cmd]
    req = [s for s in spec if not s.startswith(("?", "*"))]
    if len(a.args) < len(req): ap.error(f"{a.cmd} needs: {' '.join(spec)}")
    args = [int(x) if x.isdigit() and a.cmd in ("ax-dump",) else x for x in a.args]
    cmd = fn(*args)
    if a.run:
        if sys.platform != "darwin": sys.exit("--run only works on macOS; send the printed command with Shell(machineId=...)")
        r = subprocess.run(["/bin/bash", "-c", cmd], capture_output=True, text=True); print(r.stdout + r.stderr); sys.exit(r.returncode)
    print(cmd)

if __name__ == "__main__":
    main()
