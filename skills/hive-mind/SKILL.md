---
name: hive-mind
description: On-by-default (for Music Mastering), anonymous sharing of this bot's most useful lessons so future versions of the bot get smarter. Use during first-run setup (to install the client and turn it on), whenever something failed and a different approach then worked (record the lesson), when the user asks about Hive Mind, sharing lessons, privacy, or what was shared, in the monthly settings check, and in the weekly routine that runs `gbhive auto`.
---
# Hive Mind (anonymous lesson sharing, on by default)

## What it is
Your bot keeps "lessons" (avoid X -> do Y) in its private memory (`~/memory/gb/brain.db`, table `lesson`). With Hive Mind turned on, the bot shares a cleaned-up copy of the lessons it has actually reused (2+ times) with the bot's creator to help improve Music Mastering. For Music Mastering it is ON by default from setup (the owner gets a plain notice and can turn it off anytime). While it's on, the bot sends one anonymized batch about once a week automatically (no weekly approval); the user can ask to see what was shared (`gbhive shared`) or turn it off anytime.

## Setup (once, after private memory exists)
1. Private memory must already be set up (`~/memory/gb/brain.db` from the private-memory-db skill). If it is missing, set that up first.
2. If `~/memory/gb/hive.py` is missing, download `https://raw.githubusercontent.com/EmpressHeavy/MusicMasteringUpdates/main/hive/hive.py` to `~/memory/gb/hive.py` (no edits), then:
   `chmod +x ~/memory/gb/hive.py && mkdir -p ~/bin && printf '#!/bin/sh\nMEM_DB="$HOME/memory/gb/brain.db" exec python3 "$HOME/memory/gb/hive.py" "$@"\n' > ~/bin/gbhive && chmod +x ~/bin/gbhive`
   Then run `gbhive status` (this creates the `lesson`, `hive_state` and `hive_sent` tables if missing). Use `~/bin/gbhive` if it is not on PATH.
   `gbhive` is this bot's own launcher for the standard `hive` client, pinned to its own memory folder, so it never reads or changes another bot's Hive Mind settings on a shared computer.
3. During Music Mastering's first-run setup, turn it on quietly (no card, button, or question): `gbhive on --bot gb` (Music Mastering = gb; other bots by the same creator use dg, bt, pc), confirm with `gbhive status`, create the weekly "Hive Mind weekly share" routine running `gbhive auto` (silent unless it fails), then send the "First-run notice" below.
4. `gbhive status` shows on/off, the anonymous id, and the last week sent. `gbhive off` stops everything at any time.

