"""
dispatch.py — emit a structured sub-agent dispatch prompt.

Turns the orchestrator's structured inputs into a fully-shaped
dispatch text with every required slot filled. Refuses to emit
if a required slot is missing or empty.

The required slots (`--churn`, `--task`) close the variance
surface between "rules the orchestrator should remember" and
"rules the orchestrator actually applied." Required-by-script
beats required-by-discipline.

See `python3 dispatch.py --help` for the flag list and
README.md for worked examples.
"""

import argparse
import sys

from dispatch_dsl import (
    DISPATCH_SECTIONS,
    DISPATCH_REQUIRED,
    REPORT_BACK_TEMPLATES,
    CONFORMANCE_TEMPLATE,
    DOC_UPKEEP_TEMPLATE,
    CODE_OWNERSHIP_TEMPLATE,
    BASH_DISCIPLINE_TEMPLATE,
    READ_ONLY_TEMPLATE,
    MODES,
    DEFAULT_MODE,
)


def compose_dispatch(*, task, churn="", files=None, conformance=False, read_only=False, mode=DEFAULT_MODE):
    """Compose a dispatch prompt from structured inputs.

    Raises ValueError if any required slot is empty, if mode is unknown,
    or if mutually-exclusive flags are set together. `churn` is optional;
    omit it (or pass empty) when no recent change directly affects the
    task — the section is only emitted when truthy.
    """
    inputs = {"task": task, "churn": churn}
    missing = [k for k in DISPATCH_REQUIRED if not inputs.get(k, "").strip()]
    if missing:
        raise ValueError(f"missing required slot(s): {', '.join(sorted(missing))}")

    if mode not in MODES:
        raise ValueError(f"unknown mode {mode!r}; valid: {', '.join(MODES)}")

    # Survey mode is read-only by definition: discovery work doesn't edit.
    if mode == "survey":
        if conformance:
            raise ValueError(
                "--conformance is not valid with --mode survey: surveys are "
                "read-only by definition, so there's nothing for conformance to verify."
            )
        read_only = True

    if read_only and conformance:
        raise ValueError(
            "--read-only and --conformance are mutually exclusive: a read-only "
            "task does not modify code, so there's nothing for conformance to verify."
        )

    if conformance and mode != "build":
        raise ValueError(
            f"--conformance requires --mode build; mode {mode!r} has no Validation field."
        )

    blocks = []

    if churn.strip():
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

    # Doc upkeep applies whenever the agent will be editing code (build
    # mode, not read-only). Critique and survey are read-only deliverables;
    # there's nothing to drift.
    if mode == "build" and not read_only:
        blocks.append(DISPATCH_SECTIONS["doc_upkeep"])
        blocks.append(DOC_UPKEEP_TEMPLATE)
        blocks.append("")

    # Code ownership: same gate as doc_upkeep — only meaningful when the
    # agent will be writing code. The principle is "default to exporting
    # privates, not inlining copies" — surfaces a sub-agent reflex that
    # produces drift if left implicit.
    if mode == "build" and not read_only:
        blocks.append(DISPATCH_SECTIONS["code_ownership"])
        blocks.append(CODE_OWNERSHIP_TEMPLATE)
        blocks.append("")

    if read_only:
        blocks.append(DISPATCH_SECTIONS["read_only"])
        blocks.append(READ_ONLY_TEMPLATE)
        blocks.append("")

    blocks.append(DISPATCH_SECTIONS["bash_discipline"])
    blocks.append(BASH_DISCIPLINE_TEMPLATE)
    blocks.append("")

    blocks.append(DISPATCH_SECTIONS["report_back"])
    blocks.append(REPORT_BACK_TEMPLATES[mode])

    return "\n".join(blocks)


def main():
    parser = argparse.ArgumentParser(
        description="Emit a structured sub-agent dispatch prompt with required-slot enforcement.",
    )
    parser.add_argument("--task", required=True, help="The task brief.")
    parser.add_argument(
        "--churn", default="",
        help="1-3 sentences naming what recently landed / what got ripped / "
             "what the agent should treat as moving ground. Optional — "
             "include only when recent change directly affects the task; "
             "omit for steady-state work to avoid generic-orientation noise.",
    )
    parser.add_argument(
        "--files", default="",
        help="Comma-separated list of files in scope (optional).",
    )
    parser.add_argument(
        "--mode", default=DEFAULT_MODE, choices=MODES,
        help=f"Task shape; controls the report-back contract. "
             f"(default: {DEFAULT_MODE})",
    )
    parser.add_argument(
        "--conformance", action="store_true",
        help="Require the agent to run ops/check-conformance and report. "
             "Build mode only.",
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
            mode=args.mode,
        )
    except ValueError as e:
        print(f"dispatch.py: {e}", file=sys.stderr)
        sys.exit(2)

    print(out)


if __name__ == "__main__":
    main()
