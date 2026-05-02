"""
parse_return.py — extract structured fields from a sub-agent's return.

Reads a sub-agent's reply text (stdin or --file), pulls out the
fields the dispatch asked for, and reports any missing required
field — especially the IF, which is the orchestrator's only
window into sub-agent friction.

Output is JSON to stdout. Missing-required-field warnings go
to stderr; the script exits non-zero (code 3) if any required
field is missing, and code 4 if a read-only dispatch returned
non-empty Files changed.

Usage:

    cat sub_agent_reply.txt | python3 parse_return.py
    python3 parse_return.py --file sub_agent_reply.txt
"""

import argparse
import json
import re
import sys

from dispatch_dsl import (
    RETURN_FIELDS_BY_MODE,
    RETURN_REQUIRED_BY_MODE,
    MODES,
    DEFAULT_MODE,
)


def parse_return(text, *, mode=DEFAULT_MODE):
    """Extract structured fields from a sub-agent's reply.

    Returns a dict mapping field-key -> value (string or list).
    Unparsed input is ignored; the parser walks the text looking
    for `<Field>:` prefixes (taken from the mode's field map) and
    captures each field's value (which may span lines until the
    next field begins).
    """
    return_fields = RETURN_FIELDS_BY_MODE[mode]
    field_labels = {label: key for key, label in return_fields.items()}
    label_pattern = "|".join(re.escape(l) for l in field_labels)
    field_re = re.compile(rf"^\s*[-*]?\s*({label_pattern})\s*:\s*(.*)$", re.IGNORECASE)

    fields = {}
    current_key = None
    current_buf = []

    def flush():
        if current_key is not None:
            fields[current_key] = "\n".join(current_buf).strip()

    for raw_line in text.splitlines():
        m = field_re.match(raw_line)
        if m:
            flush()
            label = m.group(1)
            current_key = next(
                key for lbl, key in field_labels.items()
                if lbl.lower() == label.lower()
            )
            current_buf = [m.group(2).strip()] if m.group(2).strip() else []
        else:
            if current_key is not None:
                current_buf.append(raw_line)

    flush()

    # Post-process: split files_changed into a list if comma-separated
    if "files_changed" in fields and fields["files_changed"]:
        val = fields["files_changed"]
        if val.lower() == "none":
            fields["files_changed"] = []
        elif "," in val:
            fields["files_changed"] = [s.strip() for s in val.split(",") if s.strip()]
        else:
            fields["files_changed"] = [val] if val else []

    return fields


def main():
    parser = argparse.ArgumentParser(
        description="Extract structured fields from a sub-agent reply.",
    )
    parser.add_argument(
        "--file", default=None,
        help="Path to a file containing the reply (default: read from stdin).",
    )
    parser.add_argument(
        "--mode", default=DEFAULT_MODE, choices=MODES,
        help=f"Task mode (must match the dispatch's --mode). Selects which "
             f"field grammar to apply. (default: {DEFAULT_MODE})",
    )
    parser.add_argument(
        "--read-only", action="store_true",
        help="The dispatch was read-only. Warn if Files changed is non-empty "
             "(the agent edited despite the prohibition).",
    )
    args = parser.parse_args()

    if args.file:
        with open(args.file) as f:
            text = f.read()
    else:
        text = sys.stdin.read()

    fields = parse_return(text, mode=args.mode)

    # "Missing" means the field key wasn't present in the input at all.
    # An explicit "none" answer (which post-processes to "" or []) is a
    # valid completion — it satisfies the slot.
    missing = [k for k in RETURN_REQUIRED_BY_MODE[args.mode] if k not in fields]
    if missing:
        print(
            f"parse_return.py: missing required field(s): {', '.join(sorted(missing))}",
            file=sys.stderr,
        )

    if args.read_only and fields.get("files_changed"):
        print(
            f"parse_return.py: read-only dispatch but Files changed is non-empty: "
            f"{fields['files_changed']!r}",
            file=sys.stderr,
        )

    print(json.dumps(fields, indent=2))

    # Any missing required field is non-zero exit so callers can branch on it.
    if missing:
        sys.exit(3)
    # Read-only violation is also exit non-zero (different code).
    if args.read_only and fields.get("files_changed"):
        sys.exit(4)


if __name__ == "__main__":
    main()
