"""
Resilient local frontend supervisor — makes Omura's UI self-heal.

Runs the Next.js dev server (`npm run dev`) and watches its HTTP health. The
classic failure that leaves you staring at a white screen is a corrupted
`.next` dev cache: the server keeps *running* but returns HTTP 500 on every page
("Cannot find module './chunks/vendor-chunks/...'"). A plain process-restart
never catches that, because the process itself never dies. This watchdog notices
the 500s (or an outright crash), wipes the stale `.next` cache, and restarts — so
the app recovers on its own instead of needing a manual cache clear.

Run:  python serve_frontend.py     (from the repo root)
Stop: Ctrl-C
"""

import os
import time
import shutil
import subprocess
import urllib.request
import urllib.error

ROOT = os.path.dirname(os.path.abspath(__file__))
FRONTEND = os.path.join(ROOT, "frontend")
NEXT_DIR = os.path.join(FRONTEND, ".next")
PORT = os.environ.get("OMURA_FRONTEND_PORT", "3001")
URL = f"http://localhost:{PORT}/"

# Wipe-.next-and-restart attempts before we give up and just leave the server up.
# A persistent 500 after a *clean* cache is a real code error, not corruption —
# restarting won't fix it and we don't want a crash loop hiding the dev overlay.
MAX_HEALS = 3
STARTUP_GRACE = 120   # seconds to let the first compile finish before judging
POLL_EVERY = 5        # seconds between health checks
BAD_STREAK = 3        # consecutive bad polls that count as "wedged"/"dead"


def _http_status(timeout=4):
    """HTTP status code for the home page, or None if not answering yet."""
    try:
        with urllib.request.urlopen(URL, timeout=timeout) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception:
        return None


def _clear_next():
    if os.path.isdir(NEXT_DIR):
        shutil.rmtree(NEXT_DIR, ignore_errors=True)
        print("[frontend] wiped stale .next cache", flush=True)


def _npm():
    for name in ("npm.cmd", "npm.exe", "npm"):
        p = shutil.which(name)
        if p:
            return p
    return "npm"


def _start():
    print(f"[frontend] starting dev server on :{PORT} ...", flush=True)
    flags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
    return subprocess.Popen([_npm(), "run", "dev"], cwd=FRONTEND, creationflags=flags)


def _kill_tree(proc):
    if not proc or proc.poll() is not None:
        return
    if os.name == "nt":
        # npm spawns node as a child — kill the whole tree, not just npm.
        subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"], capture_output=True)
    else:
        proc.terminate()
    try:
        proc.wait(timeout=10)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass


def main():
    heals = 0
    proc = None
    started = 0.0
    bad = 0
    healthy_seen = False
    try:
        while True:
            if proc is None:
                proc = _start()
                started = time.time()
                bad = 0
                healthy_seen = False

            time.sleep(POLL_EVERY)

            # 1) Crashed on its own → clear cache (crashes often leave it dirty) + restart.
            if proc.poll() is not None:
                print(f"[frontend] dev server exited (code {proc.returncode})", flush=True)
                if heals < MAX_HEALS:
                    _clear_next()
                    heals += 1
                proc = None
                time.sleep(2)
                continue

            status = _http_status()

            # 2) Healthy → reset the heal budget.
            if status == 200:
                healthy_seen = True
                bad = 0
                heals = 0
                continue

            # 3) Wedged (serving 500s) → wipe .next and restart, up to the budget.
            if status == 500:
                bad += 1
                if bad >= BAD_STREAK:
                    if heals < MAX_HEALS:
                        print("[frontend] wedged (HTTP 500) — healing: wiping .next + restart", flush=True)
                        _kill_tree(proc)
                        _clear_next()
                        heals += 1
                        proc = None
                    else:
                        print("[frontend] still 500 after a clean cache — likely a code error; "
                              "leaving the server up so the dev error is visible.", flush=True)
                        bad = 0
                continue

            # 4) Not answering. Fine during first compile; otherwise treat as dead.
            if not healthy_seen and (time.time() - started) < STARTUP_GRACE:
                continue
            bad += 1
            if bad >= BAD_STREAK:
                print("[frontend] unresponsive — restarting", flush=True)
                _kill_tree(proc)
                proc = None
    except KeyboardInterrupt:
        print("[frontend] stopping...", flush=True)
    finally:
        _kill_tree(proc)


if __name__ == "__main__":
    main()
