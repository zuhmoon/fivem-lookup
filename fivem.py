#!/usr/bin/env python3
"""Search FiveM servers by name, pick one, dump everything public about it.

    python fivem.py krown          # search -> numbered list -> pick -> full report
    python fivem.py krown 1        # skip the prompt, take result #1
    python fivem.py --code j4r9zmk # already know the join code
    python fivem.py --refresh nopixel
    python fivem.py --players j4r9zmk        # who is online right now
    python fivem.py --watch j4r9zmk 8974lv   # poll every 5 min into history.db
    python fivem.py --history j4r9zmk        # peak hours, padding, trend
    python fivem.py demo           # self-check

stdlib only. The 20MB master list is cached next to this file for 15 min.
"""
import json, os, re, sqlite3, statistics, struct, sys, time, urllib.request

API = "https://frontend.cfx-services.net/api/servers"
CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "list.bin")
MAX_AGE = 900
COLOR = re.compile(r"\^[0-9]")
BUILD = re.compile(r"v1\.0\.0\.(\d+)")
# Named products + the literal word anticheat. Built from a 608-server scan and anchored
# hard: "sentinel" and "defender" are car names, "guardian"/"shield" are clothing and police
# props, and anti-lag / anti-strafe / anti-bump are gameplay tweaks, not anticheats.
# Measured on that corpus: 38% expose a named anticheat, 1% only a *_ac suffix, 61% nothing.
AC = re.compile(r"""
    anti[-_ ]?cheat
  | ^electron(ac)?$ | electron[-_]?ac
  | fiveguard
  | ^(fivem[-_]?)?waveshield$ | ^wave$ | ^w[-_]?shield$
  | ^reaper(v\d+)?([-_]?ac)?$
  | ^pl[-_]protect$ | ^shieldm[-_]fivem$ | ^cfguard$ | ^bjornshield$
  | ^likizao[-_]ac$ | ^ec[-_]ac$ | ^rmod_gauntlet_ac$
  | ^hyperion$ | ^sentinel[-_]ac$ | ^scarab[-_]?ac$ | ^athena[-_]?ac$
  | ^watchdog$
""", re.I | re.X)
# trailing _ac is a common convention but also catches unrelated scripts — report separately
MAYBE_AC = re.compile(r"[-_]ac$", re.I)
STALE = 500  # ponytail: FXServer ships several builds/day, so ~500 behind is a couple
             # of months unpatched. Tune if it flags everything or nothing.


