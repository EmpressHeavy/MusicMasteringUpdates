"""Music Mastering for GarageBand self-updater (install-time + weekly backup).

Source: ONLY https://github.com/EmpressHeavy/MusicMasteringUpdates, branch main.
Replaces only files listed in the repo's MANIFEST.json (code + skill files) inside
/workspace/mastering. Never touches gb.db, ~/memory/gb/brain.db, backup/, in/, shots/,
plan.json, pre.json, settings.json or anything not in the manifest.
Snapshot first, verify (py_compile + analyzer import), roll back on any failure.
New optional settings are never enabled: only missing keys are added, set OFF.

Usage: python3 tools/updater.py [--home DIR] [--test-source file:///path]
Always exits 0 and prints one JSON line:
  {"status": "updated|current|error", "version": "...", "skill_files_changed": [...]}
"""
import json, os, py_compile, re, shutil, subprocess, sys, tempfile, time

REPO_URL = "https://github.com/EmpressHeavy/MusicMasteringUpdates"
BRANCH = "main"
DEFAULT_HOME = "/workspace/mastering"
LOCAL_DEFAULT_VERSION = "2"
PROTECTED = {"gb.db", "backup", "in", "shots", "snapshots", "plan.json", "pre.json",
             "settings.json", "VERSION", "brain.db"}
FALLBACK_MANIFEST = {
    "analysis/analyze.py": "tools/analyze.py",
    "analysis/genre_presets.py": "tools/genre_presets.py",
    "analysis/make_test_signal.py": "tools/make_test_signal.py",
    "garageband/gb_control.py": "tools/gb_control.py",
    "garageband/ui_scripts.applescript": "tools/ui_scripts.applescript",
    "records/gb_db.py": "gb_db.py",
    "skills/mastering-session/SKILL.md": "skills/mastering-session/SKILL.md",
    "skills/mastering-getting-started/SKILL.md": "skills/mastering-getting-started/SKILL.md",
    "skills/music-distribution/SKILL.md": "skills/music-distribution/SKILL.md",
    "skills/hive-mind/SKILL.md": "skills/hive-mind/SKILL.md",
    "skills/private-memory-db/SKILL.md": "skills/private-memory-db/SKILL.md",
}


def parse_version(s):
    m = re.match(r"^v?(\d+(?:\.\d+){0,3})$", (s or "").strip())
    if not m:
        raise ValueError("bad version: %r" % s)
    return tuple(int(x) for x in m.group(1).split("."))


def is_newer(remote, local):
    r, l = parse_version(remote), parse_version(local)
    n = max(len(r), len(l))
    return r + (0,) * (n - len(r)) > l + (0,) * (n - len(l))


def local_version(home):
    p = os.path.join(home, "VERSION")
    if not os.path.exists(p):
        with open(p, "w") as f:
            f.write(LOCAL_DEFAULT_VERSION + "\n")
    return open(p).read().strip()


def safe_rel(rel):
    p = os.path.normpath(rel)
    if p.startswith("..") or os.path.isabs(p):
        raise ValueError("unsafe path: %s" % rel)
    if p.split(os.sep)[0] in PROTECTED or p.endswith((".db", ".db-wal", ".db-shm")):
        raise ValueError("protected path in manifest: %s" % rel)
    return p


def fetch(source, dest):
    if source != REPO_URL and not source.startswith("file://"):
        raise ValueError("refusing non-official source")
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0")
    subprocess.run(["git", "clone", "-q", "--depth", "1", "--branch", BRANCH, source, dest],
                   check=True, capture_output=True, timeout=120, env=env)
    for root, dirs, files in os.walk(dest):
        for n in dirs + files:
            if os.path.islink(os.path.join(root, n)):
                raise ValueError("symlink in update")


def import_ok(home):
    r = subprocess.run([sys.executable, "-c", "import sys; sys.path.insert(0,'tools'); sys.path.insert(0,'.'); import analyze, genre_presets, gb_db"],
                       cwd=home, capture_output=True, text=True, timeout=60)
    if r.returncode == 0:
        return "ok"
    last = (r.stderr.strip().splitlines() or [""])[-1]
    m = re.match(r"ModuleNotFoundError: No module named '([\w.]+)'", last)
    if m and m.group(1).split(".")[0] not in ("analyze", "genre_presets", "gb_db"):
        return "missing_dep"  # third-party lib not installed on this box: not caused by the update
    return "fail:" + last[-200:]


