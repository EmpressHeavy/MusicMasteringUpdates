#!/usr/bin/env python3
"""Music Mastering records store (DOGE doge_db.py pattern, generic, data-free).
DB: $GB_DB or /workspace/mastering/gb.db; backup dir: $GB_BACKUP or ./backup next to the DB.
Subcommands: init | add-session | add-track-analysis | add-settings-applied | set-pref | history | export-csv | export-all DIR | restore DIR | backup
Every write auto-backs up (CSV + DB copy; git commit+push when the backup dir is a git repo with a remote). restore is additive.
Never stores audio files; only analysis numbers, settings, and preferences."""
import argparse, csv, json, os, sqlite3, sys, datetime, shutil, subprocess
DB = os.environ.get("GB_DB", "/workspace/mastering/gb.db")
BK = os.environ.get("GB_BACKUP", os.path.join(os.path.dirname(os.path.abspath(DB)), "backup"))
SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions(id INTEGER PRIMARY KEY, started_at TEXT, project TEXT, platform_target TEXT, notes TEXT);
CREATE TABLE IF NOT EXISTS tracks(id INTEGER PRIMARY KEY, session_id INTEGER REFERENCES sessions(id), title TEXT, file_path TEXT, version TEXT, created_at TEXT);
CREATE TABLE IF NOT EXISTS analyses(id INTEGER PRIMARY KEY, track_id INTEGER REFERENCES tracks(id), stage TEXT CHECK(stage IN ('pre','post')),
  integrated_lufs REAL, true_peak_dbtp REAL, sample_peak_dbfs REAL, crest_factor_db REAL, lra_lu REAL, clipped_samples INTEGER,
  stereo_correlation REAL, band_energy_json TEXT, raw_json TEXT, created_at TEXT);
CREATE TABLE IF NOT EXISTS settings(id INTEGER PRIMARY KEY, track_id INTEGER REFERENCES tracks(id), plugin TEXT, params_json TEXT,
  applied_by TEXT CHECK(applied_by IN ('owner','bot_ui_script','offline_render')), reason TEXT, created_at TEXT);
