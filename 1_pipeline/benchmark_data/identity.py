"""Model identity: machine-name grammar, per-source aliases, uuid5 identifiers.

A model is identified by the tuple (base_model, reasoning_level, reasoning_tokens, snapshot,
variant). Convention: '' = unknown. Two unknowns never merge with a known value: opus-5
(level='') and opus-5_high (level='high') are two distinct models.

The harness (scaffold, agent framework) is NOT part of the identity: a model's score on a
benchmark is its best score across harnesses, and the harness that produced it travels with the
score. Aliases may still carry a harness, for sources whose composite names embed one.

"Machine name" = the machine-readable format used by Epoch and Kaggle, e.g. claude-opus-4-8_high
or zai-org/glm-4.7. Its shape is fixed, [provider/]base[-date][_suffix], so it is split into
columns without a dictionary (split_name):
- '_' introduces a configuration knob, '-' is part of the name (kimi-k2-thinking is a NAME).
- suffix (case-insensitive): effort minimal|low|medium|high|xhigh|max|none; budget <N>K;
  thinking -> variant='thinking'; unknown -> dropped (Epoch's "effort unknown" and a bare name
  are the same state of knowledge, one identity; user decision 2026-09-09); pro<effort> ->
  variant='pro' plus the effort (gpt-5.6-sol_promax). A suffix outside the vocabulary is part
  of the name.
- the date is extracted only in the YYYY-MM-DD / YYYYMMDD forms at the end of the base (short
  forms such as 2507, 0528, 03-2025 stay in base_model, on purpose: too ambiguous).
"""

import csv
import re
import uuid
from pathlib import Path

IDENT_COLS = ["base_model", "reasoning_level", "reasoning_tokens", "snapshot", "variant"]
ALIAS_COLS = ["raw_name", *IDENT_COLS, "harness", "note"]
NAMESPACE = uuid.uuid5(uuid.NAMESPACE_DNS, "benchmark-data-pipeline")

EFFORTS = frozenset({"minimal", "low", "medium", "high", "xhigh", "max", "none"})
_BUDGET = re.compile(r"(\d+)k")
_DATE_ISO = re.compile(r"-(\d{4})-(\d{2})-(\d{2})$")
_DATE_8 = re.compile(r"-(20\d{2})(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])$")

Identity = dict[str, str]


def strip_name(raw) -> str:
    """Mechanical cleanup: trailing footnote markers (*, †, superscript digits) and whitespace."""
    return re.sub(r"[\s*†⁰¹²³⁴⁵⁶⁷⁸⁹]+$", "", str(raw)).strip()


def normalize(ident: Identity) -> Identity:
    """Apply the convention: a known effort or token budget makes `thinking` implicit.

    `variant='thinking'` only says "thinking on, effort and budget unknown"; once either is known
    it carries no information and would split one model into two identities.
    """
    if ident["variant"] == "thinking" and (ident["reasoning_level"] or ident["reasoning_tokens"]):
        return {**ident, "variant": ""}
    return ident


def split_name(name: str) -> Identity:
    """Split a machine name into an identity dict ('' = unknown). Grammar: module docstring."""
    ident = dict.fromkeys(IDENT_COLS, "")
    s = name
    if s.count("/") == 1:
        s = s.split("/", 1)[1]
    if "_" in s:
        base, suffix = s.rsplit("_", 1)
        sfx = suffix.lower()
        if sfx.startswith("pro") and (sfx[3:] in EFFORTS or sfx[3:] == "unknown"):
            # Epoch writes the pro variant glued to the effort: gpt-5.6-sol_promax, _prounknown.
            s, ident["variant"] = base, "pro"
            if sfx[3:] in EFFORTS:
                ident["reasoning_level"] = sfx[3:]
        elif sfx in EFFORTS:
            s, ident["reasoning_level"] = base, sfx
        elif sfx == "unknown":
            s = base                       # same identity as the bare name
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


def load_aliases(path: Path) -> dict[str, dict[str, str]]:
    """aliases.csv -> {raw_name: {*IDENT_COLS, harness}}. Empty base_model = DROP (still returned).

    Raises:
        ValueError: unexpected header, or duplicated raw_name (the last row would silently
            overwrite the earlier ones).
    """
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        # fieldnames rather than rows[0]: a header-only file (what the README asks for when a
        # source is added) must be validated too.
        if reader.fieldnames != ALIAS_COLS:
            raise ValueError(f"{path}: columns {reader.fieldnames} != {ALIAS_COLS}")
        rows = list(reader)
    seen = [r["raw_name"] for r in rows]
    dupes = sorted({n for n in seen if seen.count(n) > 1})
    if dupes:
        raise ValueError(f"{path}: duplicated raw_name: {dupes}")
    return {r["raw_name"]: {c: r[c].strip() for c in [*IDENT_COLS, "harness"]} for r in rows}


def resolve_model(raw, aliases: dict[str, dict[str, str]], splittable: bool):
    """-> ('ok', ident, harness) | ('drop', None, '') | ('unmapped', None, '').

    Order: the source's aliases.csv first; otherwise the machine-name grammar (split_name) when
    the source follows it; otherwise unresolved (reported, never guessed).
    """
    name = strip_name(raw)
    if not name:
        return "unmapped", None, ""
    if name in aliases:
        entry = aliases[name]
        if not entry["base_model"]:
            return "drop", None, ""
        return "ok", normalize({c: entry[c] for c in IDENT_COLS}), entry["harness"]
    if splittable:
        return "ok", split_name(name), ""
    return "unmapped", None, ""


def machine_name(ident: Identity) -> str:
    """Inverse of split_name: an Epoch-style machine name for an identity.

    The snapshot is rendered the way the developer writes it: 8 digits for Anthropic
    (`claude-opus-4-20250514`), ISO otherwise (`gpt-4o-2024-08-06`). Used only for models no
    Epoch or Kaggle file names directly; otherwise the observed spelling wins (see
    `steps.enrich.add_model_version`).
    """
    name = ident["base_model"]
    if ident["snapshot"]:
        snap = ident["snapshot"]
        name += "-" + (snap.replace("-", "") if name.startswith("claude") else snap)
    if ident["variant"] == "pro":
        name += "_pro" + (ident["reasoning_level"] or "unknown")
    elif ident["reasoning_level"]:
        name += "_" + ident["reasoning_level"]
    elif ident["reasoning_tokens"]:
        name += f"_{int(ident['reasoning_tokens']) // 1000}K"
    elif ident["variant"] == "thinking":
        name += "_thinking"
    return name


def model_id(ident: Identity) -> str:
    return str(uuid.uuid5(NAMESPACE, "model|" + "|".join(ident[c] for c in IDENT_COLS)))


def benchmark_id(name: str) -> str:
    return str(uuid.uuid5(NAMESPACE, "benchmark|" + name))
