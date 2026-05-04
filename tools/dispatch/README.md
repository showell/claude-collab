# dispatch — sub-agent dispatch protocol

A pair of scripts that encode the orchestrator's per-dispatch
discipline as a checkable protocol. The orchestrator's job
(composing a sub-agent prompt, parsing its return) has load-
bearing rules that previously lived as separate prose memories
the orchestrator had to remember to apply each time.

**Honest framing:** this is a checklist with teeth, not a
machine-checked gate. Nothing prevents the orchestrator from
composing a dispatch by hand and skipping the script entirely.
The closure mechanism is on the *running of the script* — when
it runs, it refuses bad inputs; if it doesn't run, the discipline
falls back to the orchestrator's memory. Don't oversell what's
enforced. The value is structural: the rules are in code instead
of scattered across prose memories, so the orchestrator who *does*
invoke the script gets the discipline applied uniformly.

## Why

Several rules were prose-only and easy to forget:

- **Anchor in recent churn when it's task-relevant** — a 1–3
  sentence hint about what just landed in the surface the agent
  is touching, so they can tell "this prose is stale" from "I
  don't get this yet." Optional, not required: forcing a churn
  slot on every dispatch produces generic-orientation noise when
  no recent change actually affects the task. Include it when
  the churn affects the work; omit it for steady-state tasks.
- **Mandatory IF in every return** — every sub-agent must
  finish with `IF: I could have done this more easily IF...`,
  the orchestrator's only window into friction the sub-agent
  hit silently. (If no friction surfaced, the agent writes
  `IF: none-this-time — <one-line why>` to satisfy the slot
  without forcing fabrication.)
- **Read-only intent stated explicitly** — when a task is an
  audit, the dispatch should say so up-front so the agent
  doesn't reach for Edit on impulse, and the parser can flag
  a violation if files were changed anyway.
- **Doc upkeep alongside code edits** — build-mode dispatches
  remind the agent to update affected docs (READMEs, design
  docs, top-of-file comments) as part of the same change.
  Closing doc-drift inside the dispatch is cheaper than
  queueing it as follow-up; deferred doc cleanup tends to be
  forgotten.
- **Code ownership** — sub-agents own every file in the repo,
  not just the ones in `Files in scope`. When a needed helper
  is private to another module, the default is to export it
  (small, mechanical) and import — NOT to inline a copy as a
  workaround. Inlining produces drift the orchestrator chases
  later; punting (status `partial`, surface the question) is
  also valid.

The orchestrator composes dispatches by hand. If a rule is
forgotten, nothing fails loudly — the dispatch just silently
omits the slot, and future cross-session signal is lost.

`dispatch.py` refuses to emit unless `--task` is present;
`--churn` is optional and is only rendered when supplied.
`parse_return.py` exits non-zero (code 3) if any required
return field is missing, and code 4 if a read-only dispatch
returned non-empty Files changed. Closure on a real variance
surface (the orchestrator's per-call discipline), not a
stylistic linter.

## Files

- `dispatch_dsl.py` — shared grammar (slot names, required-vs-
  optional, fixed templates for each section). One source of
  truth for the section headers + required-field invariants;
  both scripts import it.
- `dispatch.py` — emitter. Takes structured CLI args, emits
  the dispatch text. Refuses to emit if `--task` or `--churn`
  is empty.
- `parse_return.py` — extractor. Reads a sub-agent's reply
  (stdin or `--file`), pulls out the structured fields,
  emits JSON. Warns + exits non-zero (code 3) if any required
  field is missing; code 4 on a read-only-violation.

## Modes

Different task shapes have different deliverables. The
report-back contract is keyed by `--mode`:

| Mode | Required return fields |
|---|---|
| `build` (default) | Status, Files changed, Validation, IF, Out-of-scope |
| `critique` | Status, Findings, IF, Out-of-scope |
| `survey` | Status, Inventory, Open questions, IF, Out-of-scope |

Build mode is for "implement / refactor / fix" work — code
edits + tests. Critique mode is for audits and reviews where
the deliverable is prose findings, not code. Survey mode is
for discovery / mapping / orientation work where the deliverable
is an Inventory (what exists, where, how it's shaped) plus a
separate Open-questions field for unresolved subject-ambiguities.
Survey is read-only by definition — passing `--mode survey`
auto-applies the read-only template and rejects `--conformance`.

`survey` vs `critique`: critique evaluates ("is this good?"),
survey describes ("what is this?"). Different question, different
deliverable. `Open questions` (survey) and `IF` (all modes) are
also deliberately separate: open questions are unresolved
ambiguities about the *subject*; IF is friction in doing the
*work*. Sweep is still likely a future addition.

`parse_return.py` takes the same `--mode` flag and applies the
matching field grammar; pass the value the dispatch was
emitted with.

## Usage

Compose a build dispatch:

```
python3 dispatch.py \
    --task "Refactor X to use Y" \
    --churn "Z just landed; W docs not yet swept" \
    --files "path/a.py,path/b.py" \
    --conformance
```

Compose a critique dispatch:

```
python3 dispatch.py \
    --mode critique \
    --task "Audit the v1 X engine for code quality and design" \
    --churn "X engine landed yesterday in commit abc123" \
    --read-only
```

Compose a survey dispatch (read-only is auto-applied):

```
python3 dispatch.py \
    --mode survey \
    --task "Inventory the puzzle catalog: schema, fields, sort/dedup keys" \
    --churn "Python mining script retired today; catalog is currently frozen JSON"
```

`--read-only` and `--conformance` are mutually exclusive — a
read-only task does not modify code, so there's nothing for
conformance to verify. `--conformance` further requires
`--mode build`; other modes have no Validation field.

Parse a return (pass the same `--mode` the dispatch used):

```
cat reply.txt | python3 parse_return.py --mode critique
# or
python3 parse_return.py --file reply.txt --mode build
# or, if the dispatch was read-only:
python3 parse_return.py --file reply.txt --read-only
```

`--read-only` on the parser warns and exits non-zero (code 4)
if the agent reported any files changed despite the prohibition.
(Note: critique mode has no Files-changed field, so the
read-only check is a no-op there — the prohibition is text-
only, not parser-enforced.)

## What this is not

- Not a linter for letters or essays — those don't need one
  (two LLMs follow templates trivially; the format isn't a
  real variance surface).
- Not a runtime gate on Agent calls — Claude Code's `Agent`
  tool is invoked directly, with no pre-call hook the harness
  can use to enforce script invocation. The orchestrator must
  *choose* to run the script. From the receiving sub-agent's
  end, there's no way to verify whether a dispatch came from
  the script or was hand-composed; the closure on
  "script-was-run" is invisible from inside the dispatch.
- Not Brandon-side tooling — Brandon's plan-executor already
  has structured return blocks via `.claude/plan-executor.log`
  and `tools/analyze_ifs/` parses them. This is the analogous
  shape for ad-hoc orchestrators that don't run via plan-
  executor (i.e., today's Steve+Claude default mode).