def get(url, binary=False):
    req = urllib.request.Request(url, headers={"User-Agent": "CitizenFX/1.0"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read() if binary else json.loads(r.read())


def varint(b, i):
    n = s = 0
    while True:
        c = b[i]; i += 1
        n |= (c & 0x7F) << s; s += 7
        if not c & 0x80:
            return n, i


def walk(b):
    """Minimal protobuf reader: yields (field_no, value). Enough for this schema."""
    i = 0
    while i < len(b):
        key, i = varint(b, i)
        no, wt = key >> 3, key & 7
        if wt == 0:
            v, i = varint(b, i)
        elif wt == 2:
            ln, i = varint(b, i); v = b[i:i + ln]; i += ln
        elif wt == 5:
            v = struct.unpack("<I", b[i:i + 4])[0]; i += 4
        elif wt == 1:
            v = struct.unpack("<Q", b[i:i + 8])[0]; i += 8
        else:
            return  # group wiretypes: not in this schema, bail rather than desync
        yield no, v


# Verified against the live stream 2026-08-06: frame = <u32 len><Server>,
# Server{1:EndPoint, 2:Data}, Data{1:maxclients, 2:clients, 4:hostname, 5:gametype,
# 6:mapname, 9:version, 12:repeated var{1:key,2:value}}.
def parse(blob):
    off, out = 0, []
    while off + 4 <= len(blob):
        (ln,), off = struct.unpack("<I", blob[off:off + 4]), off + 4
        frame, off = blob[off:off + ln], off + ln
        if len(frame) < ln:
            break  # truncated tail
        code, s = None, {}
        for no, v in walk(frame):
            if no == 1:
                code = v.decode("utf8", "replace")
            elif no == 2:
                for n2, v2 in walk(v):
                    if n2 == 2:
                        s["clients"] = v2
                    elif n2 == 1:
                        s["max"] = v2
                    elif n2 == 4:
                        s["name"] = v2.decode("utf8", "replace")
                    elif n2 == 9:
                        m = BUILD.search(v2.decode("utf8", "replace"))
                        if m:
                            s["build"] = int(m.group(1))
        if code:
            s["code"] = code
            out.append(s)
    return out


def fetch_list(refresh=False):
    if refresh or not os.path.exists(CACHE) or time.time() - os.path.getmtime(CACHE) > MAX_AGE:
        sys.stderr.write("downloading master list...\n")
        blob = get(API + "/streamRedir/", binary=True)
        open(CACHE, "wb").write(blob)
    return parse(open(CACHE, "rb").read())


def clean(s):
    return COLOR.sub("", s).strip()


def latest_build(servers):
    """What 'current' means today, taken from the population itself — no version
    endpoint to go stale on us. 99th pct, not max, so one bogus self-reported
    version string can't move the bar."""
    b = sorted(s["build"] for s in servers if s.get("build"))
    return b[int(len(b) * 0.99) - 1] if b else 0  # nearest-rank, so n=100 gives the 99th


def search(servers, term):
    t = term.lower()
    hits = [s for s in servers if t in clean(s.get("name", "")).lower()]
    return sorted(hits, key=lambda s: -s.get("clients", 0))


FRAMEWORKS = {"qb-core": "QBCore", "qbx_core": "Qbox", "es_extended": "ESX",
              "ox_core": "ox_core", "vrp": "vRP", "nd_core": "ND"}


def report(code):
    d = get(f"{API}/single/{code}")["Data"]
    v = d.get("vars", {})
    res = d.get("resources", [])
    players = d.get("players", [])
    pings = [p.get("ping", 0) for p in players]
    said = d.get("selfReportedClients")

    print(f"\n{clean(d.get('hostname', '?'))}")
    print(f"  code      cfx.re/join/{code}")
    print(f"  endpoint  {', '.join(d.get('connectEndPoints') or ['(proxied)'])}")
    print(f"  players   {d.get('clients')}/{d.get('svMaxclients')}"
          + (f"   self-reported {said}" if said not in (None, d.get("clients")) else ""))
    mine = BUILD.search(d.get("server") or "")
    behind = ""
    if mine and os.path.exists(CACHE):  # don't trigger a 20MB download just for this
        newest = latest_build(parse(open(CACHE, "rb").read()))
        gap = newest - int(mine.group(1))
        if gap > STALE:
            behind = f"   <-- {gap} builds behind current ({newest})"
    print(f"  build     {d.get('server')}{behind}")
    print(f"  game      {d.get('gametype')} / {d.get('mapname')}  onesync={v.get('onesync_enabled')}")
    print(f"  owner     {d.get('ownerName')}  {d.get('ownerProfile') or ''}")
    print(f"  discord   {v.get('discord.gg') or v.get('Discord') or '-'}")
    print(f"  locale    {v.get('locale')}   tags: {(v.get('tags') or '-')[:80]}")

    fw = [n for k, n in FRAMEWORKS.items() if k in res]
    print(f"\n  {len(res)} resources   framework: {', '.join(fw) or 'unknown/custom'}")
    ac = [r for r in res if AC.search(r)]
    maybe = [r for r in res if MAYBE_AC.search(r) and not AC.search(r)]
    if ac:
        print(f"    {'anticheat':14} {', '.join(ac[:6])}")
    elif maybe:
        print(f"    {'maybe AC':14} {', '.join(maybe[:6])}  (name convention only)")
    else:
        print(f"    {'anticheat':14} none visible — renaming is normal, so this isn't proof")

    for label, pat in (("screenshot", r"screenshot"),
                       ("escrowed/paid", r"^(esx_|qb-)?(k4mb1|nopixel|codem|quasar|rcore)")):
        m = [r for r in res if re.search(pat, r, re.I)]
        if m:
            print(f"    {label:14} {', '.join(m[:6])}")

    # padding heuristic — see notes at bottom of file
    flags = []
    if said and abs(said - len(players)) > max(5, said * 0.1):
        flags.append(f"list count {said} vs {len(players)} actual player entries")
    if not hidden_list(players):
        if pings and len(set(pings)) <= max(1, len(pings) // 10):
            flags.append(f"{len(set(pings))} distinct pings across {len(pings)} players")
        if sum(1 for p in pings if p <= 0) > len(pings) * 0.2:
            flags.append("many zero pings")
    print("\n  population: " + ("LOOKS PADDED - " + "; ".join(flags) if flags else "consistent"))
    if hidden_list(players):
        print(f"  player list hidden - every entry is a placeholder "
              f"({players[0].get('name')!r}, id 0, ping 0); the count itself is still real")

    out = os.path.join(os.path.dirname(CACHE), f"{code}.json")
    json.dump(d, open(out, "w", encoding="utf8"), indent=2, ensure_ascii=False)
    print(f"\n  full dump -> {out}\n")


def hidden_list(players):
    """~34% of servers replace every entry with a placeholder ('Player', id 0, ping 0).
    That's privacy, not padding — the count still matches — so the ping-shape checks must
    skip these or they flag a third of all servers as fake."""
    return (len(players) >= 5
            and len({p.get("name") for p in players}) == 1
            and all(not p.get("id") and not p.get("ping") for p in players))


def live_players(d):
    """Ask the server itself, so the list is current rather than a cached snapshot.
    Falls back to the frontend copy when the port is closed or proxied."""
    for ep in d.get("connectEndPoints") or []:
        if ep.startswith("https://"):
            continue  # Cfx-proxied: no direct port to hit
        try:
            req = urllib.request.Request(f"http://{ep}/players.json",
                                         headers={"User-Agent": "CitizenFX/1.0"})
            with urllib.request.urlopen(req, timeout=8) as r:
                return json.loads(r.read()), "direct"
        except Exception:
            pass
    return d.get("players") or [], "cached"


def players(code):
    d = get(f"{API}/single/{code}")["Data"]
    pl, src = live_players(d)
    pings = [p.get("ping") or 0 for p in pl]
    print(f"\n{clean(d.get('hostname','?'))} — {len(pl)} online ({src})")
    if hidden_list(pl):
        print(f"\n  This server hides its player list: all {len(pl)} entries are the same"
              f" placeholder ({pl[0].get('name')!r}, id 0, ping 0).")
        print("  The count is real, the names are not. Nothing further to show.\n")
        return
    if pings:
        print(f"  ping median {statistics.median(pings):.0f}, range {min(pings)}-{max(pings)}, "
              f"{len(set(pings))} distinct\n")
    for p in sorted(pl, key=lambda p: p.get("ping") or 0):
        print(f"  {p.get('id'):>5}  {str(p.get('name'))[:38]:<38} {p.get('ping'):>4}ms")

    leaked = {i.split(":")[0] for p in pl for i in (p.get("identifiers") or [])}
    print(f"\n  identifiers exposed: {', '.join(sorted(leaked)) if leaked else 'none'}"
          " (FXServer masks these from outside queries by default)\n")


def db():
    c = sqlite3.connect(os.path.join(os.path.dirname(CACHE), "history.db"))
    c.execute("CREATE TABLE IF NOT EXISTS pop"
              "(ts INT, code TEXT, clients INT, listed INT, said INT, max INT)")
    return c


def watch(codes, every=300):
    c = db()
    print(f"polling {', '.join(codes)} every {every}s — ctrl-c to stop")
    while True:
        for code in codes:
            try:
                d = get(f"{API}/single/{code}")["Data"]
                row = (int(time.time()), code, d.get("clients") or 0,
                       len(d.get("players") or []), d.get("selfReportedClients") or 0,
                       d.get("svMaxclients") or 0)
                c.execute("INSERT INTO pop VALUES (?,?,?,?,?,?)", row)
                c.commit()
                print(f"  {time.strftime('%H:%M')} {code:<9} {row[2]:>4}/{row[5]}", flush=True)
            except Exception as e:
                # a dropped connection at 3am must not end the run and lose the series
                print(f"  {time.strftime('%H:%M')} {code:<9} failed: {e}", flush=True)
        time.sleep(every)


def bars(by_hour, width=34):
    top = max(by_hour.values())
    for h in sorted(by_hour):
        n = by_hour[h]
        print(f"  {h:02d}:00 {'#' * max(1, round(n / top * width)):<{width}} {n}")


def history(code):
    rows = db().execute("SELECT ts, clients, listed, said, max FROM pop "
                        "WHERE code=? ORDER BY ts", (code,)).fetchall()
    if not rows:
        sys.exit(f"no samples yet - run: python fivem.py --watch {code}")
    pop = [r[1] for r in rows]
    span = (rows[-1][0] - rows[0][0]) / 3600
    print(f"\n{code}: {len(rows)} samples over {span:.1f}h")
    print(f"  peak {max(pop)}   median {statistics.median(pop):.0f}   low {min(pop)}"
          f"   cap {rows[-1][4]}")

    gap = [r[3] - r[2] for r in rows if r[3]]  # self-reported minus actual entries
    if gap:
        print(f"  self-reported over actual: median {statistics.median(gap):+.0f}, "
              f"worst {max(gap):+d}")

    by_hour = {}
    for r in rows:
        by_hour.setdefault(time.localtime(r[0]).tm_hour, []).append(r[1])
    if span >= 6:
        print("\n  median players by hour (your local time)")
        bars({h: round(statistics.median(v)) for h, v in by_hour.items()})
    else:
        print(f"\n  (need ~6h of samples for the by-hour view, have {span:.1f}h)")
    print()


def demo():
    # one synthetic frame through the real parser
    data = (b"\x0a\x03abc\x12\x24\x08\x20\x10\x05\x22\x07My Serv"
            b"\x4a\x15FXServer v1.0.0.31039")
    blob = struct.pack("<I", len(data)) + data
    assert parse(blob) == [{"max": 32, "clients": 5, "name": "My Serv",
                            "build": 31039, "code": "abc"}], parse(blob)
    assert clean("^2Green^0 RP") == "Green RP"
    # one absurd self-reported build must not become "latest"
    assert latest_build([{"build": b} for b in [100] * 99 + [999999]]) == 100
    # real anticheats match; furniture, cars, clothing and gameplay tweaks do not
    assert all(AC.search(r) for r in ["ElectronAC", "electron", "waveshield", "qbx_anticheat",
                                      "reaperv4", "pl_protect", "s6o-fiveguard", "aegis-anticheat"])
    assert not any(AC.search(r) for r in
                   ["ac_radio", "ac_single_modern_armchair_1", "reaper-replays", "wm_reaper880",
                    "electronicstore", "bracelet-electronique", "codewave-caps", "204ssentinelgt",
                    "bt_defender", "guardian-character", "policeshields", "antilag",
                    "tgiann-anti-strafe", "mm_coastguard"])
    assert MAYBE_AC.search("likizao_ac") and not MAYBE_AC.search("ac_radio")
    # an anonymised list must not be mistaken for a real one, or vice versa
    assert hidden_list([{"name": "Player", "id": 0, "ping": 0}] * 9)
    assert not hidden_list([{"name": "Player", "id": i, "ping": 30 + i} for i in range(9)])
    assert not hidden_list([{"name": "Player", "id": 0, "ping": 0}] * 3)   # too few to tell
    servers = [{"name": "^1Krown RP", "clients": 5}, {"name": "krown dev", "clients": 90},
               {"name": "Other", "clients": 1}]
    assert [s["clients"] for s in search(servers, "KROWN")] == [90, 5]
    assert parse(b"\x10\x00\x00\x00\x0a\x03abc") == []  # truncated tail, no crash
    print("ok")


def main(args):
    hits = search(fetch_list("--refresh" in sys.argv), args[0])
    if not hits:
        sys.exit(f"no server name contains {args[0]!r}")
    for i, s in enumerate(hits[:30], 1):
        print(f"{i:>3}. {s.get('clients',0):>4}/{s.get('max',0):<4} {clean(s['name'])[:60]:<60} {s['code']}")
    if len(hits) > 30:
        print(f"     ... {len(hits)-30} more")

    pick = int(args[1]) if len(args) > 1 else (1 if len(hits) == 1 else int(input("\npick #: ")))
    report(hits[pick - 1]["code"])


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if args and args[0] == "demo":
        demo(); sys.exit()
    if "--code" in sys.argv:
        report(args[0]); sys.exit()
    if "--players" in sys.argv:
        players(args[0]); sys.exit()
    if "--watch" in sys.argv:
        try:
            watch(args)
        except KeyboardInterrupt:
            print("\nstopped —", f"python fivem.py --history {args[0]}")
        sys.exit()
    if "--history" in sys.argv:
        history(args[0]); sys.exit()

    launched = not args  # double-clicked / no argv: prompt, and hold the window open
    if launched:
        args = [input("server name: ").strip()]
    try:
        if args[0]:
            main(args)
    except (KeyboardInterrupt, EOFError):
        pass
    except Exception as e:  # a bare traceback vanishes with the window
        print(f"\nerror: {e}")
    finally:
        if launched:
            input("\npress enter to close...")

# ponytail: hand-rolled 20-line protobuf reader instead of a .proto + protobuf dep —
# the schema is 7 fields and hasn't moved in years. If Cfx adds nesting you care
# about, that's the point to `pip install protobuf` and generate properly.
