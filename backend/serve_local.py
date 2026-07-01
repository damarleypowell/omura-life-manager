"""
Resilient local backend supervisor.

Runs the SQLite-backed app (backend.run_local:app) and AUTO-RESTARTS it if it
ever exits/crashes, so the frontend never sits on a dead backend ("Failed to
fetch"). Scheduler stays off locally. Stop with Ctrl-C.

Run:  python -m backend.serve_local
"""

import os
import sys
import time
import glob
import socket
import subprocess


def _ensure_local_pg() -> None:
    """Best-effort: start the user-owned local Postgres cluster if it exists and
    isn't already up, so the app's local DB is available after a reboot. Never
    blocks app startup — any failure is logged and ignored (the app will just
    fall back to SQLite if LOCAL_DATABASE_URL can't connect)."""
    data = os.environ.get("OMURA_PG_DATA", os.path.expanduser(r"~\omura_pgdata"))
    port = int(os.environ.get("OMURA_PG_PORT", "5433"))
    if not os.path.isdir(data):
        return
    sock = socket.socket()
    sock.settimeout(1)
    try:
        if sock.connect_ex(("127.0.0.1", port)) == 0:
            return  # already running
    finally:
        sock.close()
    pg_ctls = sorted(glob.glob(r"C:\Program Files\PostgreSQL\*\bin\pg_ctl.exe"))
    if not pg_ctls:
        return
    try:
        subprocess.run(
            [pg_ctls[-1], "-D", data, "-o", f"-p {port}", "-l", os.path.join(data, "server.log"), "start"],
            timeout=30, capture_output=True,
        )
        time.sleep(2)
        print(f"[serve] local Postgres started ({data} :{port})", flush=True)
    except Exception as exc:
        print(f"[serve] could not auto-start local Postgres: {exc}", flush=True)


_ensure_local_pg()

PORT = os.environ.get("OMURA_PORT", "8003")
CMD = [
    sys.executable, "-m", "uvicorn", "backend.run_local:app",
    "--host", "127.0.0.1", "--port", PORT, "--log-level", "warning",
    # Hot-reload on code edits so a long-running local backend never serves
    # stale routes (e.g. newly added Titan lesson endpoints 404-ing).
    "--reload", "--reload-dir", "backend",
]
ENV = {**os.environ, "SCHEDULER_ENABLED": "false"}

proc = None
try:
    backoff = 2
    while True:
        print(f"[serve] starting backend on :{PORT} …", flush=True)
        proc = subprocess.Popen(CMD, env=ENV)
        code = proc.wait()
        # Clean exit (0) only happens on a deliberate stop; anything else = crash.
        print(f"[serve] backend exited (code {code}); restarting in {backoff}s", flush=True)
        time.sleep(backoff)
        backoff = min(backoff * 2, 15)  # back off if it's crash-looping
except KeyboardInterrupt:
    print("[serve] stopping…", flush=True)
finally:
    if proc and proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except Exception:
            proc.kill()
