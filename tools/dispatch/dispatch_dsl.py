"""
Sub-agent dispatch DSL — shared grammar for dispatch + return.

The grammar lives in one place so dispatch.py (emitter) and
parse_return.py (extractor) agree on slot names, required-vs-
optional, and section ordering.

The DSL is two grammars wired together:

  DISPATCH  — what the orchestrator sends to the sub-agent.
              Required slots: churn, task, report_back.
              Optional slots: files, conformance.

  RETURN    — what the sub-agent sends back.
              Required fields: status, files_changed, if_easier.
              Optional fields: validation, out_of_scope.

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

RETURN_FIELDS = {
    "status": "Status",            # required: success | partial | blocked
    "files_changed": "Files changed",  # required
    "validation": "Validation",     # optional
    "if_easier": "IF",              # required: "I could have done this more easily IF..."
    "out_of_scope": "Out-of-scope",  # optional
}

# ── Required-slot enforcement ──

DISPATCH_REQUIRED = {"churn", "task"}
RETURN_REQUIRED = {"status", "files_changed", "if_easier"}

# ── The fixed text of the report-back contract ──

REPORT_BACK_TEMPLATE = """\
Reply with these fields, each on its own line, in this order:

- Status: success | partial | blocked
- Files changed: <comma-separated list, or "none">
- Validation: <output of any tests/checks run, or "none">
- IF: I could have done this more easily IF... <REQUIRED — name the
  single biggest friction you hit, even if small. Tooling gap, doc
  ambiguity, missing context, naming collision — any axis. If you
  genuinely hit no friction worth naming, write
  "IF: none-this-time — <one-line why nothing surfaced>"; that
  satisfies the requirement without forcing fabrication. Do NOT
  omit the field entirely.>
- Out-of-scope: <anything you noticed but did not act on, or "none">"""

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
