# FiveM Server Lookup

Look up any FiveM server by name and see what it publishes about itself before you join:
join code, endpoint, real vs self-reported population, FXServer build age, framework,
resource list, and whether it can screenshot your game.

All public data. No login, no backend.

## Setting it up on GitHub

`index.html` is the whole site — one file, no build step, no dependencies, no npm.

### Step 1 — put it on GitHub Pages

```bash
git init
git add .                    # .gitignore already excludes the 20MB cache and local data
git commit -m "FiveM server lookup"
git branch -M main
git remote add origin https://github.com/<you>/<repo>.git
git push -u origin main
```

Then on github.com: **Settings → Pages → Source: _Deploy from a branch_ → `main` / `/ (root)` → Save.**
It's live at `https://<you>.github.io/<repo>/` in about a minute.

At this point search, filters, browsing, favorites, icons, deep links, CSV and history all
work. Players, resources, the anticheat filter and name-watching will be intermittent —
that's step 2.

### Step 2 — deploy the proxy (this is what makes everything work)

Cfx serves the server list with `Access-Control-Allow-Origin: *`, but **not** `single/<code>`,
which is the only source of resource lists and player lists. Without a proxy, a browser can't
read it — the page degrades gracefully and tells you so, but those features come and go.

`worker.js` fixes it in about two minutes and costs nothing:

1. Sign up at [workers.cloudflare.com](https://workers.cloudflare.com) (free tier: 100,000
   requests/day — a full 60-server anticheat scan is 60).
2. **Create application → Create Worker**, give it a name, **Deploy**.
3. **Edit code**, delete the placeholder, paste all of `worker.js`, **Deploy** again.
4. Copy its URL, e.g. `https://fivem-proxy.yourname.workers.dev`.
5. In `index.html`, set the constant near the top of the `<script>`:

   ```js
   const PROXY = "https://fivem-proxy.yourname.workers.dev";
   ```

6. `git commit -am "point at worker" && git push` — Pages redeploys in about a minute.

To confirm it worked: open any busy server; you should get a resource count and a player
list instead of the "players & resources unavailable" message.

### Do I need to do it differently?

No — a static host is the right call. There's no server-side code, no database, and no
secrets in the page, so GitHub Pages does the whole job. The only thing it can't do is add a
CORS header to somebody else's API, which is precisely and only what the worker does.

Two things that genuinely can't work in a browser at all, on any host:

- **Direct queries to a game server** (`http://<ip>:30120/players.json`) — game servers send
  no CORS header, and an HTTPS page can't make plaintext HTTP requests anyway. The CLI does
  this fine; a website never will.
- **Collecting history while the tab is closed.** Use `fivem.py --watch` for that.

### Running it locally

Any static server; the file has no build step.

```bash
python -m http.server 8765
```

The master list is a ~20 MB download on each page load. Everything in the top half of the
detail panel comes out of it, so clicking a server is instant with no second request.

Players, resources, server vars and history each open in a filterable popup — type to narrow
a 300-player list down to the name you're looking for. Click `id`, `name` or `ping` to sort,
click again to reverse; sorting survives filtering. Close with Escape, the backdrop, or ×.

- **Browse without searching.** Leave the box empty and you get every listed server by
  population. Filter by game (gta5 / rdr3 / gta5enhanced), locale, tag, and player range —
  all from data already in the list, so filtering costs no extra requests. Finding a *small*
  server is as easy as finding a big one.
- **Filter by anticheat** — has one / no name visible / a specific product (ElectronAC, Wave,
  FiveGuard, Reaper, pl_protect, generic `*-anticheat`). This one *does* cost requests:
  resource lists exist only behind `single/<code>`, so the page scans the current results in
  batches of 60 (six at a time, ~2s a batch) and caches what it learns for a day. "Scan more"
  continues through a larger result set, and the status line always says how many are still
  unknown rather than pretending an unscanned server has no anticheat. Every server you open
  normally also feeds the same cache.
- **Favorites.** Star a server; favorites are sampled every 5 minutes for history while the
  tab is open, and are the set that name-watching checks.
- **Watch player names.** Add a name and it appears in a panel down the left side with a live
  status dot — green on a server (with which one, click to open it), grey after they leave
  plus how long ago, amber before the first check. You get a toast and a browser notification
  (if allowed) when someone comes online, **moves between servers**, or **disconnects**.
  Matching is partial and case-insensitive. Checks run every 5 minutes against your
  favorites, or immediately via "check now".

  A failed check is never reported as a disconnect: a player is only marked offline when the
  server they were last seen on actually answers and says they're gone. If the network or
  CORS drops, their status is simply left alone until the next round.
