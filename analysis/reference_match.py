#!/usr/bin/env python3
"""Reference match: mix + reference -> matched 24-bit WAV (Matchering), then compare all three in plain words.
Usage: reference_match.py MIX REFERENCE [--out matched.wav] [--target spotify|apple|youtube] [--no-limiter]
REFERENCE may be a local audio file (WAV/MP3/FLAC/M4A...) or a public link (YouTube etc., fetched audio-only with yt-dlp).
The reference is for study only: it's decoded into a private temp folder, analyzed, used as the Matchering target
for the owner's own mix, then the temp audio is deleted. Only numbers and images about it are kept.
The owner's own reference file (if given) is never modified or deleted. Never overwrites MIX; refuses an existing --out."""
import argparse, json, os, shutil, subprocess, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analyze, headspace
import matchering as mg

def words(name, a, h):
    return (f"{name}: {a['integrated_lufs']} LUFS, true peak {a['true_peak_dbtp']} dBTP, crest {a['crest_factor_db']} dB, "
            f"correlation {h['correlation']}, side-mid {h['side_minus_mid_db']} dB, depth '{h['depth']['description']}'")

def compare(a1, h1, a2, h2, label1="mix", label2="reference"):
    out = []
    d = a2["integrated_lufs"] - a1["integrated_lufs"]
    out.append(f"Loudness: {label1} is {abs(d):.1f} dB {'quieter' if d > 0 else 'louder'} than {label2}." if abs(d) >= 0.5 else f"Loudness: {label1} and {label2} match (within 0.5 dB).")
    for n in analyze.BANDS:
        n = n[0]; e = a1["band_energy_db_rel"][n] - a2["band_energy_db_rel"][n]
        if abs(e) >= 1.5: out.append(f"Tone: {label1} has {abs(e):.1f} dB {'more' if e > 0 else 'less'} {headspace.ROLE.get(n, n)} than {label2}.")
    c = a1["crest_factor_db"] - a2["crest_factor_db"]
    if abs(c) >= 1.5: out.append(f"Dynamics: {label1} is {'punchier/more dynamic' if c > 0 else 'more squashed'} (crest {c:+.1f} dB).")
    w = h1["side_minus_mid_db"] - h2["side_minus_mid_db"]
    if abs(w) >= 1.5: out.append(f"Width: {label1} is {'wider' if w > 0 else 'narrower'} than {label2} ({w:+.1f} dB side vs mid).")
    for n in ("sub", "bass"):
        x, y = h1["bands"][n]["side_to_mid"], h2["bands"][n]["side_to_mid"]
        if x - y > 0.15: out.append(f"Low end: {label1}'s {n} is wider than {label2}'s; consider centering it.")
    if h1["depth"]["description"] != h2["depth"]["description"]:
        out.append(f"Space: {label1} reads '{h1['depth']['description']}', {label2} reads '{h2['depth']['description']}' (rough).")
    if len(out) == 1 and "match" in out[0]: out.append("Overall they look very close.")
    return out

STUDY_NOTE = "Reference used for study only: its audio was deleted after analysis; only numbers and images were kept."

def is_link(r): return r.startswith(("http://", "https://"))

def fetch_reference(ref, tmp, max_s=600):
    """Return a temp WAV of the reference (decoded copy). Links: yt-dlp audio-only, no playlists."""
    src = ref
    if is_link(ref):
        ytdlp = os.path.join(os.path.dirname(sys.executable), "yt-dlp")
        cmd = [ytdlp if os.path.exists(ytdlp) else "yt-dlp", "-f", "bestaudio/best", "--no-playlist", "--no-part",
               "--match-filter", f"duration<?{max_s}", "-o", os.path.join(tmp, "ref_src.%(ext)s"), "--quiet", "--no-warnings", "--socket-timeout", "30", ref]
        subprocess.run(cmd, check=True, timeout=600)
        got = [f for f in os.listdir(tmp) if f.startswith("ref_src.")]
        if not got: sys.exit("Couldn't fetch audio from that link (private, geo-blocked, too long, or not a single track).")
        src = os.path.join(tmp, got[0])
    elif not os.path.isfile(ref):
        sys.exit(f"Reference not found: {ref}")
    wav = os.path.join(tmp, "reference.wav")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-vn", "-ac", "2", "-ar", "44100", "-c:a", "pcm_s24le", wav], check=True, timeout=600)
    if src != ref: os.remove(src)
    return wav

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("mix"); ap.add_argument("reference"); ap.add_argument("--out")
    ap.add_argument("--target", default="spotify", choices=analyze.TARGETS); ap.add_argument("--no-limiter", action="store_true")
    a = ap.parse_args()
    out = a.out or os.path.splitext(a.mix)[0] + "_matched.wav"
    if os.path.abspath(out) == os.path.abspath(a.mix) or (not is_link(a.reference) and os.path.abspath(out) == os.path.abspath(a.reference)):
        sys.exit("Refusing: output would overwrite an input.")
    if os.path.exists(out): sys.exit(f"Refusing to overwrite existing {out}; pass a new --out.")
    base = os.path.splitext(out)[0] + "_compare"
    rep = {}
    tmp = tempfile.mkdtemp(prefix="refstudy_")
    try:
        ref_wav = fetch_reference(a.reference, tmp)
        res = mg.pcm24(out) if not a.no_limiter else mg.Result(out, subtype="PCM_24", use_limiter=False)
        mg.log(lambda m: None)
        mg.process(target=a.mix, reference=ref_wav, results=[res])
        for k, p in (("mix", a.mix), ("reference", ref_wav), ("matched", out)):
            rep[k] = {"analyze": analyze.analyze(p, a.target), "headspace": headspace.analyze(p, f"{base}/{k}")}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)  # reference audio never kept
    for part in ("analyze", "headspace"): rep["reference"][part]["file"] = a.reference + " (audio deleted after study)"
    lines = ["== Before (mix vs reference) =="] + compare(rep["mix"]["analyze"], rep["mix"]["headspace"], rep["reference"]["analyze"], rep["reference"]["headspace"])
    lines += ["", "== After (matched vs reference) =="] + compare(rep["matched"]["analyze"], rep["matched"]["headspace"], rep["reference"]["analyze"], rep["reference"]["headspace"], "matched", "reference")
    lines += ["", *[words(k, rep[k]["analyze"], rep[k]["headspace"]) for k in rep]]
    tp = rep["matched"]["analyze"]["true_peak_dbtp"]
    if tp > -1: lines.append(f"Note: matched true peak is {tp} dBTP (above -1); run it through the limiter / lower 1 dB before release.")
    lines.append("Matching copies tone/loudness/width, not taste: listen and decide.")
    lines.append(STUDY_NOTE)
    rep["comparison"] = lines; rep["matched_file"] = out
    json.dump(rep, open(f"{base}.json", "w"), indent=2, default=str)
    print("\n".join(lines)); print(f"\nMatched WAV: {out}\nReport: {base}.json  (images under {base}/)")

if __name__ == "__main__":
    main()