def verify(home, rels, baseline):
    for rel in rels:
        if rel.endswith(".py"):
            py_compile.compile(os.path.join(home, rel), doraise=True)
    now = import_ok(home)
    if now.startswith("fail") or (baseline == "ok" and now != "ok"):
        raise RuntimeError("import check: " + now)


def run(home=DEFAULT_HOME, source=REPO_URL):
    out = {"status": "error", "version": "", "skill_files_changed": []}
    snap = None
    changed = []
    tmp = tempfile.mkdtemp(prefix="mm-update-")
    try:
        cur = local_version(home)
        out["version"] = cur
        src = os.path.join(tmp, "repo")
        fetch(source, src)
        remote = open(os.path.join(src, "VERSION")).read().strip()
        if not is_newer(remote, cur):
            out["status"] = "current"
            return out
        mpath = os.path.join(src, "MANIFEST.json")
        manifest = json.load(open(mpath)) if os.path.exists(mpath) else {"files": FALLBACK_MANIFEST}
        files = {r: safe_rel(l) for r, l in manifest["files"].items()}
        for r in files:
            safe_rel(r)
        baseline = import_ok(home)
        # snapshot every manifest target + VERSION + settings files (as they exist now)
        snap = os.path.join(home, "snapshots", time.strftime("%Y%m%d-%H%M%S") + "-v" + cur)
        existed = []
        for l in list(files.values()) + ["VERSION", "settings.json"]:
            p = os.path.join(home, l)
            if os.path.isfile(p):
                os.makedirs(os.path.dirname(os.path.join(snap, l)), exist_ok=True)
                shutil.copy2(p, os.path.join(snap, l))
                existed.append(l)
        json.dump({"from": cur, "to": remote, "existed": existed, "targets": list(files.values())},
                  open(os.path.join(snap, "_snapshot.json"), "w"))
        for r, l in files.items():
            s, d = os.path.join(src, r), os.path.join(home, l)
            if not os.path.isfile(s):
                continue
            if os.path.isfile(d) and open(s, "rb").read() == open(d, "rb").read():
                continue
            os.makedirs(os.path.dirname(d), exist_ok=True)
            shutil.copy2(s, d + ".new")
            os.replace(d + ".new", d)
            changed.append(l)
        new_settings = manifest.get("settings") or {}
        if new_settings:
            sp = os.path.join(home, "settings.json")
            cfg = json.load(open(sp)) if os.path.exists(sp) else {}
            for k in new_settings:
                cfg.setdefault(k, False)  # never enable; keep existing values
            json.dump(cfg, open(sp, "w"), indent=2)
        verify(home, changed, baseline)
        with open(os.path.join(home, "VERSION"), "w") as f:
            f.write(remote + "\n")
        out.update(status="updated", version=remote,
                   skill_files_changed=[c for c in changed if c.startswith("skills/")])
        return out
    except Exception as e:
        if snap and os.path.isdir(snap):
            try:
                meta = json.load(open(os.path.join(snap, "_snapshot.json")))
                for l in set(meta["targets"] + ["VERSION", "settings.json"]):
                    p = os.path.join(home, l)
                    if l in meta["existed"]:
                        shutil.copy2(os.path.join(snap, l), p)
                    elif os.path.exists(p):
                        os.remove(p)  # file was added by the failed update
            except Exception:
                pass
        out["status"] = "error"
        out["skill_files_changed"] = []
        out["error"] = str(e)[:200]
        return out
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main(argv):
    home, source = DEFAULT_HOME, REPO_URL
    if "--home" in argv:
        home = argv[argv.index("--home") + 1]
    if "--test-source" in argv:
        source = argv[argv.index("--test-source") + 1]
    try:
        res = run(home, source)
    except Exception as e:
        res = {"status": "error", "version": "", "skill_files_changed": [], "error": str(e)[:200]}
    print(json.dumps(res))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
