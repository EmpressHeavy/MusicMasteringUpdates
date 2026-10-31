#!/usr/bin/env python3
"""Genre presets for Music Mastering for GarageBand (v2).
Each preset is a STARTING POINT built only from GarageBand's built-in plug-ins plus the free Youlean Loudness Meter.
plan(genre, analysis, platform) merges a preset with analyze.py output into concrete settings:
  - master chain (Channel EQ -> Compressor -> Adaptive Limiter -> Youlean Loudness Meter, last, metering only)
  - per-track chains (lead vocal, backing vocals, bass, drums, other) the bot applies on individual tracks
  - loudness target (platform target, or the genre's quieter "dynamic" target when the genre wants it)
All EQ moves are capped at +/-2.5 dB and limiter gain at 0..12 dB; small moves win. No audio leaves the box/Mac.
CLI: genre_presets.py list | genre_presets.py plan <genre> <analysis.json> [--platform spotify|youtube|apple] [--out plan.json]"""
import argparse, json, sys

PLATFORMS = {"spotify": -14.0, "youtube": -14.0, "apple": -16.0}
CEILING_DBTP = -1.0
MAX_EQ_DB, MAX_LIMITER_GAIN = 2.5, 12.0

# Reference band balance (dB relative to loudest band, same bands as analyze.py) per genre family.
REF = {
    "bass_heavy": {"sub": -8, "bass": 0, "low_mid": -10, "mid": -9, "high_mid": -18, "air": -24},
    "balanced":   {"sub": -14, "bass": -2, "low_mid": -8, "mid": -4, "high_mid": -14, "air": -22},
    "bright":     {"sub": -16, "bass": -3, "low_mid": -8, "mid": -3, "high_mid": -11, "air": -19},
    "acoustic":   {"sub": -20, "bass": -5, "low_mid": -6, "mid": 0, "high_mid": -12, "air": -21},
}

def comp(ratio, attack, release, gr, why): return {"ratio": ratio, "attack_ms": attack, "release_ms": release, "target_gain_reduction_db": gr, "why": why}

VOCAL_STD = [
    {"plugin": "Channel EQ", "moves": [{"type": "low_cut", "freq_hz": 90, "why": "Removes rumble and mic handling below the voice."},
                                        {"type": "bell", "freq_hz": 300, "gain_db": -2.0, "q": 1.2, "why": "Clears boxiness."},
                                        {"type": "high_shelf", "freq_hz": 8000, "gain_db": 1.5, "why": "Adds presence and air."}]},
    {"plugin": "Compressor", "settings": comp("3:1", 10, 80, "3-6", "Keeps every word at a steady level.")},
    {"plugin": "DeEsser 2", "settings": {"frequency_hz": 6500, "reduction_db": 4, "why": "Tames harsh S and T sounds after the EQ boost."}},
]
TRACKS_STD = {
    "lead_vocal": VOCAL_STD,
    "backing_vocals": [{"plugin": "Channel EQ", "moves": [{"type": "low_cut", "freq_hz": 150, "why": "Leaves the low end to the lead and bass."},
                                                          {"type": "bell", "freq_hz": 3000, "gain_db": -1.5, "q": 1.0, "why": "Sits them behind the lead."}]},
                       {"plugin": "Compressor", "settings": comp("4:1", 10, 100, "4-6", "Glues the stack together.")},
                       {"plugin": "DeEsser 2", "settings": {"frequency_hz": 6500, "reduction_db": 5, "why": "Stacked S sounds add up fast."}}],
    "bass": [{"plugin": "Channel EQ", "moves": [{"type": "low_cut", "freq_hz": 35, "why": "Removes inaudible sub rumble."},
                                                {"type": "bell", "freq_hz": 250, "gain_db": -1.5, "q": 1.0, "why": "Less mud, more note definition."}]},
             {"plugin": "Compressor", "settings": comp("4:1", 20, 120, "3-5", "Even note levels so the low end is steady.")}],
    "drums": [{"plugin": "Channel EQ", "moves": [{"type": "bell", "freq_hz": 400, "gain_db": -1.5, "q": 1.0, "why": "Less boxy kit."},
                                                 {"type": "high_shelf", "freq_hz": 10000, "gain_db": 1.0, "why": "Crisper cymbals."}]},
              {"plugin": "Compressor", "settings": comp("4:1", 30, 100, "2-4", "Punch: slow attack lets the hit through.")}],
    "other": [{"plugin": "Channel EQ", "moves": [{"type": "low_cut", "freq_hz": 100, "why": "Makes room for bass and kick."}]}],
}

