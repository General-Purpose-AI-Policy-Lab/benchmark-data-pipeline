"""Feed `seal`: Scale SEAL leaderboards, one captured HTML page per board.

The pages are not redistributed (upstream license, see NOTICE.md): `refresh` fetches them.
"""

import json
import logging
import re
from collections.abc import Iterator
from pathlib import Path

from benchmark_data.sources.record import Record

log = logging.getLogger(__name__)

# Dictionary: board slug -> benchmark. Scores on 0-100, no published stderr.
# rli is ALSO in the Epoch ZIP: a deliberate partial overlap, dedup settles it.
SEAL_SPEC = {
    'audiomc':                       'AudioMultiChallenge',
    'drugdiscoverybench':            'DrugDiscoveryBench',
    'hil':                           'HiL-Bench',
    'hle-diamond':                   'HLE Diamond',
    'instruction_following':         'SEAL Instruction Following',
    'mcp_atlas':                     'MCP Atlas',
    'multichallenge':                'MultiChallenge',
    'multinrc':                      'MultiNRC',
    'prbench-finance':               'PRBench Finance',
    'prbench-legal':                 'PRBench Legal',
    'rli':                           'Remote Labor Index',
    'swe_bench_pro_private':         'SWE-Bench Pro (Private)',
    'swe_bench_pro_public':          'SWE-Bench Pro',
    'swe_bench_pro_public_v2':       'SWE-Bench Pro V2',
    'sweatlas-qna':                  'SWE Atlas Codebase QnA',
    'sweatlas-refactoring':          'SWE Atlas Refactoring',
    'sweatlas-tw':                   'SWE Atlas Test Writing',
    'tool_use_enterprise':           'SEAL Tool Use (Enterprise)',
    'tutorbench':                    'TutorBench',
    'visual_language_understanding': 'Visual Task Assessment (VISTA)',
    'vtb':                           'VisualToolBench',
}

# Boards whose page holds several tables: the `label` of the table to read, or of the tables whose
# rows together are the board. Elsewhere the largest `entries` array is the board (and a page that
# shows several labelled tables without an entry here is reported).
# SWE-Bench Pro V2 shows a Full table and a HARD one; HARD is the board Scale ranks on and the one
# with more models (user, 2026-09-30); Scale shortened the labels to "Full" / "HARD" in November
# 2026. AudioMultiChallenge was one table of text-output (`*`) and audio-output (`†`) rows until
# Scale split it into two tables the same month: the board stays their union (decision of
# 2026-10-01: "the union of its two sub-boards").
SEAL_TABLE = {
    'swe_bench_pro_public_v2':       'HARD',
    'audiomc':                       ('Text Output', 'Audio Output'),
    # MultiChallenge: a table of large models and one of small models, read together since
    # 2026-11-17 (user); before, only the larger table was taken.
    'multichallenge':                ('Large', 'Small'),
    # Both SWE-Bench Pro pages carry the Public and the Private table (benchmarks excluded today).
    'swe_bench_pro_public':          'Public',
    'swe_bench_pro_private':         'Private',
}

# Boards set aside, with the reason.
SEAL_SKIP = {
    'arabic':                        'multilingual Elo score, not a proportion in [0, 1]',
    'chinese':                       'multilingual Elo score, not a proportion in [0, 1]',
    'coding':                        'Elo score (~600-1240), not a proportion in [0, 1]',
    'humanitys_last_exam_text_only': 'text-only subset of HLE, which is itself replaced by HLE Diamond (2026-09-30)',
    'japanese':                      'multilingual Elo score, not a proportion in [0, 1]',
    'spanish':                       'multilingual Elo score, not a proportion in [0, 1]',
}

if set(SEAL_SPEC) & set(SEAL_SKIP):
    raise ValueError("board in both SEAL_SPEC and SEAL_SKIP")

_SCORE_SCALE = 100  # scores are published on 100
BOARD_URL = "https://labs.scale.com/leaderboard/{}"


