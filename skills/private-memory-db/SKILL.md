---
name: private-memory-db
description: >-
  Use at the start of every task and whenever you learn something durable: sets
  up and uses this bot's own private SQLite memory (brain.db plus the gbmem CLI)
  with an optional GitHub backup.
---
# Private memory database
Each owner gets their own empty, private memory on their bot's computer. Never copy another owner's data into it.
This bot keeps its memory in its own folder, `~/memory/gb/`, and its CLI is `gbmem`, so it never mixes with another bot's memory (for example DOGE's `~/memory/brain.db` and `mem`) on a shared computer.

## Setup (first run, if `~/memory/gb/brain.db` is missing)
1. `mkdir -p ~/memory/gb ~/bin`. Download https://raw.githubusercontent.com/EmpressHeavy/MusicMasteringUpdates/main/memory/mem.py to `~/memory/gb/mem` (or write the CLI below), `chmod +x` it, and symlink it to `~/bin/gbmem`.
2. Run `gbmem init`, then `gbmem log setup "memory created"`.

```python
#!/usr/bin/env python3
"""Private memory CLI for this bot (DOGE private-memory-db pattern). DB: $MEM_DB or ~/memory/gb/brain.db.
Own folder per bot so several bots on one computer never share memory. Never store passwords, PINs, tokens, or SSNs."""
import sqlite3,sys,os,datetime
DB=os.environ.get('MEM_DB',os.path.expanduser('~/memory/gb/brain.db'))
os.makedirs(os.path.dirname(DB),exist_ok=True)
c=sqlite3.connect(DB);c.execute('PRAGMA journal_mode=WAL')
now=datetime.datetime.now().isoformat(timespec='seconds')
a=sys.argv[1:] or ['help'];cmd=a[0]
if cmd=='init':
  c.executescript('''CREATE TABLE IF NOT EXISTS fact(id INTEGER PRIMARY KEY,subject TEXT,predicate TEXT,value TEXT,valid_from TEXT,valid_to TEXT);
CREATE TABLE IF NOT EXISTS rule(id INTEGER PRIMARY KEY,category TEXT,text TEXT,set_on TEXT,active INTEGER DEFAULT 1);
CREATE TABLE IF NOT EXISTS project(id INTEGER PRIMARY KEY,title TEXT,status TEXT,path TEXT,notes TEXT,updated TEXT);
CREATE TABLE IF NOT EXISTS log(id INTEGER PRIMARY KEY,ts TEXT,kind TEXT,text TEXT);''')
elif cmd=='fact':
  s,p,v=a[1:4]
  with c:
    c.execute('UPDATE fact SET valid_to=? WHERE subject=? AND predicate=? AND valid_to IS NULL',(now,s,p))
    c.execute('INSERT INTO fact(subject,predicate,value,valid_from) VALUES(?,?,?,?)',(s,p,v,now))
elif cmd=='rule':
  with c: c.execute('INSERT INTO rule(category,text,set_on) VALUES(?,?,?)',(a[1],a[2],now))
elif cmd=='project':
  with c: c.execute('INSERT INTO project(title,status,path,notes,updated) VALUES(?,?,?,?,?)',(a[1],a[2],a[3] if len(a)>3 else '',a[4] if len(a)>4 else '',now))
elif cmd=='log':
  with c: c.execute('INSERT INTO log(ts,kind,text) VALUES(?,?,?)',(now,a[1],a[2]))
elif cmd=='q':
  for r in c.execute(a[1]): print('|'.join(map(str,r)))
elif cmd=='boot':
  for t,q in [('RULES','SELECT category,text FROM rule WHERE active=1'),('FACTS','SELECT subject,predicate,value FROM fact WHERE valid_to IS NULL'),('PROJECTS',"SELECT id,title,status,path FROM project WHERE status!='done'"),('RECENT','SELECT ts,kind,text FROM log ORDER BY id DESC LIMIT 10')]:
    print('##',t)
    for r in c.execute(q): print('|'.join(map(str,r)))
elif cmd=='export':
  out=a[1] if len(a)>1 else os.path.expanduser('~/memory/gb/export')
  os.makedirs(out,exist_ok=True)
  with open(os.path.join(out,'dump.sql'),'w') as f:
    for line in c.iterdump(): f.write(line+'\n')
  print(os.path.join(out,'dump.sql'))
else: print('gbmem init|boot|fact S P V|rule CAT TEXT|project TITLE STATUS [PATH] [NOTES]|log KIND TEXT|q SQL|export [DIR]')
```

## Every task
- Start with `gbmem boot`, then `gbmem q` for anything specific.
- Write facts as they happen, not in batches: `gbmem fact`, `gbmem rule`, `gbmem project`, `gbmem log`. `gbmem fact` closes the old current value automatically, so rows are never deleted.
- To change a project's status, run a short `UPDATE project SET status=?,updated=? WHERE id=?` in python3 sqlite3, then `gbmem log`.
- Never store passwords, PINs, tokens, SSNs, or full card numbers. Write "in vault" or the last 4 digits only.

## Optional GitHub backup
Only if the owner chose the GitHub backup in setup (card 4) and GitHub is connected: use a **private** repo they own (the same `my-mastering-backup` repo in a `memory/` folder, or a second private repo). Export with `gbmem export <backup folder>/memory` (an `iterdump()` SQL dump, diffable), commit only the export, and push. Ask before the first push, and confirm the repo is private (`gh repo view <name> --json visibility`). Re-export after notable memory writes and at least weekly.