CREATE TABLE IF NOT EXISTS owner_prefs(key TEXT PRIMARY KEY, value TEXT, updated_at TEXT);
CREATE TABLE IF NOT EXISTS meta(k TEXT PRIMARY KEY, v TEXT);
INSERT OR IGNORE INTO meta VALUES('schema_version','1');
"""
now = lambda: datetime.datetime.now().isoformat(timespec="seconds")
def con():
    os.makedirs(os.path.dirname(os.path.abspath(DB)), exist_ok=True)
    c = sqlite3.connect(DB); c.executescript(SCHEMA); return c
def ins(c, sql, args):
    cur = c.execute(sql, args); c.commit(); print(cur.lastrowid); after_write()
TABLES = ("sessions", "tracks", "analyses", "settings", "owner_prefs", "meta")
def export_all(out):
    os.makedirs(out, exist_ok=True); c = sqlite3.connect(DB)
    for t in TABLES:
        cur = c.execute(f"SELECT * FROM {t}")
        with open(os.path.join(out, f"{t}.csv"), "w", newline="") as f:
            w = csv.writer(f); w.writerow([d[0] for d in cur.description]); w.writerows(cur)
    c.close(); return out
def after_write(msg="auto: write"):
    export_all(BK); shutil.copy2(DB, os.path.join(BK, "gb.db"))
    if not os.path.isdir(os.path.join(BK, ".git")): return
    g = lambda *a: subprocess.run(["git", "-C", BK, *a], capture_output=True, text=True)
    if not g("remote").stdout.strip(): return
    g("add", "-A")
    if g("diff", "--cached", "--quiet").returncode == 0: return
    g("commit", "-m", msg)
    for _ in range(3):
        r = g("push", "origin", "HEAD")
        if r.returncode == 0: print("backup pushed"); return
    print("WARNING: backup push failed (tell the owner): " + r.stderr.strip(), file=sys.stderr)
def restore(d):
    """Additive: adds rows from <dir>/<table>.csv not already present. Never deletes or overwrites."""
    c = con(); n = {}
    for t in TABLES:
        f = os.path.join(d, f"{t}.csv")
        if not os.path.exists(f): continue
        with open(f, newline="") as fh:
            r = csv.reader(fh); h = next(r, None); rows = [[v if v != "" else None for v in x] for x in r]
        if not h: continue
        before = c.total_changes
        c.executemany(f"INSERT OR IGNORE INTO {t}({','.join(h)}) VALUES({','.join('?' * len(h))})", rows); n[t] = c.total_changes - before
    c.commit(); print("restored (added, existing kept):", n)

def main():
    ap = argparse.ArgumentParser(); s = ap.add_subparsers(dest="cmd", required=True)
    s.add_parser("init")
    p = s.add_parser("add-session"); p.add_argument("--project", required=True); p.add_argument("--target", default="spotify"); p.add_argument("--notes", default="")
    p = s.add_parser("add-track-analysis"); p.add_argument("--session", type=int, required=True); p.add_argument("--title", required=True)
    p.add_argument("--json", required=True, help="analyzer output file"); p.add_argument("--stage", default="pre", choices=["pre", "post"]); p.add_argument("--track", type=int)
    p = s.add_parser("add-settings-applied"); p.add_argument("--track", type=int, required=True); p.add_argument("--plugin", required=True)
    p.add_argument("--params", default="{}"); p.add_argument("--by", default="owner", choices=["owner", "bot_ui_script", "offline_render"]); p.add_argument("--reason", default="")
    p = s.add_parser("set-pref"); p.add_argument("key"); p.add_argument("value")
    p = s.add_parser("history"); p.add_argument("--limit", type=int, default=20)
    p = s.add_parser("export-csv"); p.add_argument("--table", default="analyses"); p.add_argument("--out", default="-")
    p = s.add_parser("export-all"); p.add_argument("dir")
    p = s.add_parser("restore"); p.add_argument("dir")
    s.add_parser("backup")
    a = ap.parse_args(); c = con()
    if a.cmd == "init": print(f"initialized {DB}")
    elif a.cmd == "add-session": ins(c, "INSERT INTO sessions(started_at,project,platform_target,notes) VALUES(?,?,?,?)", (now(), a.project, a.target, a.notes))
    elif a.cmd == "add-track-analysis":
        m = json.load(open(a.json)); tid = a.track
        if not tid:
            tid = c.execute("INSERT INTO tracks(session_id,title,file_path,created_at) VALUES(?,?,?,?)", (a.session, a.title, m.get("file"), now())).lastrowid
        ins(c, """INSERT INTO analyses(track_id,stage,integrated_lufs,true_peak_dbtp,sample_peak_dbfs,crest_factor_db,lra_lu,clipped_samples,
            stereo_correlation,band_energy_json,raw_json,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
            (tid, a.stage, m["integrated_lufs"], m["true_peak_dbtp"], m["sample_peak_dbfs"], m["crest_factor_db"], m["lra_lu"],
             m["clipped_samples"], m["stereo_correlation"], json.dumps(m["band_energy_db_rel"]), json.dumps(m), now()))
    elif a.cmd == "add-settings-applied":
        json.loads(a.params); ins(c, "INSERT INTO settings(track_id,plugin,params_json,applied_by,reason,created_at) VALUES(?,?,?,?,?,?)", (a.track, a.plugin, a.params, a.by, a.reason, now()))
    elif a.cmd == "set-pref":
        c.execute("INSERT OR REPLACE INTO owner_prefs VALUES(?,?,?)", (a.key, a.value, now())); c.commit(); after_write(); print("ok")
    elif a.cmd == "history":
        for r in c.execute("""SELECT s.id,s.project,t.id,t.title,an.stage,an.integrated_lufs,an.true_peak_dbtp,an.created_at FROM analyses an
            JOIN tracks t ON t.id=an.track_id JOIN sessions s ON s.id=t.session_id ORDER BY an.id DESC LIMIT ?""", (a.limit,)):
            print("session %s %s | track %s %s | %s LUFS %s dBTP %s @ %s" % (r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7]))
    elif a.cmd == "export-all": print(export_all(a.dir))
    elif a.cmd == "restore": restore(a.dir)
    elif a.cmd == "backup": after_write("manual backup"); print("backed up to", BK)
    elif a.cmd == "export-csv":
        if a.table not in TABLES: sys.exit("bad table")
        cur = c.execute(f"SELECT * FROM {a.table}"); f = sys.stdout if a.out == "-" else open(a.out, "w", newline="")
        w = csv.writer(f); w.writerow([d[0] for d in cur.description]); w.writerows(cur)
if __name__ == "__main__": main()
