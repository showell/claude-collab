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
    "doc_upkeep": "## Doc upkeep",
    "code_ownership": "## Code ownership",
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
    "survey": {
        "status": "Status",            # required: success | partial | blocked
        "inventory": "Inventory",       # required: prose deliverable (what exists)
        "open_questions": "Open questions",  # required: unresolved subject-ambiguities
        "if_easier": "IF",              # required: friction signal
        "out_of_scope": "Out-of-scope",  # optional
    },
}

RETURN_REQUIRED_BY_MODE = {
    "build": {"status", "files_changed", "if_easier"},
    "critique": {"status", "findings", "if_easier"},
    "survey": {"status", "inventory", "open_questions", "if_easier"},
}

MODES = tuple(RETURN_FIELDS_BY_MODE.keys())
DEFAULT_MODE = "build"

# ── Required-slot enforcement ──
#
# `churn` is intentionally NOT required. The original design treated it as
# load-bearing on every dispatch, but in practice many tasks have no recent
# change worth naming — forcing a churn slot produced generic orientation
# prose that read as boilerplate rather than as actionable signal. Keep
# churn for tasks where recent change directly affects the work; omit it
# for steady-state tasks. (Steve, 2026-05-04.)

DISPATCH_REQUIRED = {"task"}

# ── The fixed text of the report-back contract (per mode) ──

_IF_BLURB = """- IF: I could have done this more easily IF... <REQUIRED — name the
  single biggest friction you hit, even if small. Tooling gap, doc
  ambiguity, missing context, naming collision — any axis. If you
  genuinely hit no friction worth naming, write
  "IF: none-this-time — <one-line why nothing surfaced>"; that
  satisfies the requirement without forcing fabrication. Do NOT
  omit the field entirely.>"""

_OOS_BLURB = '- Out-of-scope: <anything you noticed but did not act on, or "none">'

_OPEN_QUESTIONS_BLURB = """- Open questions: <numbered list of unresolved ambiguities ABOUT THE
  SUBJECT you couldn't fully resolve from docs + code. Distinct from
  IF: open questions are uncertainties about the system being surveyed
  ("the catalog has both puzzle_id and seed fields — couldn't determine
  which is the dedup key"); IF is friction in doing the survey itself
  ("the docs were scattered and I had to grep for the schema"). If you
  fully resolved everything, write "Open questions: none — <one-line
  why nothing surfaced>". Do NOT omit the field entirely.>"""

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
    "survey": f"""\
Reply with these fields, each on its own line, in this order:

- Status: success | partial | blocked
- Inventory: <the survey deliverable. Structured prose describing what
  you found — files, schemas, code paths, naming conventions, whatever
  the task asked you to map. Use sub-headings, numbered lists, or
  tables as fits the subject. The Inventory field spans every line
  until the next field begins, so write as much prose as the work
  warrants. Survey is descriptive ("what exists"); for evaluative work
  ("is this good") use --mode critique instead.>
{_OPEN_QUESTIONS_BLURB}
{_IF_BLURB}
{_OOS_BLURB}""",
}

CONFORMANCE_TEMPLATE = """\
After implementation, run `ops/check-conformance` from the repo root
and include the green/red result in the Validation field. Do not
report success without running it."""

DOC_UPKEEP_TEMPLATE = """\
If your changes affect behavior, contracts, vocabulary, or file
layout that is documented anywhere (READMEs, design docs, top-of-file
comments, memory entries cited in this dispatch), update the relevant
docs as part of the change. Code drift is faster than doc drift;
closing the gap inside the same dispatch is cheaper than queueing it
as follow-up. Include any docs you touched in the Files-changed
field. If you decide a doc is intentionally out of date, say so in
Out-of-scope rather than silently leaving it stale."""

CODE_OWNERSHIP_TEMPLATE = """\
You own every file in this repo, not just the ones named in `Files
in scope`. If a needed helper is currently private to another
module, the default move is to export it (a one-line edit) and
import it — do NOT inline a copy as a workaround. Inlining produces
drift the orchestrator must chase later. The valid alternatives
are: (a) export-and-import (preferred); (b) punt — return status
`partial` and surface the question. Inlining-as-shortcut is the
wrong instinct."""

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
