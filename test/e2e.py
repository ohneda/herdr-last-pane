#!/usr/bin/env python3
"""Drive the running Herdr window and check last-pane.go end to end.

    python3 test/e2e.py

Needs Herdr open with the mod installed and its floating block in the shown
layout. Makes a throwaway "lp-test" space, runs the scenarios, closes the
space and puts focus back where it was. The mod notices focus within ~300 ms,
so each step waits a little before the next.
"""
import json, pathlib, subprocess, sys, time

FOLDER = str(pathlib.Path(__file__).resolve().parent.parent)
SH = ["/bin/sh"]


def do(cmd, args=None):
    a = ["herdr-app", "do", cmd] + ([json.dumps(args)] if args else [])
    r = subprocess.run(a, capture_output=True, text=True)
    out = json.loads(r.stdout or "{}")
    if r.returncode or "error" in out:
        raise SystemExit(f"{cmd} {args}: {r.stdout}{r.stderr}")
    return out


def status():
    return json.loads(subprocess.run(["herdr-app", "status"], capture_output=True, text=True).stdout)


def settle(s=0.7):
    time.sleep(s)


results = []


def check(name, want_pane, want_tab=None):
    st = status()
    ok = st["focused_pane"] == want_pane and (want_tab is None or st["tab"] == want_tab)
    results.append((ok, name, st["focused_pane"], want_pane))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  got {st['focused_pane']} want {want_pane}"))


orig = status()
space = None
try:
    made = do("space.new", {"name": "lp-test", "folder": FOLDER, "argv": SH})
    space, tab1, a = made["space"], made["tab"], None
    settle()
    a = status()["focused_pane"]
    b = do("pane.split", {"direction": "right", "argv": SH})["pane"]
    settle()
    c = do("pane.split", {"direction": "down", "argv": SH})["pane"]
    settle()

    # 1. toggle between the last two
    do("pane.focus", {"pane": b}); settle()
    do("last-pane.go"); settle()
    check("go returns to the pane focused before (c)", c)
    do("last-pane.go"); settle()
    check("go again toggles back (b)", b)

    # 2. a third pane: only the last one is remembered, as in tmux
    # (pane.go from `herdr-app do` doesn't move focus in this build, so
    # pane.focus stands in for a directional move here)
    do("pane.focus", {"pane": a}); settle()
    check("focus moved to a", a)
    do("last-pane.go"); settle()
    check("go after a third pane returns to b", b)

    # 3. across tabs in the same space
    t2 = do("tab.new", {"space": space, "argv": SH})
    tab2, d = t2["tab"], None
    settle()
    d = status()["focused_pane"]
    do("last-pane.go"); settle()
    check("go from a new tab returns to b in tab 1", b, tab1)
    do("last-pane.go"); settle()
    check("go again goes back to tab 2", d, tab2)

    # 4. per space: another space's history doesn't leak in
    do("space.select", {"id": orig["space"]}); settle()
    before = status()["focused_pane"]
    do("last-pane.go"); settle()
    after = status()
    ok = after["space"] == orig["space"]
    results.append((ok, "go in another space stays in that space", after["space"], orig["space"]))
    print(("PASS " if ok else "FAIL ") + "go in another space stays in that space")
    do("space.select", {"id": space}); settle()

    # 5. previous pane closed: nothing happens
    do("tab.select", {"id": tab1}); settle()
    do("pane.focus", {"pane": a}); settle()
    do("pane.focus", {"pane": c}); settle()
    do("pane.close", {"pane": a}); settle()
    now = status()["focused_pane"]
    do("last-pane.go"); settle()
    check("go with the previous pane closed stays put", now)
finally:
    if space:
        do("space.close", {"id": space, "confirmed": True})
        settle()
    do("space.select", {"id": orig["space"]}); settle(0.3)
    do("tab.select", {"id": orig["tab"]}); settle(0.3)
    if orig.get("focused_pane"):
        do("pane.focus", {"pane": orig["focused_pane"]})

fails = [r for r in results if not r[0]]
print(f"\n{len(results) - len(fails)}/{len(results)} passed")
sys.exit(1 if fails else 0)