def P(family, comp_s, limiter_char, dynamic_target=None, vocal=None, notes=""):
    return {"family": family, "master_compressor": comp_s, "limiter_style": limiter_char,
            "dynamic_target_lufs": dynamic_target, "tracks": dict(TRACKS_STD, **(vocal or {})), "notes": notes}

PRESETS = {
    "pop": P("bright", comp("2:1", 30, 150, "1-2", "Gentle glue for a polished, even mix."), "transparent"),
    "hip-hop": P("bass_heavy", comp("2:1", 30, 100, "1-3", "Holds the kick and 808 steady."), "punchy",
                 notes="Watch sub energy: a loud 808 uses most of the headroom."),
    "rnb": P("bass_heavy", comp("1.5:1", 30, 200, "1-2", "Smooth glue that keeps the groove breathing."), "transparent"),
    "rock": P("balanced", comp("2:1", 20, 120, "2-3", "Holds guitars and drums together."), "punchy"),
    "edm": P("bass_heavy", comp("2:1", 10, 80, "2-3", "Tight, steady energy for the drop."), "punchy",
             notes="Streaming will turn very loud masters down; -14 LUFS keeps the punch."),
    "country": P("bright", comp("2:1", 30, 150, "1-2", "Even glue; keeps the vocal front."), "transparent"),
    "acoustic": P("acoustic", comp("1.5:1", 40, 250, "1", "Barely-there glue to keep it natural."), "transparent", dynamic_target=-16.0),
    "jazz": P("acoustic", comp("1.5:1", 40, 300, "0-1", "Protects the dynamics players worked for."), "transparent", dynamic_target=-16.0),
    "lofi": P("balanced", comp("3:1", 30, 150, "2-4", "Warm, squashed feel that suits the style."), "soft",
              notes="Rolled-off highs are part of the sound; skip air boosts."),
    "classical": P("acoustic", None, "transparent", dynamic_target=-18.0,
                   notes="No glue compression; only a safety limiter. Quieter target keeps the dynamics."),
    "spoken": P("balanced", comp("3:1", 10, 100, "3-6", "Even speech level."), "transparent", dynamic_target=-16.0,
                notes="Podcasts and audiobooks: -16 LUFS is the common spoken-word reference."),
}
ALIASES = {"hip hop": "hip-hop", "hiphop": "hip-hop", "rap": "hip-hop", "trap": "hip-hop", "r&b": "rnb", "r and b": "rnb", "soul": "rnb",
           "dance": "edm", "electronic": "edm", "house": "edm", "techno": "edm", "folk": "acoustic", "singer-songwriter": "acoustic",
           "lo-fi": "lofi", "lo fi": "lofi", "metal": "rock", "punk": "rock", "indie": "rock", "orchestral": "classical",
           "podcast": "spoken", "audiobook": "spoken", "gospel": "rnb", "latin": "pop", "reggaeton": "hip-hop", "afrobeats": "pop", "k-pop": "pop"}

def resolve(genre):
    g = genre.strip().lower()
    g = ALIASES.get(g, g)
    if g not in PRESETS: raise KeyError(f"unknown genre '{genre}'. Known: {', '.join(sorted(PRESETS))} (or aliases: {', '.join(sorted(ALIASES))})")
    return g

clamp = lambda v, lo, hi: max(lo, min(hi, v))

