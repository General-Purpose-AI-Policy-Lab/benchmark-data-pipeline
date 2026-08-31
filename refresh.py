"""Rafraîchit `input/feed/` depuis le réseau, puis on relance le notebook.

Usage : `python3 refresh.py`, puis Run All dans `pipeline.ipynb` — le notebook, lui,
reste hors-ligne et déterministe : il ne lit que `input/feed/`. Le diff des données
se lit dans git : `git diff --stat input/feed/`.

RAND non rafraîchi : rapport figé (Dev et al. 2025).

Les listes de boards (Kaggle, SEAL) sont lues dans `pipeline.ipynb` : une seule
source de vérité, pas de liste dupliquée ici.
"""
import ast
import hashlib
import io
import json
import socket
import urllib.error
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path

socket.setdefaulttimeout(60)              # une connexion qui cale échoue en 60 s au lieu de pendre

ROOT = Path(__file__).resolve().parent
FEED = ROOT / "input/feed"

EPOCH_ZIP_URL = "https://epoch.ai/data/benchmark_data.zip"
EPOCH_LIVE_URL = "https://epoch.ai/data/benchmarks.csv"
KAGGLE_URL = "https://www.kaggle.com/api/v1/benchmarks/{}/leaderboard"
SEAL_URL = "https://labs.scale.com/leaderboard/{}"
SEAL_HEADERS = {"User-Agent": "Mozilla/5.0"}   # sans en-tête de navigateur, la page ne se rend pas

FETCHED_AT = datetime.now(timezone.utc).isoformat()

# On repart de la provenance existante : une page conservée parce que sa source ne
# répond plus garde ainsi son entrée (url, date, sha256) au lieu de disparaître du
# fichier réécrit. Les artefacts re-téléchargés écrasent la leur au passage.
_PROV_PATH = FEED / "provenance.json"
provenance = (json.loads(_PROV_PATH.read_text()) if _PROV_PATH.exists() else {})


def fetch(key, url, headers=None):
    """Télécharge une URL, enregistre sa provenance, renvoie les octets."""
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers or {})) as r:
        data = r.read()
    provenance[key] = {"url": url, "fetched_at": FETCHED_AT,
                       "sha256": hashlib.sha256(data).hexdigest(), "byte_size": len(data)}
    print(f"{key} : {len(data):,} o")
    return data


def specs_du_notebook():
    """KAGGLE_SPEC / SEAL_SPEC lus dans le notebook (json + ast, pas d'exécution)."""
    cells = json.loads((ROOT / "pipeline.ipynb").read_text())["cells"]
    code = "\n".join("".join(c["source"]) for c in cells if c["cell_type"] == "code")
    out = {}
    for node in ast.parse(code).body:
        if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name):
            if node.targets[0].id in ("KAGGLE_SPEC", "SEAL_SPEC"):
                out[node.targets[0].id] = ast.literal_eval(node.value)
    assert out.keys() == {"KAGGLE_SPEC", "SEAL_SPEC"}, f"specs introuvables : {sorted(out)}"
    return out["KAGGLE_SPEC"], out["SEAL_SPEC"]


if __name__ == "__main__":
    kaggle_spec, seal_spec = specs_du_notebook()
    print(f"{len(kaggle_spec)} board(s) Kaggle, {len(seal_spec)} board(s) SEAL (lus dans pipeline.ipynb)\n")

    # Epoch ZIP : remplace tous les CSV du répertoire, sauf aliases.csv (dictionnaire du projet).
    data = fetch("input/feed/epoch (benchmark_data.zip)", EPOCH_ZIP_URL)
    # Le ZIP est ouvert AVANT toute suppression : une archive tronquée ou corrompue
    # doit échouer sans avoir détruit le feed en place.
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        fresh = {Path(n).name: z.read(n) for n in z.namelist()
                 if n.endswith(".csv") and Path(n).name != "aliases.csv"}
    assert fresh, "le ZIP Epoch ne contient aucun CSV : feed laissé intact"
    for p in (FEED / "epoch").glob("*.csv"):
        if p.name != "aliases.csv":
            p.unlink()
    for name, blob in fresh.items():
        (FEED / "epoch" / name).write_bytes(blob)

    # Feed live Epoch : un seul CSV, versionné par tâche.
    (FEED / "epoch_live/epoch_live_benchmarks.csv").write_bytes(
        fetch("input/feed/epoch_live/epoch_live_benchmarks.csv", EPOCH_LIVE_URL))

    # Kaggle : un JSON de leaderboard par board.
    for board in kaggle_spec:
        name = board.replace("/", "_") + ".json"
        (FEED / "kaggle" / name).write_bytes(fetch(f"input/feed/kaggle/{name}", KAGGLE_URL.format(board)))

    # SEAL : une page HTML par board ; un board qui ne répond plus garde sa page (périmé > vide).
    for slug in seal_spec:
        try:
            data = fetch(f"input/feed/seal/{slug}.html", SEAL_URL.format(slug), SEAL_HEADERS)
        except urllib.error.HTTPError as e:
            print(f"  ! seal/{slug} : HTTP {e.code} — page existante conservée")
            continue
        (FEED / "seal" / f"{slug}.html").write_bytes(data)

    provenance["input/feed/rand/rand_benchmark_scores.csv"] = {
        "url": "https://www.rand.org/pubs/research_reports/RRA3797-1.html",
        "fetched_at": "figé", "note": "RAND RR-A3797-1 (Dev et al. 2025), jamais rafraîchi",
        "sha256": hashlib.sha256((FEED / "rand/rand_benchmark_scores.csv").read_bytes()).hexdigest(),
        "byte_size": (FEED / "rand/rand_benchmark_scores.csv").stat().st_size}
    print("\nrand : non rafraîchi (rapport figé, Dev et al. 2025)")
    (FEED / "provenance.json").write_text(json.dumps(provenance, indent=2, sort_keys=True) + "\n")
    print(f"provenance.json : {len(provenance)} artefact(s) — diff des données : git diff --stat input/feed/")
