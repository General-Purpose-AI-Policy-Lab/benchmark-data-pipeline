#!/usr/bin/env python3
"""Static server for index.html plus the local refresh API.

Serves the repo root exactly like `python3 -m http.server`, and adds the two
endpoints the Refresh tab calls:

    GET  /api/snapshots  -> {"snapshots": ["2026-08-19", ...]}
    POST /api/run        -> {"ok": bool, "log": str, "check": str}
    GET  /api/queue      -> {"missing_models": [...], "missing_meta": [...],
                             "categories": [...]}
    POST /api/curate     -> {"ok": true} | 400 {"error": ...} | 409 during a run

/api/curate appends one reviewed decision per call to the canonical files:
{"action":"review","name":N} · {"action":"alias","variant":V,"canonical":C,"note":T}
· {"action":"drop","variant":V,"note":T} · {"action":"metadata","benchmark":B,
"category":C,"notes":T}. A decided name leaves /api/queue immediately, which is
also the duplicate guard.

/api/run deletes the requested source caches inside the target snapshot folder,
runs the pipeline notebook headlessly, then runs scripts/check.py. The swap into
data/processed/ is the notebook's last section (section 10), so a failed run
leaves data/processed/ untouched, and check.py's byte-compare against
data/pipeline/output/ catches a half-written output.
"""
import csv
import functools
import json
import os
import re
import shutil
import subprocess
import sys
import threading
from datetime import datetime, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SNAPSHOTS = ROOT / "data" / "pipeline" / "snapshots"
CANON = ROOT / "data" / "pipeline" / "canonical"
MISSING = ROOT / "data" / "pipeline" / "output" / "missing_models.csv"
MERGED = ROOT / "data" / "processed" / "benchmarks_merged.csv"
ALIASES = CANON / "model_aliases.csv"
METADATA = CANON / "benchmark_metadata.csv"
REVIEWED = CANON / "reviewed_models.txt"
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
PORT = 8130

_jupyter = Path.home() / "miniforge3" / "envs" / "pymc_env" / "bin" / "jupyter"
JUPYTER = str(_jupyter) if _jupyter.exists() else "jupyter"

# Cache paths a force-refetch checkbox clears, relative to the target snapshot.
CACHES = {
    "epoch_zip": ["epoch", "epoch_benchmark_data.zip", "provenance.json"],
    "live": ["epoch_live_benchmarks.csv"],
    "rand": ["rand_benchmark_scores.csv"],
    "seal": ["seal"],
    "kaggle": ["kaggle"],
}

# ponytail: one user, one lock; a queue if this ever multi-users
RUN_LOCK = threading.Lock()


def _exec(cmd, cwd, env, timeout):
    """Run cmd, return (returncode, stdout+stderr). A timeout or a missing
    executable comes back as a failing code, not an exception."""
    try:
        r = subprocess.run(cmd, cwd=str(cwd), env=env, capture_output=True,
                           text=True, timeout=timeout)
        return r.returncode, r.stdout + r.stderr
    except subprocess.TimeoutExpired:
        return 1, f"TIMEOUT: {cmd[0]} ran past {timeout} s and was killed.\n"
    except FileNotFoundError as e:
        return 1, f"NOT FOUND: {e}\n"


def run(date, refetch):
    target = SNAPSHOTS / (date or datetime.now(timezone.utc).strftime("%Y-%m-%d"))
    for key in refetch:
        for name in CACHES[key]:
            p = target / name
            if p.is_dir():
                shutil.rmtree(p)
            elif p.exists():
                p.unlink()

    env = {**os.environ, **({"SNAPSHOT_DATE": date} if date else {})}
    code, log = _exec([JUPYTER, "execute", "pipeline.ipynb"],
                      ROOT / "data" / "pipeline", env, 900)
    check = ""
    ok = False
    if code == 0:
        code, check = _exec([sys.executable, str(ROOT / "scripts" / "check.py")],
                            ROOT, env, 60)
        ok = code == 0
    return {"ok": ok, "log": log[-8000:], "check": check}


def _col(path, field):
    """One CSV column as a list, skipping empty cells. [] if the file is missing."""
    if not path.exists():
        return []
    with path.open(newline="") as f:
        return [row[field] for row in csv.DictReader(f) if row.get(field)]


