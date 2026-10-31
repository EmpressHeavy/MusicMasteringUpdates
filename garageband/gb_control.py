#!/usr/bin/env python3
"""GarageBand interface layer STUB. The Grok Bot box is Linux: every osascript call here must run on the
owner's Mac via a machine-targeted Shell (machineId) with owner approval. Nothing here runs on the box.
Requires on the Mac: Accessibility + Automation permission for the app running osascript (Terminal/agent)."""
import shlex, subprocess, sys

def osa(script, run=False):
    """Return the command; only execute when run=True AND on macOS."""
    cmd = "osascript -e " + shlex.quote(script)
    if run and sys.platform == "darwin":
        return subprocess.run(["osascript", "-e", script], capture_output=True, text=True).stdout
    return cmd

def open_project(path):        # Feasible: plain `open`
    return f"open -a GarageBand {shlex.quote(path)}"

def is_running():
    return osa('tell application "System Events" to (name of processes) contains "GarageBand"')

def list_menus():              # Discovery step before any UI click (menu titles vary by version/language)
    return osa('tell application "System Events" to tell process "GarageBand" to get name of menu bar items of menu bar 1')

def show_master_track():       # TODO: verify menu path on target GB version (Track > Show Master Track, shortcut Cmd-Shift-M)
    return osa('''tell application "GarageBand" to activate
tell application "System Events" to tell process "GarageBand" to keystroke "m" using {command down, shift down}''')

def export_song_to_disk(dest_name=None):
    """Feasible-but-fragile: Share > Export Song to Disk... then dialog. TODO: set format/quality popups via AX paths, handle Replace sheet."""
    return osa('''tell application "GarageBand" to activate
tell application "System Events" to tell process "GarageBand"
  set frontmost to true
  click menu item "Export Song to Disk…" of menu "Share" of menu bar 1
end tell''')  # NOTE: ellipsis char may be "…" or "..." depending on version — check list_menus()

def set_master_plugin(slot, plugin, params):
    """TODO (hard): inserting plugins and setting knobs requires AX paths into the Plug-ins area & plugin window.
    Plugin windows often expose few AX values. Recommended instead: give the owner step-by-step instructions
    from analyzer suggestions, or use offline_master() then reimport."""
    raise NotImplementedError

def offline_master(in_path, out_path, gain_db, ceiling_db=-1.0):
    """Fallback path: render outside GarageBand (pedalboard on the Mac or the box), then import the result into
    GarageBand (drag in or File > Open) for A/B. Never overwrites in_path. Returns the final true peak (dBTP).
    pedalboard's Limiter is not true-peak, so a final 4x-oversampled check trims the whole file until the true
    peak sits at or below ceiling_db (no clipping). Always re-check with analysis/analyze.py afterwards."""
    import os
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

if __name__ == "__main__":
    for fn in (is_running, list_menus, show_master_track, export_song_to_disk): print(fn.__name__, "=>", fn(), "\n")