- **Deep links.** Opening a server puts `?s=<code>` in the URL — paste that anywhere and it
  opens straight to that server's report.
- **CSV export.** The results list, and any player / resource / vars popup. Exports respect
  the current filter and sort, and carry a UTF-8 BOM so Excel shows unicode names correctly.
- **Keyboard.** `↓` from the search box enters the results, `↑`/`↓` move, `Enter` opens,
  `↑` at the top returns to the search box.
- **Server icons** in both the list and the report.

### History in the browser

A page can't poll while it's closed, so the site records one population sample every time you
open a server, kept in `localStorage`. Once a few hours have accumulated you get peak/median/low
and a median-players-by-hour chart. "Track every 5 min" samples a server on a timer for as long
as the tab stays open.

For history that collects while your browser is shut, use the CLI — `--watch` is the same idea
with a real process behind it.

### The one catch: `single/<code>` and CORS

Two endpoints, two different behaviours:

| Endpoint | Gives | Browser-readable |
|---|---|---|
| `streamRedir/` | name, join code, population, build, **IP:port**, all server vars | yes, reliably |
| `single/<code>` | **resource list + who's online** | intermittent — CORS header comes and goes |
| `http://<ip>:30120/*` | everything, live from the server itself | no — no CORS header, and mixed content on an HTTPS page |

The page tries `single/` anyway and degrades to a plain explanation when it's blocked, so it
never shows a broken panel. To make players and resources reliable, deploy `worker.js`
(Cloudflare Workers, free tier, ~20 lines) and set `PROXY` at the top of `index.html` to its
URL. It adds the missing header and nothing else.

The CLI has no such problem — CORS is a browser rule, so `fivem.py` always sees everything.

## CLI

`fivem.py` does the same thing in a terminal, plus population tracking the website can't do
(that needs a process running while your browser is closed).

```bash
python fivem.py krown              # search, pick from the list, full report
python fivem.py --code j4r9zmk     # straight to a known join code
python fivem.py --watch j4r9zmk    # poll every 5 min into history.db
python fivem.py --history j4r9zmk  # peak hours, padding trend, by-hour chart
python fivem.py demo               # self-check
```

Double-click `fivem.bat` on Windows to get a terminal that just asks for the name.

## How it works

`https://frontend.cfx-services.net/api/servers/streamRedir/` returns every listed server as a
protobuf stream: 4-byte little-endian length, then `Server{1:code, 2:Data}` with
`Data{1:maxclients, 2:clients, 4:hostname, 9:version}`. Both the Python and the JS decode it
with ~20 lines rather than a protobuf dependency. `single/<code>` returns the full detail JSON.

Field numbers were read off the live stream, not a published schema — if Cfx changes them,
search breaks loudly rather than silently, and `python fivem.py demo` will tell you.

## Reading the output

- **self-reported vs actual** — servers report their own player count to the list. A gap
  between that and the actual player array is the padding signal.
- **builds behind** — "current" is the 99th percentile of every build in the list, so it
  tracks reality without a version endpoint to go stale.
- **anticheat** — detection is by resource name. The pattern was built from a 608-server scan
  (see the corpus scripts in the repo history) and matches 51 distinct products including
  ElectronAC, WaveShield, FiveGuard, Reaper, pl_protect and every `*-anticheat` variant.
  Measured on that corpus: **38%** of servers expose a named anticheat, 1% only a `*_ac`
  suffix, **61% show nothing**. That last number is the honest ceiling — vendors tell
  operators to rename the resource so cheaters can't fingerprint it, so "none visible" is not
  evidence that none is running. Names are anchored deliberately: `sentinel` and `defender`
  are cars, `guardian`/`shield` are clothing and police props, and `anti-lag` / `anti-strafe`
  / `anti-bump` are gameplay tweaks.
- **screenshot-basic** — a normal, widely used resource, but it does mean staff can capture
  your game view. Worth knowing it's there.
- **player list** — name, slot id and ping is genuinely everything. Modern FXServer returns
  `identifiers: []` and a placeholder `127.0.0.1` endpoint even when you query the game
  server directly on its own port, so nobody's Steam or Discord ID is exposed to a lookup.
- **"list hidden"** — about a third of servers replace every entry with one placeholder
  (usually `Player`, id 0, ping 0). Measured over 422 servers listing 5+ players: 34% do it,
  and in **142 of 142 cases the number of placeholders exactly equalled the reported player
  count**. So it hides *who* is on, not *how many* — it is a privacy setting, not fake
  population. Both tools detect it and suppress the padding warning, which would otherwise
  fire on every one of those servers.