def _page_text(html: str) -> str:
    """The page's data: the Next.js streaming chunks, decoded and joined."""
    decoded = []
    for chunk in re.findall(r'self\.__next_f\.push\(\[\d+,\s*"((?:[^"\\]|\\.)*)"\]\)', html):
        try:
            decoded.append(json.loads('"' + chunk + '"'))
        except ValueError:
            decoded.append(chunk.encode("latin-1", "backslashreplace").decode("unicode_escape", "replace"))
    return "".join(decoded)


def table_labels(html: str) -> list[str]:
    """The labels of the page's labelled tables (`{"key": ..., "label": ..., "entries": [...]}`),
    in page order: more than one means the board is split into variants."""
    return re.findall(r'"label"\s*:\s*("(?:[^"\\]|\\.)*")\s*,\s*"entries"\s*:\s*\[\s*\{\s*"model"',
                      _page_text(html))


def seal_entries(html: str, label: str | tuple[str, ...] | None = None) -> list[dict]:
    """SEAL page -> list of {model, score, ...} entries, or [].

    The data lives in the Next.js streaming chunks (`self.__next_f.push([...])`); the visible
    <table> is a stale snapshot. json.loads per chunk handles the \\uXXXX escapes AND keeps
    literal UTF-8 (unicode_escape would mangle it into mojibake). The largest `"entries":[...]`
    array whose items have a `model` key is kept, or, with `label`, the array of the table carrying
    that label (`{"key": ..., "label": ..., "entries": [...]}`); [] when no table has it. A tuple
    of labels gives the rows of those tables together, [] as soon as one of them is missing.
    """
    if isinstance(label, tuple):
        parts = [seal_entries(html, one) for one in label]
        return [e for part in parts for e in part] if all(parts) else []
    text = _page_text(html)

    arrays = []
    labelled = []
    for m in re.finditer(r'"entries"\s*:\s*\[', text):
        start = m.end() - 1
        depth, i = 0, start
        while i < len(text):
            if text[i] == "[":
                depth += 1
            elif text[i] == "]":
                depth -= 1
                if depth == 0:
                    break
            i += 1
        try:
            arr = json.loads(text[start:i + 1])
        except ValueError:
            continue
        if arr and isinstance(arr[0], dict) and "model" in arr[0]:
            arrays.append(arr)
            if label is not None and re.search(r'"label"\s*:\s*' + re.escape(json.dumps(label))
                                               + r'\s*,\s*$', text[max(0, m.start() - 200):m.start()]):
                labelled.append(arr)
    if label is not None:
        return max(labelled, key=len) if labelled else []
    return max(arrays, key=len) if arrays else []


def translate(feed_dir: Path) -> Iterator[Record]:
    """One board = one benchmark. The harness, when a name embeds one, comes from aliases.csv.

    Raises:
        FileNotFoundError: no captured HTML page (fresh clone without `refresh`).
    """
    pages = sorted((feed_dir / "seal").glob("*.html"))
    if not pages:
        raise FileNotFoundError(
            "0_input/feed/seal/ holds no HTML page. Scale SEAL pages are not redistributed with "
            "the repository (see NOTICE.md): run `python -m benchmark_data refresh` first.")
    for path in pages:
        if path.stem in SEAL_SKIP:
            continue
        if path.stem not in SEAL_SPEC:
            log.warning("seal: ? %s: in neither SEAL_SPEC nor SEAL_SKIP", path.name)
            continue
        html = path.read_text()
        entries = seal_entries(html, SEAL_TABLE.get(path.stem))
        if not entries:
            log.warning("seal: ! %s: no `entries` array in the page%s", path.name,
                        f" for the table(s) {SEAL_TABLE[path.stem]!r}; the page has "
                        f"{[json.loads(x) for x in table_labels(html)]}"
                        if path.stem in SEAL_TABLE else "")
            continue
        if path.stem not in SEAL_TABLE and len(labels := table_labels(html)) > 1:
            log.warning("seal: ! %s: the page shows several tables %s and only the largest is "
                        "read; name the one(s) to read in SEAL_TABLE", path.name,
                        [json.loads(x) for x in labels])
        for e in entries:
            if isinstance(e.get("score"), (int, float)):
                yield Record(e["model"], SEAL_SPEC[path.stem], e["score"] / _SCORE_SCALE, "", "", "",
                             {}, f"Scale SEAL ({path.stem})", BOARD_URL.format(path.stem))
