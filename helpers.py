"""Machinerie du pipeline. Le notebook (pipeline.ipynb) est le récit ; ce fichier tient les fonctions.

Identification d'un modèle = tuple (base_model, reasoning_level, reasoning_tokens, snapshot, variant).
Convention : '' = inconnu. Deux inconnus ne fusionnent PAS avec du connu :
opus-5 (level='') et opus-5_high (level='high') sont deux modèles distincts.

« Nom machine » = nom au format machine qu'utilisent Epoch et Kaggle, ex. claude-opus-4-8_high
ou zai-org/glm-4.7. Sa forme est fixe — [fournisseur/]base[-date][_suffixe] — donc on le découpe
en colonnes sans dictionnaire (split_name) :
- '_' introduit un réglage, '-' fait partie du nom (kimi-k2-thinking est un NOM, pas un réglage).
- suffixe (majuscules ignorées) : effort minimal|low|medium|high|xhigh|max|none ; budget <N>K ;
  thinking -> variant='thinking' ; unknown -> variant='unknown-effort' (la source dit explicitement
  « effort inconnu », distinct d'un nom nu). Suffixe hors vocabulaire = le '_' fait partie du nom.
- date extraite seulement aux formats YYYY-MM-DD / YYYYMMDD en fin de base (les formats courts
  2507, 0528, 03-2025 restent dans base_model, exprès : pas d'ambiguïté possible).
"""
import csv
import json
import re
import uuid
from pathlib import Path

IDENT_COLS = ["base_model", "reasoning_level", "reasoning_tokens", "snapshot", "variant"]
ALIAS_COLS = ["raw_name", *IDENT_COLS, "note"]
NAMESPACE = uuid.uuid5(uuid.NAMESPACE_DNS, "eval-data-pipeline")

EFFORTS = {"minimal", "low", "medium", "high", "xhigh", "max", "none"}
_BUDGET = re.compile(r"(\d+)k")
_DATE_ISO = re.compile(r"-(\d{4})-(\d{2})-(\d{2})$")
_DATE_8 = re.compile(r"-(20\d{2})(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])$")


def strip_name(raw):
    """Nettoyage mécanique : footnotes */† et blancs en fin de nom."""
    return re.sub(r"[\s*†]+$", "", str(raw)).strip()


def split_name(name):
    """Découpe un nom machine en dict d'identification ('' = inconnu). Grammaire : voir l'en-tête."""
    ident = dict.fromkeys(IDENT_COLS, "")
    s = name
    if s.count("/") == 1:
        s = s.split("/", 1)[1]
    if "_" in s:
        base, suffix = s.rsplit("_", 1)
        sfx = suffix.lower()
        if sfx in EFFORTS:
            s, ident["reasoning_level"] = base, sfx
        elif sfx == "unknown":
            s, ident["variant"] = base, "unknown-effort"
        elif _BUDGET.fullmatch(sfx):
            s, ident["reasoning_tokens"] = base, str(int(sfx[:-1]) * 1000)
        elif sfx == "thinking":
            s, ident["variant"] = base, "thinking"
    m = _DATE_ISO.search(s) or _DATE_8.search(s)
    if m:
        s = s[: m.start()]
        ident["snapshot"] = "-".join(m.groups())
    ident["base_model"] = s
    return ident


def load_aliases(path):
    """aliases.csv -> {raw_name: dict IDENT_COLS}. base_model vide = DROP (dict quand même retourné)."""
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if rows and list(rows[0]) != ALIAS_COLS:
        raise ValueError(f"{path}: colonnes {list(rows[0])} != {ALIAS_COLS}")
    return {r["raw_name"]: {c: r[c].strip() for c in IDENT_COLS} for r in rows}


def resolve_model(raw, aliases, decoupable):
    """-> ('ok', ident) | ('drop', None) | ('unmapped', None).

    Ordre : aliases.csv de la source d'abord ; sinon découpe du nom machine (split_name)
    si la source s'y prête ; sinon non-résolu (signalé, jamais deviné).
    """
    name = strip_name(raw)
    if not name:
        return "unmapped", None
    if name in aliases:
        ident = aliases[name]
        return ("drop", None) if not ident["base_model"] else ("ok", ident)
    if decoupable:
        return "ok", split_name(name)
    return "unmapped", None