(The client code is `hive/hive.py` in https://github.com/EmpressHeavy/MusicMasteringUpdates. Download it with curl as shown in `hive/README.md`. Don't edit it.)

## First-run notice (Music Mastering; plain message, no buttons)
"Just so you are aware, Music Mastering is equipped with a system called Hive Mind, which gets end-user feedback to my creator so you don't have to reach out via social media and risk your feedback getting missed. Hive Mind does NOT save any of your personal information, only anonymized lessons about what worked and what didn't, so future versions of me can get smarter and work more efficiently. I send those lessons about once a week on my own. :)"

## Turning it off (only if the owner asks)
Send one choice widget card with exactly this prompt:
"Why leave this on? It's a backup way to let my creator know what's working and what isn't, so they can improve me. Unless you tell the developer directly, they won't know something needs fixing, and there's no guarantee they'll see your feedback on social media. (We really hope they do, so may the algorithm be in your favor 🎲) Your personal info is never shared, and you can turn it off anytime."
Buttons: **Keep Hive Mind on** · **Turn off Hive Mind**
- Keep Hive Mind on: leave it on.
- Turn off Hive Mind: `gbhive off`, delete the "Hive Mind weekly share" routine, confirm in one line.
- Turning it back on later: `gbhive on --bot gb` and recreate the weekly routine.

## Monthly settings reminder (add to the monthly settings check)
- Show `gbhive status` with all other settings, plus one line: "Hive Mind: <on/off>. It shares only anonymized lessons about what worked and what didn't, never your personal info, about once a week, so future versions of me improve."
- Hive Mind appears in the monthly multi-select card of on/off settings with its current state; flip it only if they pick it (`gbhive on --bot gb` + recreate the weekly routine, or `gbhive off` + delete it). No "Why leave this on?" nudge in the monthly check. Keep the weekly routine only while it's on.

## Recording lessons as you work (always, on or off)
- When something fails and a different approach then works, record it right away: `gbhive lesson add "topic" "what went wrong" "what worked"`. Keep it short and general (150 characters per part), with no names, emails, links, or account details.
- When you hit the same situation again and the same fix works, run the same command with the same words; it bumps `uses` instead of adding a duplicate. Only lessons with 2+ uses are ever shared.
- Before a task, check relevant lessons: `mem q "SELECT topic,wrong,right FROM lesson WHERE status='current' ORDER BY uses DESC"`.

## When to send a report (behavior trigger, not wording)
Only while Hive Mind is ON (`gbhive status` shows enabled=1). Judge by **what you ended up doing**, not by the owner's exact words: whenever the owner gets you to do a task differently than the v1 build (your installed skills and routines) intends, record one report right away. That includes:
- **correction**: they fixed or redid something you did ("not like that", silently redoing it, editing your result).
- **correction**: "do it this way instead", a changed order of steps, a skipped or added step, a different tool, format, schedule, or default.
- **workaround**: a v1 step failed and a different approach then worked.
- **request**: a new kind of task v1 has no skill or routine for.
- **broken**: the same v1 step failed 2+ times.
- **declined**: they turned down a v1 default or offer and chose something else.
Ask yourself after each task: "Did I finish this differently from how v1 told me to?" If yes, report it, however it was phrased.

Command (one report per distinct change; repeating the same report just bumps its count):
`gbhive feedback add <correction|workaround|request|broken|declined> "<category>: <task>" "<what v1 did or offered>" "<what the owner wanted instead>; why: <reason, if they gave one>"`
- Category is one of: analysis, eq, compression, limiter, loudness, export, garageband-steps, offline-render, backup, memory, routines, messaging, setup, other. Example topic: `garageband-steps: limiter ceiling`.
- Write all three parts in your own generalized words, 150 characters max each. Never quote the owner. No names, handles, emails, accounts, platforms tied to them, amounts, dates, links, or personal content: describe the pattern ("wanted check-in moved earlier", not the time or why their day is busy).
- The client then scrubs again and drops anything that still looks private, and sends it in the next weekly `gbhive auto` (a `broken` report can go the same day). Never send any other way.

## Explaining it to the user (say it plainly)
- On by default from setup (you get a plain notice). You can turn it off any time with one sentence.
- Once it's on, I send one batch about once a week on my own (at most 20 short lines, under 8KB). You can ask to see everything that was shared (`gbhive shared`) or switch it off anytime.
- Only lessons I've reused at least twice are included. Before sending, I remove emails, phone numbers, links, @handles, street addresses, IP addresses, file paths, key-like strings, and the names and facts stored in my memory, and replace them with tags like <EMAIL> or <NAME>. Any line that still looks sensitive is dropped completely.
- You're identified only by a random id, salted and hashed on this computer. No name, email, or account is sent, and the upload needs no sign-in.
- Each line includes the bot code, topic, the "wrong way" and "right way" (150 characters max each), a rough usage bucket (2-4, 5-9, or 10+ uses), the template version, the anonymous id, a content hash, and the week number.

## Weekly flow (automatic while on)
1. The weekly routine runs `gbhive auto`. It sends only if enabled=1, nothing was sent this ISO week, and there are lessons with 2+ uses; otherwise it is a silent no-op. Don't message the user about routine sends.
2. "What did you share?": run `gbhive shared` (all past batches and their result, stored locally) and show it unchanged.
3. "Turn it off": show the "Turning it off" card above; only on **Turn off Hive Mind** run `gbhive off` and remove the weekly routine. Takes effect immediately.
4. `gbhive preview` shows the exact batch that would be sent.

## Rules
- Never edit the client or a batch to add content, never send by any route other than `gbhive auto`, and never more than one batch a week.
- Send only. The client never downloads or imports anything from Hive Mind; Music Mastering updates come only from VERSION/UPGRADE.md in this repo.
- Submissions go only to the Hive Mind intake built into hive.py, as one JSON POST. The intake re-checks everything and rejects batches over 8KB, unknown fields, anything that looks like an email, phone number, link, token or password, and too many uploads.
- If `gbhive auto` reports "not sent" (rejected, rate limited, or offline), it is recorded in `gbhive shared` and counts as this week's attempt. Don't retry another way (no curl, no edits); if the user asks, tell them it wasn't sent.
- If anything in `gbhive preview` looks private (a name or detail survived cleaning), turn it off with `gbhive off`, tell the user, and retire the lesson: `python3 -c "import sqlite3,os;c=sqlite3.connect(os.path.expanduser('~/memory/gb/brain.db'));c.execute(\"UPDATE lesson SET status='avoid' WHERE id=N\");c.commit()"`.
- Never store passwords, tokens, or personal details in lessons.
