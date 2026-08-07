# FiveM Server Lookup

Check out a FiveM server before you join it.

**→ [zuhmoon.github.io/fivem-lookup](https://zuhmoon.github.io/fivem-lookup/)**

Search any of ~34,000 listed servers by name, or browse with filters, and see what it
publishes about itself:

- who's online right now, with pings
- real player count vs. the number it advertises
- every resource it runs — framework, anticheat, whether it can screenshot your game
- how far behind its FXServer build is
- join code, IP, Discord, owner

Star servers as favorites, watch for a player name and get an alert when they come online,
move servers or disconnect, and build up a picture of a server's real peak hours.

All of it is public data the server broadcasts. No login, nothing installed.

## Terminal version

`fivem.py` does the same lookups from a terminal, and can track a server's population while
your browser is closed. Python 3, no dependencies.

```bash
python fivem.py krown              # search, pick from the list, full report
python fivem.py --players j4r9zmk  # who's online
python fivem.py --watch j4r9zmk    # sample every 5 min into history.db
python fivem.py --history j4r9zmk  # peak hours and trend
```

On Windows, double-click `fivem.bat` and it just asks for a name.

## Two things worth knowing

**"No anticheat name visible" does not mean unprotected.** Detection works off resource
names, and vendors tell operators to rename them so cheaters can't fingerprint them. In a
608-server sample, 61% showed no recognisable name — plenty of those are protected.

**Some servers hide their player list**, showing every player as `Player` with no ping. That's
a privacy setting, not fake population — the *count* is still accurate.

---

Setup, deployment and how it all works: [NOTES.md](NOTES.md)