def model_id(ident):
    return str(uuid.uuid5(NAMESPACE, "model|" + "|".join(ident[c] for c in IDENT_COLS)))


def benchmark_id(name):
    return str(uuid.uuid5(NAMESPACE, "benchmark|" + name))


def seal_entries(html):
    """Page SEAL -> liste d'entrées {model, score, ...}, ou [].

    Les données vivent dans les chunks Next.js (`self.__next_f.push([...])`) ; le <table>
    visible est un snapshot périmé. json.loads par chunk gère les échappements \\uXXXX
    ET préserve l'UTF-8 littéral (unicode_escape le mangerait en mojibake). On garde
    le plus grand tableau `"entries":[...]` dont les items ont une clé `model`.
    """
    decoded = []
    for chunk in re.findall(r'self\.__next_f\.push\(\[\d+,\s*"((?:[^"\\]|\\.)*)"\]\)', html):
        try:
            decoded.append(json.loads('"' + chunk + '"'))
        except ValueError:
            decoded.append(chunk.encode("latin-1", "backslashreplace").decode("unicode_escape", "replace"))
    decoded = "".join(decoded)

    arrays = []
    for m in re.finditer(r'"entries"\s*:\s*\[', decoded):
        start = m.end() - 1
        depth, i = 0, start
        while i < len(decoded):
            if decoded[i] == "[":
                depth += 1
            elif decoded[i] == "]":
                depth -= 1
                if depth == 0:
                    break
            i += 1
        try:
            arr = json.loads(decoded[start:i + 1])
        except ValueError:
            continue
        if arr and isinstance(arr[0], dict) and "model" in arr[0]:
            arrays.append(arr)
    return max(arrays, key=len) if arrays else []


def dedup(scores, kaggle_win_ids=frozenset()):
    """-> (scores dédupliqués, rapport des désaccords, nb de doublons exacts).

    Passe 1 : doublons exacts sur (model_id, benchmark_id, score arrondi à 1e-9) —
    l'arrondi est porteur : 2.502/100 (SEAL) != 0.02502 (ZIP) au dernier bit.
    Passe 2 : désaccords résiduels -> la ligne kaggle gagne si le benchmark est dans
    kaggle_win_ids, sinon le score max.
    """
    key = ["model_id", "benchmark_id"]
    d = scores.assign(_k=scores["score"].round(9))
    n_exact = int(d.duplicated(key + ["_k"]).sum())
    d = d.drop_duplicates(key + ["_k"]).drop(columns="_k")

    report = (d.groupby(key)
               .agg(n=("score", "size"), score_min=("score", "min"), score_max=("score", "max"),
                    feeds=("feed", lambda s: ", ".join(sorted(set(s)))))
               .reset_index()
               .query("n > 1")
               .assign(spread=lambda r: r["score_max"] - r["score_min"])
               .sort_values(["spread", "model_id"], ascending=[False, True]))

    prio = ((d["feed"] == "kaggle") & d["benchmark_id"].isin(kaggle_win_ids)).astype(int)
    d = (d.assign(_p=prio)
          .sort_values(["_p", "score"], na_position="first")
          .drop_duplicates(key, keep="last")
          .drop(columns="_p"))
    return d, report, n_exact


def report_leftovers(label, meta_orphans, targets_without):
    """Les deux restes d'une jointure de métadonnées, imprimés pareil partout."""
    print(f"{label}: {len(meta_orphans)} ligne(s) meta sans cible, "
          f"{len(targets_without)} cible(s) sans meta")
    for x in sorted(meta_orphans)[:8]:
        print(f"    meta orpheline : {x}")
    for x in sorted(targets_without)[:8]:
        print(f"    sans meta      : {x}")


def write_aliases(path, rows):
    """Écrit une liste de dicts ALIAS_COLS, triée par raw_name."""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=ALIAS_COLS)
        w.writeheader()
        w.writerows(sorted(rows, key=lambda r: r["raw_name"].lower()))
