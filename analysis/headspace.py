#!/usr/bin/env python3
"""Headspace: 'ears' for the bot. WAV -> JSON + PNGs describing stereo image, space and depth.
Usage: headspace.py FILE [--outdir DIR] [--max-seconds N]
Outputs DIR/headspace.json plus spectrogram.png, pan_map.png, midside.png, correlation.png,
goniometer.png, depth.png. Read-only on the input file."""
import argparse, json, os
import numpy as np, soundfile as sf
from scipy import signal
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

BANDS = [("sub", 20, 60), ("bass", 60, 250), ("low_mid", 250, 500), ("mid", 500, 2000),
         ("high_mid", 2000, 6000), ("air", 6000, 16000)]
ROLE = {"sub": "sub/kick", "bass": "bass", "low_mid": "low mids (body, guitars, keys)", "mid": "mids (vocal, leads)",
        "high_mid": "presence (vocal bite, snare, cymbals)", "air": "air (cymbals, breath, reverb shimmer)"}
db = lambda x: 10 * np.log10(np.maximum(x, 1e-12))

def pan_word(p):
    a = abs(p)
    side = "left" if p < 0 else "right"
    return "centered" if a < 0.1 else (f"slightly {side}" if a < 0.3 else (f"{side}" if a < 0.6 else f"hard {side}"))

def width_word(w):
    return "mono/narrow" if w < 0.1 else "narrow" if w < 0.25 else "moderately wide" if w < 0.5 else "wide" if w < 0.8 else "very wide"