def queue():
    """The open curation decisions, recomputed from the files on every call."""
    decided = set(_col(ALIASES, "variant"))
    if REVIEWED.exists():
        decided |= {l.strip() for l in REVIEWED.read_text().splitlines() if l.strip()}
    return {
        "missing_models": [m for m in _col(MISSING, "model_version")
                           if m not in decided],
        "missing_meta": sorted(set(_col(MERGED, "benchmark"))
                               - set(_col(METADATA, "benchmark"))),
        "categories": sorted(set(_col(METADATA, "category"))),
    }


def _ensure_nl(path):
    """Make sure the file ends with a newline before an append lands."""
    if path.exists() and path.read_bytes()[-1:] not in (b"", b"\n"):
        with path.open("a") as f:
            f.write("\n")


def _append_row(path, row):
    _ensure_nl(path)
    with path.open("a", newline="") as f:
        csv.writer(f).writerow(row)


def curate(body):
    """Apply one decision; return an error string or None on success. Queue
    membership doubles as the duplicate guard: a decided name leaves the queue."""
    q = queue()
    action = body.get("action")
    if action == "review":
        name = body.get("name")
        if name not in q["missing_models"]:
            return "name is not in the current missing_models queue"
        _ensure_nl(REVIEWED)
        with REVIEWED.open("a") as f:
            f.write(name + "\n")
    elif action in ("alias", "drop"):
        variant = body.get("variant")
        note = (body.get("note") or "").strip()
        if variant not in q["missing_models"]:
            return "variant is not in the current missing_models queue"
        if action == "alias":
            canonical = body.get("canonical") or ""
            if canonical not in set(_col(MERGED, "model_version")):
                return "canonical must be an existing model_version in the merged data"
        else:
            canonical = ""  # the DROP sentinel
            if not note:
                return "a drop must carry a justification note"
        _append_row(ALIASES, [variant, canonical, note])
    elif action == "metadata":
        bench = body.get("benchmark")
        if bench not in q["missing_meta"]:
            return "benchmark is not in the current missing_meta queue"
        category = (body.get("category") or "").strip()
        if not category:
            return "category must be non-empty"
        _append_row(METADATA, [bench, category, (body.get("notes") or "").strip()])
    else:
        return "unknown action"
    return None


class Handler(SimpleHTTPRequestHandler):
    def _json(self, code, payload):
        body = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/api/queue":
            return self._json(200, queue())
        if path != "/api/snapshots":
            return super().do_GET()
        names = sorted((d.name for d in SNAPSHOTS.iterdir()
                        if d.is_dir() and DATE_RE.match(d.name)),
                       reverse=True) if SNAPSHOTS.is_dir() else []
        self._json(200, {"snapshots": names})

    def do_POST(self):
        path = self.path.split("?")[0]
        if path not in ("/api/run", "/api/curate"):
            return self._json(404, {"error": "not found"})
        try:
            n = int(self.headers.get("Content-Length") or 0)
            body = json.loads(self.rfile.read(n) or "{}")
        except ValueError:
            return self._json(400, {"error": "body is not JSON"})
        if not isinstance(body, dict):
            return self._json(400, {"error": "body must be a JSON object"})

        if path == "/api/curate":
            if not RUN_LOCK.acquire(blocking=False):
                return self._json(409, {"error": "a run is already in progress"})
            try:
                err = curate(body)
            finally:
                RUN_LOCK.release()
            return self._json(400, {"error": err}) if err else self._json(200, {"ok": True})

        date = body.get("date") or ""
        refetch = body.get("refetch") or []
        if date and not DATE_RE.match(date):
            return self._json(400, {"error": "date must be YYYY-MM-DD or empty"})
        if not isinstance(refetch, list) or any(k not in CACHES for k in refetch):
            return self._json(400, {"error": f"refetch keys must be from {sorted(CACHES)}"})

        if not RUN_LOCK.acquire(blocking=False):
            return self._json(409, {"error": "a run is already in progress"})
        try:
            self._json(200, run(date, refetch))
        finally:
            RUN_LOCK.release()


if __name__ == "__main__":
    handler = functools.partial(Handler, directory=str(ROOT))
    print(f"serving {ROOT} on http://localhost:{PORT}  (Ctrl-C to stop)")
    ThreadingHTTPServer(("127.0.0.1", PORT), handler).serve_forever()
