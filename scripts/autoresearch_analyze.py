"""Frontier viewer for results.tsv (analogue of karpathy's analysis.ipynb)."""

from __future__ import annotations

import csv
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS_TSV = ROOT / "results.tsv"


def main() -> None:
    if not RESULTS_TSV.exists():
        print("no results.tsv yet; run autoresearch_iter.py first")
        return
    rows = list(csv.DictReader(RESULTS_TSV.open(encoding="utf-8"), delimiter="\t"))
    if not rows:
        print("results.tsv has no rows")
        return

    print(f"total experiments: {len(rows)}")
    counts = {"keep": 0, "discard": 0, "crash": 0, "pending": 0}
    for r in rows:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    decided = counts["keep"] + counts["discard"]
    keep_rate = counts["keep"] / decided if decided else 0.0
    print(f"  outcomes: {counts}")
    print(f"  keep-rate (excluding crashes/pending): {keep_rate:.1%}")

    print("\nfrontier (cumulative best mean_judge over KEEP rows):")
    best = -math.inf
    for r in rows:
        if r["status"].lower() != "keep":
            continue
        try:
            mj = float(r["mean_judge"])
        except ValueError:
            continue
        if mj > best:
            best = mj
            marker = "↑"
        else:
            marker = " "
        print(f"  {marker} {r['commit']}  judge={mj:.4f}  best={best:.4f}  {r['description']}")


if __name__ == "__main__":
    main()
