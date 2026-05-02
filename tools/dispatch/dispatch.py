"""
dispatch.py — emit a structured sub-agent dispatch prompt.

Turns the orchestrator's structured inputs into a fully-shaped
dispatch text with every required slot filled. Refuses to emit
if a required slot is missing or empty.

The required slots (`--churn`, `--task`) close the variance
surface between "rules the orchestrator should remember" and
"rules the orchestrator actually applied." Required-by-script
beats required-by-discipline.

Usage:

    python3 dispatch.py \\
        --task "Refactor X to use Y" \\
        --churn "Z just landed; W docs not yet swept" \\
        --files "path/to/file1.py,path/to/file2.py" \\
        --conformance

Emits the dispatch text to stdout. Pipe into the Agent prompt.
"""

import argparse
import sys

from dispatch_dsl import (
    DISPATCH_SECTIONS,
    DISPATCH_REQUIRED,
    REPORT_BACK_TEMPLATE,
    CONFORMANCE_TEMPLATE,
    BASH_DISCIPLINE_TEMPLATE,
    READ_ONLY_TEMPLATE,
)


def compose_dispatch(*, task, churn, files=None, conformance=False, read_only=False):
    """Compose a dispatch prompt from structured inputs.

    Raises ValueError if any required slot is empty, or if mutually-
    exclusive flags are set together.
    """
    inputs = {"task": task, "churn": churn}
    missing = [k for k in DISPATCH_REQUIRED if not inputs.get(k, "").strip()]
    if missing:
        raise ValueError(f"missing required slot(s): {', '.join(sorted(missing))}")

    if read_only and conformance:
        raise ValueError(
            "--read-only and --conformance are mutually exclusive: a read-only "
            "task does not modify code, so there's nothing for conformance to verify."
        )

    blocks = []

    blocks.append(DISPATCH_SECTIONS["churn"])
    blocks.append(churn.strip())
    blocks.append("")

    blocks.append(DISPATCH_SECTIONS["task"])
    blocks.append(task.strip())
    blocks.append("")

    if files:
        blocks.append(DISPATCH_SECTIONS["files"])
        for f in files:
            blocks.append(f"- {f}")
        blocks.append("")

    if conformance:
        blocks.append(DISPATCH_SECTIONS["conformance"])
        blocks.append(CONFORMANCE_TEMPLATE)
        blocks.append("")

    if read_only:
        blocks.append(DISPATCH_SECTIONS["read_only"])
        blocks.append(READ_ONLY_TEMPLATE)
        blocks.append("")

    blocks.append(DISPATCH_SECTIONS["bash_discipline"])
    blocks.append(BASH_DISCIPLINE_TEMPLATE)
    blocks.append("")

    blocks.append(DISPATCH_SECTIONS["report_back"])
    blocks.append(REPORT_BACK_TEMPLATE)

    return "\n".join(blocks)


def main():
    parser = argparse.ArgumentParser(
        description="Emit a structured sub-agent dispatch prompt with required-slot enforcement.",
    )
    parser.add_argument("--task", required=True, help="The task brief.")
    parser.add_argument(
        "--churn", required=True,
        help="1-3 sentences naming what recently landed / what got ripped / "
             "what the agent should treat as moving ground.",
    )
    parser.add_argument(
        "--files", default="",
        help="Comma-separated list of files in scope (optional).",
    )
    parser.add_argument(
        "--conformance", action="store_true",
        help="Require the agent to run ops/check-conformance and report.",
    )
    parser.add_argument(
        "--read-only", action="store_true",
        help="Mark the task as read-only (no edits permitted). Mutually "
             "exclusive with --conformance.",
    )
    args = parser.parse_args()

    files = [f.strip() for f in args.files.split(",") if f.strip()] if args.files else None

    try:
        out = compose_dispatch(
            task=args.task,
            churn=args.churn,
            files=files,
            conformance=args.conformance,
            read_only=args.read_only,
        )
    except ValueError as e:
        print(f"dispatch.py: {e}", file=sys.stderr)
        sys.exit(2)

    print(out)


if __name__ == "__main__":
    main()
