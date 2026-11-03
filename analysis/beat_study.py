#!/usr/bin/env python3
"""Beat study: dissect a reference's groove so the owner can build an ORIGINAL beat with a similar feel.
Usage: beat_study.py REFERENCE [--outdir DIR] [--max-seconds N]
REFERENCE = local audio file or public link (same rules as reference_match.py: decoded to a temp folder,
analyzed, audio deleted; only numbers + images kept; the owner's own file is never modified).
Outputs DIR/beat_study.json, drum_grid.png, structure.png and plain-words GarageBand build notes.
Signal heuristics (band onsets), no AI model; treat results as a starting point, not a transcription."""
import argparse, json, os, shutil, sys, tempfile
import numpy as np, librosa
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from reference_match import fetch_reference, is_link, STUDY_NOTE

SR, HOP = 22050, 256
KEYS = ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"]
MAJ = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
MIN = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])
DRUMS = {"kick": (30, 120), "snare": (180, 2500), "hats": (7000, 11000)}

def key_of(y):
    c = librosa.feature.chroma_cqt(y=librosa.effects.harmonic(y), sr=SR).mean(axis=1)
    best = max(((np.corrcoef(np.roll(p, k), c)[0, 1], f"{KEYS[k]} {m}") for k in range(12) for p, m in ((MAJ, "major"), (MIN, "minor"))))
    return best[1], round(float(best[0]), 2)

def band_env(S, freqs, lo, hi):
    sel = (freqs >= lo) & (freqs < hi)
    b = np.sqrt(S[sel].sum(axis=0))  # band amplitude (linear, so quiet leakage doesn't trigger)
    e = np.maximum(0, np.diff(b, prepend=b[0]))
    return e / (np.percentile(e, 99) + 1e-9)

