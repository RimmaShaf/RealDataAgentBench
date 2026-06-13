"""Regenerate the embedded INLINE_SUMMARY / INLINE_RUNS arrays in docs/index.html
from the canonical docs/results.json.

index.html embeds a copy of the leaderboard data so the top sections render with
zero network latency, then overlays the freshly-fetched results.json on load.
Those two embedded arrays were previously kept in sync by hand (see the "Keep in
sync" comments) — this script removes that drift risk:

    python scripts/sync_inline_leaderboard.py        # rewrite in place
    python scripts/sync_inline_leaderboard.py --check # exit 1 if out of sync (CI)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
RESULTS = ROOT / "docs" / "results.json"
INDEX = ROOT / "docs" / "index.html"

_SUMMARY_RE = re.compile(r"const INLINE_SUMMARY = \[.*?\n  \];", re.DOTALL)
_RUNS_RE = re.compile(r"const INLINE_RUNS = \[.*?\];", re.DOTALL)


def _render(data: dict) -> tuple[str, str]:
    summary = data["model_summary"]
    runs = data["runs"]
    summary_block = (
        "const INLINE_SUMMARY = [\n"
        + ",\n".join("    " + json.dumps(r, separators=(",", ":")) for r in summary)
        + "\n  ];"
    )
    runs_block = "const INLINE_RUNS = " + json.dumps(runs, separators=(",", ":")) + ";"
    return summary_block, runs_block


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="exit 1 if out of sync")
    args = ap.parse_args()

    data = json.loads(RESULTS.read_text())
    html = INDEX.read_text()
    summary_block, runs_block = _render(data)

    if not _SUMMARY_RE.search(html) or not _RUNS_RE.search(html):
        sys.exit("ERROR: could not locate INLINE_SUMMARY / INLINE_RUNS markers in index.html")

    new_html = _SUMMARY_RE.sub(lambda _: summary_block, html)
    new_html = _RUNS_RE.sub(lambda _: runs_block, new_html)

    if args.check:
        if new_html != html:
            sys.exit("index.html INLINE_* arrays are out of sync with results.json — "
                     "run: python scripts/sync_inline_leaderboard.py")
        print("index.html inline data is in sync with results.json.")
        return

    if new_html == html:
        print("Already in sync — no change.")
        return
    INDEX.write_text(new_html)
    print(f"Synced index.html from results.json: "
          f"{len(data['model_summary'])} models, {len(data['runs'])} runs.")


if __name__ == "__main__":
    main()
