"""Single auto-research experiment for the PPT harness.

Karpathy/autoresearch analogue: this is the **fixed-budget runner** the agent
calls between edits. It:

1. Runs the full LangGraph pipeline on every topic in a pinned eval set.
2. Scores each deck with both the structural ``score_deck`` and the richer
   ``judge_deck`` (the latter is the metric the agent optimises).
3. Appends one row to ``results.tsv`` (commit, mean_judge, mean_evals,
   per-topic breakdown, status placeholder, description).

The agent edits the **policy surface** (``policy.yaml``) — analogous to
``train.py`` in karpathy/autoresearch. ``prepare.py``-equivalents (the
pipeline, eval set, judge) are read-only.

Usage:
    python scripts/autoresearch_iter.py --desc "tighten designer audience prompt"
"""

from __future__ import annotations

import argparse
import json
import statistics
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from autoresearch.evals import score_deck  # noqa: E402
from autoresearch.graph import build_pipeline  # noqa: E402
from autoresearch.judge import judge_deck  # noqa: E402
from autoresearch.seeds import upgraded_client  # noqa: E402

# Pinned eval set — like karpathy's pinned val shard.
EVAL_TOPICS: list[tuple[str, str]] = [
    ("Anti-bribery for procurement partners", "External procurement partners"),
    ("Data protection (GDPR) for partners", "Channel resellers in the EU"),
]

RESULTS_TSV = ROOT / "results.tsv"
HEADER = "commit\tmean_judge\tmean_evals\tper_topic_judge\tstatus\tdescription\n"


def _git_short_sha() -> str:
    try:
        out = subprocess.check_output(
            ["git", "-C", str(ROOT), "rev-parse", "--short=7", "HEAD"],
            stderr=subprocess.DEVNULL,
        )
        return out.decode().strip()
    except Exception:
        return "nogit00"


def run_one(topic: str, audience: str) -> tuple[float, float]:
    client, search = upgraded_client(topic, audience)
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "deck.pptx"
        graph = build_pipeline(client=client, out_path=out, search=search)
        final = graph.invoke({"topic": topic, "audience": audience})
    plan = final["deck_plan"]
    return judge_deck(plan).total, score_deck(plan).total


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--desc", required=True, help="one-line experiment description")
    ap.add_argument(
        "--status",
        default="pending",
        choices=["pending", "keep", "discard", "crash"],
        help="leave 'pending' here; the agent decides keep/discard after comparison",
    )
    args = ap.parse_args()

    if not RESULTS_TSV.exists():
        RESULTS_TSV.write_text(HEADER, encoding="utf-8")

    per_topic_judge: dict[str, float] = {}
    per_topic_evals: dict[str, float] = {}
    try:
        for topic, audience in EVAL_TOPICS:
            j, e = run_one(topic, audience)
            per_topic_judge[topic] = j
            per_topic_evals[topic] = e
        mean_judge = statistics.mean(per_topic_judge.values())
        mean_evals = statistics.mean(per_topic_evals.values())
        status = args.status
    except Exception as exc:  # noqa: BLE001
        print(f"[crash] {exc!r}", file=sys.stderr)
        per_topic_judge = {}
        mean_judge = 0.0
        mean_evals = 0.0
        status = "crash"

    sha = _git_short_sha()
    row = "\t".join(
        [
            sha,
            f"{mean_judge:.6f}",
            f"{mean_evals:.6f}",
            json.dumps(per_topic_judge),
            status,
            args.desc.replace("\t", " ").replace("\n", " "),
        ]
    )
    with RESULTS_TSV.open("a", encoding="utf-8") as f:
        f.write(row + "\n")

    print("---")
    print(f"commit:        {sha}")
    print(f"mean_judge:    {mean_judge:.4f}   (higher is better; ceiling 1.0)")
    print(f"mean_evals:    {mean_evals:.4f}   (existing structural rubric)")
    for t, v in per_topic_judge.items():
        print(f"  · {t[:50]:<50}  judge={v:.4f}")
    print(f"status:        {status}")
    print(f"description:   {args.desc}")


if __name__ == "__main__":
    main()