def study(path, outdir, label, max_s=None):
    y, _ = librosa.load(path, sr=SR, mono=True, duration=max_s)
    os.makedirs(outdir, exist_ok=True)
    tempo, beats = librosa.beat.beat_track(y=y, sr=SR, hop_length=HOP)
    tempo = float(np.atleast_1d(tempo)[0])
    while tempo < 70: tempo *= 2; beats = None
    while tempo > 180: tempo /= 2; beats = None
    if beats is None or len(beats) < 8:
        _, beats = librosa.beat.beat_track(y=y, sr=SR, hop_length=HOP, bpm=tempo)
    bt = librosa.frames_to_time(beats, sr=SR, hop_length=HOP)
    S = librosa.feature.melspectrogram(y=y, sr=SR, hop_length=HOP, n_mels=128, fmax=11025)
    mf = librosa.mel_frequencies(n_mels=128, fmax=11025)
    env = {k: band_env(S, mf, *v) for k, v in DRUMS.items()}
    # snare: mids minus what the kick explains
    env["snare"] = np.clip(env["snare"] - 1.0 * env["kick"], 0, None); env["snare"] /= np.percentile(env["snare"], 99) + 1e-9
    nT = len(env["kick"]); ft = librosa.frames_to_time(np.arange(nT), sr=SR, hop_length=HOP)
    # time signature: accent periodicity of beat-level energy
    acc = np.interp(bt, ft, env["kick"] + env["snare"])
    def per(p): return np.mean([np.corrcoef(acc[:-p], acc[p:])[0, 1]]) if len(acc) > 2 * p else -1
    ts = "3/4" if per(3) > per(4) + 0.1 and per(3) > per(2) else "4/4"
    bpb = 3 if ts == "3/4" else 4
    # downbeat phase: which beat offset has the strongest kick
    w2 = int(0.04 * SR / HOP) + 1
    near = lambda e: np.array([e[max(0, i - w2): i + w2].max() for i in np.searchsorted(ft, bt).clip(0, nT - 1)])
    kb, sb = near(env["kick"]), near(env["snare"])
    # downbeat = beat with strong kick and weak snare (backbeat snare lands on 2 and 4)
    phase = int(np.argmax([kb[o::bpb].mean() - sb[o::bpb].mean() + (sb[o + 1::bpb].mean() if bpb == 4 else 0) for o in range(bpb)]))
    bt = bt[phase:]
    nbars = (len(bt) - 1) // bpb
    steps = bpb * 4
    grid = {k: np.zeros((nbars, steps)) for k in DRUMS}
    swing_off = []
    win = int(0.035 * SR / HOP) + 1
    for b in range(nbars):
        for q in range(bpb):
            t0, t1 = bt[b * bpb + q], bt[b * bpb + q + 1]
            for s in range(4):
                tt = t0 + (t1 - t0) * s / 4; i = int(np.searchsorted(ft, tt))
                for k in DRUMS:
                    grid[k][b, q * 4 + s] = env[k][max(0, i - win): i + win].max() if i < nT else 0
            # swing: where is the hat/snare peak around the off-beat 8th (50% = straight, 66% = triplet)
            lo, hi = np.searchsorted(ft, t0 + 0.35 * (t1 - t0)), np.searchsorted(ft, t0 + 0.8 * (t1 - t0))
            seg = env["hats"][lo:hi] + 0.5 * env["snare"][lo:hi]
            if hi > lo and seg.max() > 0.3: swing_off.append((ft[lo + int(np.argmax(seg))] - t0) / (t1 - t0))
    swing = float(np.median(swing_off)) * 100 if len(swing_off) > 8 else 50.0
    hits, pattern = {}, {}
    for k in DRUMS:
        g = grid[k]; thr = 0.3 if g.size else 1
        hits[k] = (g > thr).astype(int)
        frac = hits[k].mean(axis=0) if nbars else np.zeros(steps)
        pattern[k] = [i + 1 for i in range(steps) if frac[i] >= 0.5]
    # sections from bar energy
    rms = librosa.feature.rms(y=y, hop_length=HOP)[0]; rt = librosa.frames_to_time(np.arange(len(rms)), sr=SR, hop_length=HOP)
    be = np.array([20 * np.log10(rms[(rt >= bt[b * bpb]) & (rt < bt[(b + 1) * bpb])].mean() + 1e-9) for b in range(nbars)]) if nbars else np.array([])
    sections = []
    if nbars:
        sm = np.convolve(be, np.ones(2) / 2, "same"); top = np.percentile(sm, 80); bot = np.percentile(sm, 20)
        lvl = np.where(sm > top - 2, 2, np.where(sm < bot + 2, 0, 1))
        start = 0
        for b in range(1, nbars + 1):
            if b == nbars or lvl[b] != lvl[start]:
                if sections and b - start < 2: sections[-1]["end_bar"] = b
                else: sections.append({"start_bar": start + 1, "end_bar": b, "level": int(lvl[start])})
                start = b
        for i, s in enumerate(sections):
            nxt = sections[i + 1]["level"] if i + 1 < len(sections) else None
            s["label"] = ("intro" if i == 0 and s["level"] < 2 else "outro" if i == len(sections) - 1 and s["level"] < 2
                          else "drop/chorus" if s["level"] == 2 else "breakdown then build" if nxt == 2 and s["level"] == 0 else "build" if nxt == 2 else "breakdown/verse")
            s["start_s"] = round(float(bt[(s["start_bar"] - 1) * bpb]), 1)
    # palette
    P = np.abs(librosa.stft(y, hop_length=HOP)) ** 2; f = librosa.fft_frequencies(sr=SR)
    tot = P.sum() + 1e-20
    sub = float(P[(f >= 30) & (f < 70)].sum() / tot)
    H, Pp = librosa.decompose.hpss(P)
    harm = float(H.sum() / (H.sum() + Pp.sum() + 1e-20))
    cent = float(np.mean(librosa.feature.spectral_centroid(S=np.sqrt(P), sr=SR)))
    subenv = P[(f >= 30) & (f < 70)].sum(axis=0); sustain = float(np.mean(subenv > 0.3 * np.percentile(subenv, 95)))
    hon = librosa.onset.onset_detect(onset_envelope=librosa.onset.onset_strength(S=librosa.power_to_db(H), sr=SR), sr=SR, hop_length=HOP); dens = len(hon) / (len(y) / SR)
    palette = {"sub_share": round(sub, 3), "sub_sustain": round(sustain, 2), "harmonic_share": round(harm, 2),
               "brightness_hz": round(cent), "harmonic_onsets_per_s": round(dens, 2)}
    words = []
    if sub > 0.25 and sustain > 0.3: words.append("long 808/sub bass that rings under the beat")
    elif sub > 0.12: words.append("solid sub/kick low end")
    else: words.append("light low end")
    if harm > 0.7 and dens < 2.5: words.append("sustained pads/chords")
    if dens >= 2.5: words.append("plucky/rhythmic melodic parts (plucks, keys, arps)")
    words.append("bright, crisp top" if cent > 3000 else "warm/dark tone" if cent < 1700 else "balanced brightness")
    key, kconf = key_of(y)
    kit = ("Drum Machine Designer 808-style or trap kit (e.g. 'Trap Door' / 'Boutique 808')" if sub > 0.2
           else "a punchy electronic kit in Drum Machine Designer" if cent > 2500 else "an acoustic/Drummer kit or soft electronic kit")
    sw = "straight" if swing < 54 else "light swing" if swing < 60 else "heavy swing/triplet feel"
    fmt = lambda l: ", ".join(map(str, l)) if l else "none found"
    summary = [f"Tempo about {tempo:.0f} BPM, {ts}, {sw} (swing ~{swing:.0f}%); key guess {key} (confidence {kconf}).",
               f"Sound palette: {'; '.join(words)}.",
               f"Typical bar on a {steps}-step grid of 16ths (" + ", ".join(f"step {q*4+1} = beat {q+1}" for q in range(bpb)) + "):",
               f"  Kick: {fmt(pattern['kick'])}", f"  Snare/clap: {fmt(pattern['snare'])}", f"  Hats: {fmt(pattern['hats'])}",
               "Structure: " + (", ".join(f"{s['label']} bars {s['start_bar']}-{s['end_bar']}" for s in sections) or "too short"),
               f"GarageBand: set project tempo {tempo:.0f}, time signature {ts}, key {key.split()[0]}{'m' if 'minor' in key else ''}. "
               f"Make a Software Instrument drum kit track ({kit}), create an empty one-bar MIDI region (Control-click the track lane > "
               f"Create MIDI Region), turn Cycle on over it, and open the Piano Roll (E) with the grid set to 1/16. Draw kick, snare and hat notes on "
               f"the steps above (each step = one 1/16 grid cell), loop or copy the region, then change at least a few steps and the sounds so it's your own groove"
               + (f"; use the region's Quantize with swing (about {swing:.0f}%) for the shuffle." if swing >= 54 else "."),
               "Confidence: high on clean loops; on full dense mixes the drum steps and time signature are rough (no stem separation yet). Check with your ears.",
               "Borrow the feel, tempo, groove and palette only. Don't recreate the reference's melody, vocal hook or samples note-for-note."]
    # images
    fig, axs = plt.subplots(2, 1, figsize=(12, 6.5), gridspec_kw={"height_ratios": [1, 2]})
    tp = np.array([hits[k].mean(axis=0) if nbars else np.zeros(steps) for k in DRUMS])
    axs[0].imshow(tp, aspect="auto", cmap="Greens", vmin=0, vmax=1)
    for (r, c), v in np.ndenumerate(tp): axs[0].text(c, r, "X" if v >= 0.5 else "", ha="center", va="center", fontsize=12, weight="bold")
    axs[0].set_yticks(range(3)); axs[0].set_yticklabels(list(DRUMS)); axs[0].set_xticks(range(steps)); axs[0].set_xticklabels(range(1, steps + 1))
    for q in range(1, bpb): axs[0].axvline(q * 4 - 0.5, c="k", lw=1.5)
    axs[0].set_title(f"{label}: typical bar ({tempo:.0f} BPM, {ts}); X = hit in at least half the bars, shade = how often")
    nb = min(nbars, 16)
    rows = np.vstack([np.hstack([hits[k][b] * (i + 1) for k in []]) if False else np.concatenate([hits[k][b] * (i + 1) for i, k in enumerate(DRUMS)]) for b in range(nb)]) if nb else np.zeros((1, 3 * steps))
    axs[1].imshow(rows, aspect="auto", cmap=matplotlib.colors.ListedColormap(["white", "tab:red", "tab:blue", "tab:orange"]), vmin=0, vmax=3, interpolation="nearest")
    for i in range(1, 3): axs[1].axvline(i * steps - 0.5, c="k", lw=2)
    axs[1].set_xticks([steps / 2 - .5, 1.5 * steps - .5, 2.5 * steps - .5]); axs[1].set_xticklabels(["kick (red)", "snare (blue)", "hats (orange)"])
    axs[1].set_ylabel("bar"); axs[1].set_yticks(range(nb)); axs[1].set_yticklabels(range(1, nb + 1)); axs[1].set_title(f"First {nb} bars, 16 steps each per drum")
    fig.tight_layout(); fig.savefig(os.path.join(outdir, "drum_grid.png"), dpi=110); plt.close(fig)
    fig, ax = plt.subplots(figsize=(12, 3.5))
    if nbars:
        ax.plot(range(1, nbars + 1), be, c="k")
        cols = {"intro": "#cde", "build": "#fd9", "drop/chorus": "#f99", "breakdown/verse": "#cfc", "breakdown then build": "#bdf", "outro": "#ddd"}
        for s in sections:
            ax.axvspan(s["start_bar"] - 0.5, s["end_bar"] + 0.5, color=cols[s["label"]], alpha=.7)
            ax.text((s["start_bar"] + s["end_bar"]) / 2, be.max() + 0.5, s["label"], ha="center", fontsize=8)
    ax.set_xlabel("bar"); ax.set_ylabel("energy dB"); ax.set_title("Section structure by energy"); fig.subplots_adjust(top=0.85, bottom=0.18)
    fig.savefig(os.path.join(outdir, "structure.png"), dpi=110); plt.close(fig)
    out = {"source": label, "tempo_bpm": round(tempo, 1), "time_signature_guess": ts, "swing_pct": round(swing, 1), "key_guess": key,
           "key_confidence": kconf, "bars_analyzed": nbars, "pattern_16_steps": pattern, "per_bar_hits": {k: hits[k][:64].tolist() for k in DRUMS},
           "palette": palette, "palette_words": words, "sections": sections, "summary": summary,
           "images": {"drum_grid": os.path.join(outdir, "drum_grid.png"), "structure": os.path.join(outdir, "structure.png")},
           "method": "band-onset heuristics (no stem separation)"}
    json.dump(out, open(os.path.join(outdir, "beat_study.json"), "w"), indent=2)
    return out

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("reference"); ap.add_argument("--outdir", default="out/beat_study"); ap.add_argument("--max-seconds", type=float)
    a = ap.parse_args()
    tmp = tempfile.mkdtemp(prefix="beatstudy_")
    try:
        r = study(fetch_reference(a.reference, tmp), a.outdir, a.reference, a.max_seconds)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("\n".join(r["summary"])); print(STUDY_NOTE); print(f"\nJSON + images in {a.outdir}")