def plan(genre, analysis, platform="spotify"):
    g = resolve(genre); p = PRESETS[g]
    if platform not in PLATFORMS: raise KeyError(f"unknown platform '{platform}'")
    target = PLATFORMS[platform] if p["dynamic_target_lufs"] is None else min(PLATFORMS[platform], p["dynamic_target_lufs"])
    ref = REF[p["family"]]; bands = analysis.get("band_energy_db_rel", {})
    eq, notes = [], []
    if bands:
        dev = {b: bands[b] - ref[b] for b in ref if b in bands}
        if dev.get("sub", 0) > 3: eq.append({"type": "low_cut", "freq_hz": 30, "why": "More sub than this genre usually carries; frees headroom."})
        for band, freq, kind in (("low_mid", 300, "bell"), ("mid", 1000, "bell"), ("high_mid", 3500, "bell"), ("air", 10000, "high_shelf"), ("bass", 100, "low_shelf")):
            d = dev.get(band, 0)
            if abs(d) >= 3:
                if band == "air" and g == "lofi" and d < 0: continue
                gain = round(clamp(-d / 3, -MAX_EQ_DB, MAX_EQ_DB), 1)
                eq.append({"type": kind, "freq_hz": freq, "gain_db": gain, "q": 1.0,
                           "why": f"{band.replace('_', '-')} is {abs(d):.0f} dB {'above' if d > 0 else 'below'} a typical {g} balance."})
    lowcut = [m for m in eq if m["type"] == "low_cut"]
    eq = lowcut + sorted([m for m in eq if m["type"] != "low_cut"], key=lambda m: -abs(m["gain_db"]))[:3]  # at most 3 tone moves
    lufs = analysis.get("integrated_lufs")
    gain = None if lufs is None else round(target - lufs, 1)
    if analysis.get("clipped_samples"): notes.append("The mix itself clips: lower the loudest tracks (or the mix) before mastering; a limiter can't undo clipping.")
    if gain is not None and gain < 0: notes.append(f"Already {abs(gain)} dB louder than {target} LUFS: no limiter gain; optionally lower Master Volume {abs(gain)} dB.")
    if gain is not None and gain > MAX_LIMITER_GAIN: notes.append(f"Needs {gain} dB: more than a limiter should add. Raise track levels in the mix first, then re-measure.")
    lim_gain = None if gain is None else clamp(gain, 0.0, MAX_LIMITER_GAIN)
    if p["notes"]: notes.append(p["notes"])
    master = [{"slot": 1, "plugin": "Channel EQ", "moves": eq or [{"type": "none", "why": f"Balance already fits {g}; leave EQ flat."}]},
              {"slot": 2, "plugin": "Compressor", "settings": p["master_compressor"] or {"bypass": True, "why": "This genre keeps its dynamics."}},
              {"slot": 3, "plugin": "Adaptive Limiter", "settings": {"gain_db": lim_gain, "out_ceiling_db": CEILING_DBTP, "style": p["limiter_style"],
               "why": f"Brings it to about {target} LUFS with peaks under {CEILING_DBTP} dBTP."}},
              {"slot": 4, "plugin": "Youlean Loudness Meter 2 (Audio Units > Youlean)", "settings": {"mode": "metering only", "target_integrated_lufs": target, "max_true_peak_dbtp": CEILING_DBTP,
               "why": "Last in the chain so it reads exactly what gets exported. It never changes the sound."}}]
    return {"genre": g, "platform": platform, "target_integrated_lufs": target, "true_peak_ceiling_dbtp": CEILING_DBTP,
            "measured_integrated_lufs": lufs, "limiter_gain_db": lim_gain, "master_chain": master, "track_chains": p["tracks"],
            "tolerance": {"integrated_lufs": 1.0, "true_peak_max_dbtp": CEILING_DBTP}, "notes": notes}

def check(post, plan_):
    """Pass/fail of an exported master against the plan, with the next small move."""
    t, tol = plan_["target_integrated_lufs"], plan_["tolerance"]["integrated_lufs"]
    lufs, tp, clip = post["integrated_lufs"], post["true_peak_dbtp"], post.get("clipped_samples", 0)
    moves = []
    if tp > CEILING_DBTP or clip: moves.append("Lower Adaptive Limiter Gain 0.5-1 dB (true peak or clipping over the ceiling).")
    if lufs < t - tol: moves.append(f"Raise Adaptive Limiter Gain about {round(min(t - lufs, 3), 1)} dB.")
    if lufs > t + tol:
        if (plan_.get("limiter_gain_db") or 0) > 0: moves.append(f"Lower Adaptive Limiter Gain about {round(min(lufs - t, 3), 1)} dB.")
        else: moves.append(f"Optional: lower Master Volume about {round(lufs - t, 1)} dB (platforms will turn it down anyway; the mix was already loud).")
    return {"pass": not moves, "integrated_lufs": lufs, "true_peak_dbtp": tp, "target": t, "next_moves": moves}

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); s = ap.add_subparsers(dest="cmd", required=True)
    s.add_parser("list")
    p = s.add_parser("plan"); p.add_argument("genre"); p.add_argument("analysis"); p.add_argument("--platform", default="spotify", choices=PLATFORMS); p.add_argument("--out")
    p = s.add_parser("check"); p.add_argument("post"); p.add_argument("plan")
    a = ap.parse_args()
    if a.cmd == "list":
        for k, v in PRESETS.items(): print(f"{k}: family={v['family']} dynamic_target={v['dynamic_target_lufs']}")
        print("aliases:", ", ".join(f"{k}->{v}" for k, v in sorted(ALIASES.items()))); sys.exit()
    if a.cmd == "plan":
        try: r = plan(a.genre, json.load(open(a.analysis)), a.platform)
        except KeyError as e: sys.exit(str(e))
    else: r = check(json.load(open(a.post)), json.load(open(a.plan)))
    out = json.dumps(r, indent=2); open(a.out, "w").write(out) if getattr(a, "out", None) else print(out)
