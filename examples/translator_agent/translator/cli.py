"""CLI: `python -m translator "Hello, world."`"""

from __future__ import annotations

import argparse
import json
import sys

from .llm import has_api_keys
from .pipeline import translate


def main() -> int:
    p = argparse.ArgumentParser(prog="translator")
    p.add_argument("text", help="English source text")
    p.add_argument("--no-reflection", action="store_true",
                   help="Skip the reflect+edit step (single-shot baseline)")
    p.add_argument("--trace", action="store_true",
                   help="Print the full trace (draft, findings, final) as JSON")
    args = p.parse_args()

    if not has_api_keys():
        print(
            "warning: OPENAI_API_KEY and/or ANTHROPIC_API_KEY not set — "
            "real translation will fail. Use the demo script for the "
            "FakeLLM walkthrough.",
            file=sys.stderr,
        )

    trace = translate(args.text, skip_reflection=args.no_reflection)

    if args.trace:
        print(json.dumps({
            "source_en": trace.source_en,
            "draft_ko": trace.draft_ko,
            "findings": [f.__dict__ for f in trace.findings],
            "final_ko": trace.final_ko,
            "edited": trace.edited,
        }, ensure_ascii=False, indent=2))
    else:
        print(trace.final_ko)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
