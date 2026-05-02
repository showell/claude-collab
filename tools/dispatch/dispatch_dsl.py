"""
Sub-agent dispatch DSL — shared grammar for dispatch + return.

The grammar lives in one place so dispatch.py (emitter) and
parse_return.py (extractor) agree on slot names, required-vs-
optional, and section ordering. See `DISPATCH_SECTIONS`,
`RETURN_FIELDS`, `DISPATCH_REQUIRED`, and `RETURN_REQUIRED`
below for the canonical lists — they are the source of truth.

The IF field is required-and-load-bearing — it is the
orchestrator's only window into sub-agent friction. Both
emitter and parser refuse to accept a return that lacks it.
"""

# ── Section headers (canonical wording; emitter + parser both pin these) ──

DISPATCH_SECTIONS = {
    "churn": "## Recent churn",
    "task": "## Task",
    "files": "## Files in scope",
    "conformance": "## Validation requirement",
    "read_only": "## Read-only",
    "bash_discipline": "## Bash discipline",
    "report_back": "## Report-back contract",
}

# Field-label maps and required-field sets are mode-keyed. The label
# map for a mode lists every field the parser will recognize for that
# mode, in the order the report-back contract presents them. The
# required set lists which of those must be present (parser exits
# non-zero if any are missing).

RETURN_FIELDS_BY_MODE = {
    "build": {
        "status": "Status",            # required: success | partial | blocked
        "files_changed": "Files changed",  # required
        "validation": "Validation",     # optional
        "if_easier": "IF",              # required: friction signal
        "out_of_scope": "Out-of-scope",  # optional
    },
    "critique": {
        "status": "Status",            # required: success | partial | blocked
        "findings": "Findings",        # required: prose deliverable
        "if_easier": "IF",              # required: friction signal
        "out_of_scope": "Out-of-scope",  # optional
    },
}

RETURN_REQUIRED_BY_MODE = {
    "build": {"status", "files_changed", "if_easier"},
    "critique": {"status", "findings", "if_easier"},
}

MODES = tuple(RETURN_FIELDS_BY_MODE.keys())
DEFAULT_MODE = "build"

# ── Required-slot enforcement ──

DISPATCH_REQUIRED = {"churn", "task"}

# ── The fixed text of the report-back contract (per mode) ──

_IF_BLURB = """- IF: I could have done this more easily IF... <REQUIRED — name the
  single biggest friction you hit, even if small. Tooling gap, doc
  ambiguity, missing context, naming collision — any axis. If you
  genuinely hit no friction worth naming, write
  "IF: none-this-time — <one-line why nothing surfaced>"; that
  satisfies the requirement without forcing fabrication. Do NOT
  omit the field entirely.>"""

_OOS_BLURB = '- Out-of-scope: <anything you noticed but did not act on, or "none">'

REPORT_BACK_TEMPLATES = {
    "build": f"""\
Reply with these fields, each on its own line, in this order:

- Status: success | partial | blocked
- Files changed: <comma-separated list, or "none">
- Validation: <output of any tests/checks run, or "none">
{_IF_BLURB}
{_OOS_BLURB}""",
    "critique": f"""\
Reply with these fields, each on its own line, in this order:

- Status: success | partial | blocked
- Findings: <numbered list of findings. Each item is a one-line claim
  prefixed by severity (high/med/low); multi-paragraph elaboration may
  follow under each item — the parser preserves it. The Findings field
  spans every line until the IF field begins, so write as much prose
  as the work warrants.>
{_IF_BLURB}
{_OOS_BLURB}""",
}

CONFORMANCE_TEMPLATE = """\
After implementation, run `ops/check-conformance` from the repo root
and include the green/red result in the Validation field. Do not
report success without running it."""

READ_ONLY_TEMPLATE = """\
This task is **read-only**. Do not edit any files. Your "Files
changed" field must be "none". If you find that the task as
described requires edits to complete, stop and report status
"blocked" with an explanation in your IF — do not proceed with
edits."""

BASH_DISCIPLINE_TEMPLATE = """\
**Bash discipline (strict — every command you run lands in front of the
human as a permission prompt; needless prompts are spam):**

- Do NOT prefix commands with `cd <dir> && ...`. The cwd is already
  set; chained `cd` triggers an extra approval gate. If you genuinely
  need to run from a different dir, use the tool that supports it
  (`git -C <dir>`, `python -C ...`, etc.) — but in nearly all cases
  the cwd is already correct.
- Do NOT chain commands with `&&` or `;` when a single command would
  do. One command per Bash call.
- Use `Read` for reading files, `Grep` for searching — NOT `cat`,
  `head`, `tail`, `sed`, `awk`. Reason: Read and Grep are the
  documented file-access tools; the harness's permissions are tuned
  to them, and free-form bash text-processing tends to grow into
  ad-hoc one-liners (`cat X | grep Y | sed Z`) that drift away from
  the documented surface.
- Keep commands minimal. Every flag, every redirect, every pipe is
  another thing the human has to scan."""
