#!/usr/bin/env python3
"""Mastering analyzer: WAV/AIFF -> JSON metrics + suggested GarageBand master-track settings.
Usage: analyze.py FILE [--target spotify|apple|youtube] [--out report.json]"""
import argparse, json, sys
import numpy as np, soundfile as sf, pyloudnorm as pyln
from scipy import signal

TARGETS = {"spotify": (-14.0, -1.0), "youtube": (-14.0, -1.0), "apple": (-16.0, -1.0)}
BANDS = [("sub", 20, 60), ("bass", 60, 250), ("low_mid", 250, 500), ("mid", 500, 2000),
         ("high_mid", 2000, 6000), ("air", 6000, 20000)]
db = lambda x: float(20 * np.log10(max(x, 1e-12)))

def true_peak(x, sr):
    up = signal.resample_poly(x, 4, 1, axis=0)  # 4x oversample (BS.1770 style approx)
    return db(np.max(np.abs(up)))

def lra(x, sr, meter):
    win, hop = int(3 * sr), int(sr)  # 3 s short-term windows, 1 s hop
    vals = []
    for s in range(0, max(len(x) - win, 0) + 1, hop):
        try:
            v = meter.integrated_loudness(x[s:s + win])
        except Exception:
            continue
        if np.isfinite(v) and v > -70: vals.append(v)
    if len(vals) < 2: return 0.0
    v = np.array(vals); v = v[v > 10 * np.log10(np.mean(10 ** (v / 10))) - 20]
    return float(np.percentile(v, 95) - np.percentile(v, 10)) if len(v) > 1 else 0.0

def analyze(path, target="spotify"):
    x, sr = sf.read(path, always_2d=True, dtype="float64")
    mono = x.mean(axis=1)
    meter = pyln.Meter(sr)
    lufs = float(meter.integrated_loudness(x))
    peak = db(np.max(np.abs(x))); tp = true_peak(x, sr)
    rms = db(np.sqrt(np.mean(mono ** 2)))
    clip = int(np.sum(np.abs(x) >= 0.999))
    f, p = signal.welch(mono, sr, nperseg=8192)
    tot = np.sum(p) + 1e-20
    bands = {n: round(float(10 * np.log10(np.sum(p[(f >= lo) & (f < hi)]) / tot + 1e-12)), 2) for n, lo, hi in BANDS}
    if x.shape[1] >= 2:
        L, R = x[:, 0], x[:, 1]; mid, side = (L + R) / 2, (L - R) / 2
        corr = float(np.corrcoef(L, R)[0, 1]) if np.std(L) > 0 and np.std(R) > 0 else 1.0
        width = float(np.sqrt(np.mean(side ** 2)) / (np.sqrt(np.mean(mid ** 2)) + 1e-12))
    else:
        corr, width = 1.0, 0.0
    m = {"file": path, "sample_rate": sr, "channels": x.shape[1], "duration_s": round(len(x) / sr, 2),
         "integrated_lufs": round(lufs, 2), "sample_peak_dbfs": round(peak, 2), "true_peak_dbtp": round(tp, 2),
         "headroom_db": round(-tp, 2), "rms_dbfs": round(rms, 2), "crest_factor_db": round(peak - rms, 2),
         "lra_lu": round(lra(x, sr, meter), 2), "clipped_samples": clip,
         "band_energy_db_rel": bands, "stereo_correlation": round(corr, 3), "side_to_mid_ratio": round(width, 3)}
    m["suggestions"] = suggest(m, target)
    return m

def suggest(m, target):
    tl, tp_ceil = TARGETS[target]
    gain = round(tl - m["integrated_lufs"], 1)
    notes, eq = [], []
    if m["clipped_samples"]: notes.append("Clipping found: lower the mix (track/master volume) before mastering; a limiter can't undo clipped samples.")
    if m["true_peak_dbtp"] > -1: notes.append("True peak above -1 dBTP: streaming encoders may distort it. The Adaptive Limiter output ceiling will fix this.")
    b = m["band_energy_db_rel"]
    if b["sub"] > -8: eq.append({"type": "low_cut", "freq_hz": 30, "why": "Heavy sub-bass eats headroom you can't hear on most speakers."})
    if b["low_mid"] > -6: eq.append({"type": "bell", "freq_hz": 300, "gain_db": -1.5, "q": 1.0, "why": "Low-mid build-up sounds muddy."})
    if b["air"] < -25: eq.append({"type": "high_shelf", "freq_hz": 10000, "gain_db": 1.5, "why": "Little top-end; a gentle shelf adds air."})
    comp = None
    if m["crest_factor_db"] > 18 or m["lra_lu"] > 12:
        comp = {"plugin": "Compressor (or Multipressor for band-specific control)", "ratio": "1.5:1-2:1", "attack_ms": 30,
                "release_ms": 150, "target_gain_reduction_db": "1-3", "why": "Wide dynamics; gentle glue compression evens it without squashing."}
    if gain < 0:
        notes.append(f"Already about {abs(gain)} dB louder than the {tl} LUFS target: the service will turn it down. Don't add limiter gain; "
                     f"optionally lower the Master Volume about {abs(gain)} dB (or leave it if you like the sound), and keep the {tp_ceil} dB ceiling.")
    if m["stereo_correlation"] < 0.2 and m["channels"] > 1:
        notes.append("Low L/R correlation: may sound thin or vanish in mono. Check mono and narrow wide parts in the mix.")
    return {"platform_target": {"platform": target, "integrated_lufs": tl, "true_peak_ceiling_dbtp": tp_ceil},
            "loudness_change_needed_db": gain,
            "garageband_master_chain": [
                {"slot": 1, "plugin": "Channel EQ", "moves": eq or [{"type": "none", "why": "Balance looks fine; leave EQ flat."}]},
                {"slot": 2, "plugin": comp["plugin"] if comp else "Compressor", "settings": comp or {"bypass": True, "why": "Dynamics already controlled."}},
                {"slot": 3, "plugin": "Adaptive Limiter", "settings": {"gain_db": max(0.0, gain), "out_ceiling_db": tp_ceil - 0.0,
                 "why": f"Raises loudness ~{max(0.0, gain)} dB toward {tl} LUFS while keeping peaks under {tp_ceil} dBTP."}}],
            "export": "Share > Export Song to Disk: WAV/AIFF, 24-bit, then re-run this analyzer on the export.",
            "notes": notes}

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("file"); ap.add_argument("--target", default="spotify", choices=TARGETS)
    ap.add_argument("--out"); a = ap.parse_args()
    r = json.dumps(analyze(a.file, a.target), indent=2)
    open(a.out, "w").write(r) if a.out else print(r)
