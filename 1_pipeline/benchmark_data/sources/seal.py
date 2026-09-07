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
    'instruction_following':         'SEAL Instruction Following',
    'mcp_atlas':                     'MCP Atlas',
    'multichallenge':                'MultiChallenge',
    'multinrc':                      'MultiNRC',
    'prbench-finance':               'PRBench Finance',
    'prbench-legal':                 'PRBench Legal',
    'rli':                           'Remote Labor Index',
    'swe_bench_pro_private':         'SWE-Bench Pro (Private)',
    'swe_bench_pro_public':          'SWE-Bench Pro',
    'sweatlas-qna':                  'SWE Atlas Codebase QnA',
    'sweatlas-refactoring':          'SWE Atlas Refactoring',
    'sweatlas-tw':                   'SWE Atlas Test Writing',
    'tool_use_enterprise':           'SEAL Tool Use (Enterprise)',
    'tutorbench':                    'TutorBench',
    'visual_language_understanding': 'Visual Task Assessment (VISTA)',
    'vtb':                           'VisualToolBench',
}

# Boards set aside, with the reason.
SEAL_SKIP = {
    'arabic':                        'multilingual Elo score, not a proportion in [0, 1]',
    'chinese':                       'multilingual Elo score, not a proportion in [0, 1]',
    'coding':                        'Elo score (~600-1240), not a proportion in [0, 1]',
    'humanitys_last_exam_text_only': 'text-only subset; not comparable to the full HLE ingested from Epoch',
    'japanese':                      'multilingual Elo score, not a proportion in [0, 1]',
    'spanish':                       'multilingual Elo score, not a proportion in [0, 1]',
}

if set(SEAL_SPEC) & set(SEAL_SKIP):
    raise ValueError("board in both SEAL_SPEC and SEAL_SKIP")

_SCORE_SCALE = 100  # scores are published on 100
BOARD_URL = "https://labs.scale.com/leaderboard/{}"


def seal_entries(html: str) -> list[dict]:
    """SEAL page -> list of {model, score, ...} entries, or [].

    The data lives in the Next.js streaming chunks (`self.__next_f.push([...])`); the visible
    <table> is a stale snapshot. json.loads per chunk handles the \\uXXXX escapes AND keeps
    literal UTF-8 (unicode_escape would mangle it into mojibake). The largest `"entries":[...]`
    array whose items have a `model` key is kept.
    """
    decoded = []
    for chunk in re.findall(r'self\.__next_f\.push\(\[\d+,\s*"((?:[^"\\]|\\.)*)"\]\)', html):
        try:
            decoded.append(json.loads('"' + chunk + '"'))
        except ValueError:
            decoded.append(chunk.encode("latin-1", "backslashreplace").decode("unicode_escape", "replace"))
    text = "".join(decoded)

    arrays = []
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
        entries = seal_entries(path.read_text())
        if not entries:
            log.warning("seal: ! %s: no `entries` array in the page", path.name)
            continue
        for e in entries:
            if isinstance(e.get("score"), (int, float)):
                yield Record(e["model"], SEAL_SPEC[path.stem], e["score"] / _SCORE_SCALE, "", "", "",
                             {}, f"Scale SEAL ({path.stem})", BOARD_URL.format(path.stem))
