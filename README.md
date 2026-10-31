# MusicMasteringUpdates

The official update source for the **Music Mastering for GarageBand** Grok Bot: it analyzes a finished mix and walks you click by click through mastering it in GarageBand, with an offline fallback you reimport.

## For owners
Updates are **automatic and always on**: once a week the bot checks this repo and, if there's a newer version, updates itself and sends you a short "Music Mastering updated to vN, here's what's new" note. This is built in and can't be switched off (you can move the time it runs).

## Safety promises
- The bot only accepts updates from this exact repo.
- Update files can never make Music Mastering run commands on your Mac, send messages, handle passwords or SSNs, or delete your data. Those abilities are **your settings**, chosen by you during setup, and each outgoing message still needs your yes.
- Your records are never overwritten. The bot takes a snapshot before every update and rolls back if anything fails.
- New optional features start off and are offered to you as a card.

Full component map: [PARITY.md](PARITY.md). Current version: [VERSION](VERSION). Changes: [CHANGELOG.md](CHANGELOG.md).