def analyze(path, outdir, max_s=None):
    x, sr = sf.read(path, always_2d=True, dtype="float64")
    if max_s: x = x[: int(max_s * sr)]
    if x.shape[1] == 1: x = np.repeat(x, 2, axis=1)
    L, R = x[:, 0], x[:, 1]; M, S = (L + R) / 2, (L - R) / 2
    os.makedirs(outdir, exist_ok=True)
    nfft, hop = 4096, 2048
    f, t, ZL = signal.stft(L, sr, nperseg=nfft, noverlap=nfft - hop)
    _, _, ZR = signal.stft(R, sr, nperseg=nfft, noverlap=nfft - hop)
    PL, PR = np.abs(ZL) ** 2, np.abs(ZR) ** 2
    PM, PS = np.abs((ZL + ZR) / 2) ** 2, np.abs((ZL - ZR) / 2) ** 2
    cross = np.real(ZL * np.conj(ZR))
    # bin pan: -1 = hard left, +1 = hard right (energy-based)
    pan_bins = (PR - PL) / (PR + PL + 1e-20)
    # aggregate pan map into 1-s frames x 24 log bands
    edges = np.geomspace(30, min(16000, sr / 2 - 1), 25)
    fr = max(1, int(round(sr / hop)))
    nT = PL.shape[1] // fr
    pan_map = np.zeros((24, max(nT, 1))); en_map = np.zeros_like(pan_map)
    for i in range(24):
        sel = (f >= edges[i]) & (f < edges[i + 1])
        if not sel.any(): continue
        for j in range(nT):
            sl = slice(j * fr, (j + 1) * fr)
            l, r = PL[sel, sl].sum(), PR[sel, sl].sum()
            pan_map[i, j] = (r - l) / (r + l + 1e-20); en_map[i, j] = l + r
    bands = {}
    for n, lo, hi in BANDS:
        sel = (f >= lo) & (f < hi)
        l, r, m, s, c = PL[sel].sum(), PR[sel].sum(), PM[sel].sum(), PS[sel].sum(), cross[sel].sum()
        corr = float(c / np.sqrt(l * r + 1e-30))
        # energy-weighted spread of per-bin pan = how much stuff sits off-centre in this band
        w = (PL[sel] + PR[sel]); spread = float(np.sqrt((w * pan_bins[sel] ** 2).sum() / (w.sum() + 1e-30)))
        bands[n] = {"pan": round(float((r - l) / (r + l + 1e-30)), 3), "side_to_mid": round(float(np.sqrt(s / (m + 1e-30))), 3),
                    "side_minus_mid_db": round(float(db(s) - db(m)), 1), "correlation": round(corr, 3),
                    "pan_spread": round(spread, 3), "energy_db_rel": 0.0}
    tot = sum(PL[(f >= lo) & (f < hi)].sum() + PR[(f >= lo) & (f < hi)].sum() for _, lo, hi in BANDS)
    for n, lo, hi in BANDS:
        sel = (f >= lo) & (f < hi); bands[n]["energy_db_rel"] = round(float(db((PL[sel].sum() + PR[sel].sum()) / tot)), 1)
    # correlation over time (400 ms windows)
    win = int(0.4 * sr); nw = len(L) // win
    ct = np.array([np.corrcoef(L[k*win:(k+1)*win], R[k*win:(k+1)*win])[0, 1] if np.std(L[k*win:(k+1)*win]) > 1e-6 and np.std(R[k*win:(k+1)*win]) > 1e-6 else 1.0 for k in range(nw)])
    rms_t = np.array([np.sqrt(np.mean(M[k*win:(k+1)*win] ** 2)) for k in range(nw)])
    loud = rms_t > np.percentile(rms_t, 30) if nw else np.array([], bool)
    corr_all = float(np.corrcoef(L, R)[0, 1]) if np.std(L) > 0 and np.std(R) > 0 else 1.0
    mono_loss_db = float(db(np.mean(M ** 2)) - db((np.mean(L ** 2) + np.mean(R ** 2)) / 2))  # mono fold-down vs stereo
    # depth / reverb: tail decay after transient drops + late/early energy ratio
    env_hop = int(0.01 * sr)
    env = np.sqrt(np.convolve(M ** 2, np.ones(env_hop) / env_hop, "same")[::env_hop]) + 1e-9
    edb = 20 * np.log10(env)
    decays = []
    pk, _ = signal.find_peaks(edb, prominence=12, distance=20)
    for p in pk:
        seg = edb[p:p + 150]
        if len(seg) < 40: continue
        drop = seg[0] - seg
        i10 = np.argmax(drop >= 10) if (drop >= 10).any() else None
        i25 = np.argmax(drop >= 25) if (drop >= 25).any() else None
        if i10 and i25 and i25 > i10: decays.append((i25 - i10) * 0.01 * 60 / 15)  # extrapolated RT60 from -10..-25 dB slope
    rt60 = float(np.median(decays)) if len(decays) >= 3 else None
    # DRR proxy: energy within 50 ms of onsets vs 50-300 ms after (higher = drier/closer)
    d_e, r_e = [], []
    for p in pk:
        a = env[p:p + 5] ** 2; b = env[p + 5:p + 30] ** 2
        if len(b) == 25: d_e.append(a.sum()); r_e.append(b.sum())
    drr = float(db(np.sum(d_e) / (np.sum(r_e) + 1e-20))) if d_e else None
    side_tail = float(db(np.mean(S ** 2)) - db(np.mean(M ** 2)))
    depth_word = "unknown"
    if rt60 is None:
        depth_word = "inconclusive (dense mix, no clean tails)"
    else:
        score = (rt60 or 0.8) / 0.8 - (drr if drr is not None else 0) / 6
        depth_word = "dry and up-front" if score < 0.3 else "a little room, mostly close" if score < 0.9 else "noticeably roomy/reverberant" if score < 1.6 else "very washy, far back"
    # summary lines
    lines = []
    lines.append(f"Overall: {width_word(np.sqrt(np.mean(S**2)/(np.mean(M**2)+1e-20)))} stereo image, L/R correlation {corr_all:.2f} "
                 f"({'mono-safe' if corr_all > 0.5 else 'check mono' if corr_all > 0.1 else 'mono risk: parts may cancel'}).")
    bal = float(db(np.mean(R ** 2)) - db(np.mean(L ** 2)))
    lines.append(f"Left/right balance: {'even' if abs(bal) < 0.5 else ('leans right' if bal > 0 else 'leans left')} ({bal:+.1f} dB R vs L).")
    for n, *_ in BANDS:
        b = bands[n]
        if b["energy_db_rel"] < -35: continue
        where = pan_word(b["pan"]); w = width_word(b["side_to_mid"])
        lines.append(f"{ROLE[n].capitalize()}: {where}, {w}" + (f"; stuff spread to the sides (spread {b['pan_spread']:.2f})" if b["pan_spread"] > 0.35 and abs(b['pan']) < 0.1 else "")
                     + (" - LOW CORRELATION, may vanish in mono" if b["correlation"] < 0.2 and abs(b["pan"]) < 0.6 else "") + ".")
    for n in ("sub", "bass"):
        if bands[n]["side_to_mid"] > 0.3 and bands[n]["energy_db_rel"] > -30:
            lines.append(f"Watch out: {ROLE[n]} is wide (side/mid {bands[n]['side_to_mid']:.2f}); low end usually works best centered/mono.")
    if bands["mid"]["side_to_mid"] < 0.3 and abs(bands["mid"]["pan"]) < 0.1:
        lines.append("Vocal/lead range looks centered and solid.")
    if bands["high_mid"]["side_to_mid"] > bands["mid"]["side_to_mid"] + 0.2 or bands["air"]["side_to_mid"] > bands["mid"]["side_to_mid"] + 0.2:
        lines.append("Highs are wider than the mids: pads, doubles, cymbals or reverb sit wide around a centered core.")
    lines.append(f"Mono fold-down changes level by {mono_loss_db:+.1f} dB" + (" (fine)." if mono_loss_db > -3.5 else " (noticeable loss in mono)."))
    if nw:
        bad = float(np.mean(ct[loud] < 0)) * 100 if loud.any() else 0
        if bad > 2: lines.append(f"Out-of-phase moments: {bad:.0f}% of the loud sections have negative correlation.")
        neg = np.where(ct < -0.1)[0]
        if len(neg) >= 5:
            runs = np.split(neg, np.where(np.diff(neg) > 2)[0] + 1); r = max(runs, key=len)
            if len(r) >= 5: lines.append(f"Longest out-of-phase stretch: {r[0]*0.4:.0f}-{(r[-1]+1)*0.4:.0f} s (often a stereo reverb/widener tail; check it in mono).")
    det = ([f"tail ~{rt60:.2f} s"] if rt60 else []) + ([f"direct/reverb ~{drr:+.1f} dB"] if drr is not None else [])
    lines.append(f"Depth: {depth_word}" + (f" ({', '.join(det)})" if det else "") + " (rough estimate).")
    # ---------- images ----------
    imgs = {}
    def save(fig, name):
        p = os.path.join(outdir, name); fig.savefig(p, dpi=110, bbox_inches="tight"); plt.close(fig); imgs[name[:-4]] = p
    mono_db = db((PL + PR) / 2); keep = f <= 16000
    fig, ax = plt.subplots(figsize=(12, 5))
    im = ax.pcolormesh(t, f[keep][1:], mono_db[keep][1:], shading="auto", cmap="magma", vmin=mono_db.max() - 90, vmax=mono_db.max())
    ax.set_yscale("log"); ax.set_ylim(30, 16000); ax.set_xlabel("time (s)"); ax.set_ylabel("Hz"); ax.set_title("Spectrogram (mid, dB)")
    fig.colorbar(im, ax=ax); save(fig, "spectrogram.png")
    fig, ax = plt.subplots(figsize=(12, 5))
    alpha = np.clip((db(en_map) - db(en_map.max()) + 60) / 60, 0, 1)
    rgba = plt.cm.coolwarm((pan_map + 1) / 2); rgba[..., 3] = 0.15 + 0.85 * alpha
    ax.imshow(rgba, aspect="auto", origin="lower", extent=[0, nT, 0, 24], interpolation="nearest")
    yt = [0, 4, 8, 12, 16, 20, 23]; ax.set_yticks([y + 0.5 for y in yt]); ax.set_yticklabels([f"{edges[y]:.0f}" for y in yt])
    ax.set_xlabel("time (s)"); ax.set_ylabel("band start (Hz)")
    ax.set_title("Pan per frequency band over time (blue = left, white = center, red = right; faint = quiet)")
    sm = plt.cm.ScalarMappable(cmap="coolwarm", norm=plt.Normalize(-1, 1)); fig.colorbar(sm, ax=ax, label="pan  L -1 ... +1 R")
    save(fig, "pan_map.png")
    names = [n for n, *_ in BANDS]
    fig, axs = plt.subplots(1, 3, figsize=(14, 4.5))
    axs[0].bar(names, [bands[n]["side_minus_mid_db"] for n in names], color="tab:purple"); axs[0].axhline(-10, ls="--", c="gray")
    axs[0].set_title("Side minus Mid (dB) per band\n(higher = wider; >-6 is very wide)"); axs[0].tick_params(axis="x", rotation=35)
    axs[1].bar(names, [bands[n]["pan"] for n in names], color=["tab:blue" if bands[n]["pan"] < 0 else "tab:red" for n in names])
    axs[1].set_ylim(-1, 1); axs[1].axhline(0, c="k"); axs[1].set_title("Average pan per band (L- / R+)"); axs[1].tick_params(axis="x", rotation=35)
    axs[2].bar(names, [bands[n]["correlation"] for n in names], color="tab:green"); axs[2].set_ylim(-1, 1); axs[2].axhline(0, c="k")
    axs[2].set_title("L/R correlation per band\n(<0.2 = mono risk)"); axs[2].tick_params(axis="x", rotation=35)
    save(fig, "midside.png")
    fig, ax = plt.subplots(figsize=(12, 3.5))
    tt = np.arange(nw) * 0.4
    ax.fill_between(tt, ct, 0, where=ct >= 0, color="tab:green", alpha=.6); ax.fill_between(tt, ct, 0, where=ct < 0, color="tab:red", alpha=.8)
    ax.set_ylim(-1, 1); ax.axhline(0.2, ls="--", c="gray"); ax.set_xlabel("time (s)")
    ax.set_title(f"L/R correlation over time (overall {corr_all:.2f}; red = out of phase, mono risk)"); save(fig, "correlation.png")
    fig, ax = plt.subplots(figsize=(6, 6))
    idx = np.random.default_rng(0).choice(len(M), min(60000, len(M)), replace=False)
    sc = max(np.max(np.abs(x)), 1e-9)
    ax.scatter(S[idx] / sc * np.sqrt(2), M[idx] / sc * np.sqrt(2), s=0.3, alpha=0.25, c="tab:cyan")
    ax.set_xlim(-1, 1); ax.set_ylim(-1, 1); ax.set_aspect("equal"); ax.axvline(0, c="gray", lw=.5); ax.axhline(0, c="gray", lw=.5)
    ax.set_xlabel("side (L-R)"); ax.set_ylabel("mid (L+R)")
    ax.set_title("Goniometer (vertical line = mono, round blob = wide,\nhorizontal = out of phase)"); save(fig, "goniometer.png")
    fig, axs = plt.subplots(1, 2, figsize=(13, 4))
    te = np.arange(len(edb)) * 0.01; axs[0].plot(te, edb, lw=.5); axs[0].plot(te[pk], edb[pk], "rv", ms=3)
    axs[0].set_ylim(edb.max() - 60, edb.max() + 3); axs[0].set_title("Envelope (dB) with detected hits used for tail estimate"); axs[0].set_xlabel("time (s)")
    if decays: axs[1].hist(decays, bins=20, color="tab:orange")
    axs[1].set_title(f"Estimated decay times (RT60-ish), median {rt60:.2f} s" if rt60 else "Not enough clean hits for tail estimate"); axs[1].set_xlabel("s")
    save(fig, "depth.png")
    out = {"file": path, "sample_rate": sr, "duration_s": round(len(x) / sr, 2), "correlation": round(corr_all, 3),
           "lr_balance_db": round(bal, 2), "mono_folddown_change_db": round(mono_loss_db, 2), "side_minus_mid_db": round(side_tail, 1),
           "bands": bands, "depth": {"rt60_est_s": round(rt60, 2) if rt60 else None, "drr_est_db": round(drr, 1) if drr is not None else None,
           "hits_used": len(decays), "description": depth_word},
           "summary": lines, "images": imgs,
           "note": "Estimates from signal math, not hearing. Pan/width are reliable; depth/reverb numbers are rough proxies."}
    json.dump(out, open(os.path.join(outdir, "headspace.json"), "w"), indent=2)
    return out

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("file"); ap.add_argument("--outdir"); ap.add_argument("--max-seconds", type=float)
    a = ap.parse_args()
    od = a.outdir or os.path.splitext(a.file)[0] + "_headspace"
    r = analyze(a.file, od, a.max_seconds)
    print("\n".join(r["summary"])); print(f"\nJSON + images in {od}")
