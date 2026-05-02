# Deferred — dispatch DSL improvements

Items surfaced by the meta-critique on 2026-05-01 (a sub-agent
critiqued the dispatch DSL while playing by its rules; full
return preserved in conversation history). The act-tonight bugs
landed in commit `62294c9`.

**Update 2026-05-02:** items 1, 2, and 3 below have landed.
Items 4, 5, and 6 remain deferred. The items are roughly
ordered by smallest-to-largest scope.

## 1. `--read-only` flag — LANDED 2026-05-02

**Surfaced by:** meta-critique. Currently "do not edit anything"
gets fished out of free-form `--task` text.

**Proposed:** add a `--read-only` boolean to `dispatch.py`. When
set:

- `dispatch.py` refuses `--conformance` (mutually exclusive).
- `parse_return.py` warns if `Files changed` is non-empty.
- The dispatch text gains an explicit "read-only — do not edit
  any files" line in the report-back area.

**Why this is right:** cheap invariant, real catch. The
read-only constraint has shown up in two of the three test
dispatches today; it's a recurring pattern, not a one-off.

**Dependencies:** none. Independent change. ~15 minutes.

## 2. `IF: none-this-time` safety valve — LANDED 2026-05-02

**Surfaced by:** meta-critique. The "REQUIRED — even if small"
framing risks filler IFs ("IF the file paths had been clickable")
which dilute `analyze_ifs.py`'s signal.

**Proposed:** keep the IF requirement, but add an explicit
absence pattern:

```
IF: none-this-time — <one-line why nothing surfaced>
```

The agent must still actively justify the absence — the
discipline is preserved — but they don't have to fabricate.

**Why this is right:** the goal of the IF channel is friction
surfacing, not ritual. Forcing a non-empty IF when nothing was
there gets you noise. Justified-absence keeps the consideration
honest.

**Dependencies:** small text change to `BASH_DISCIPLINE_TEMPLATE`'s
sibling, the `REPORT_BACK_TEMPLATE`. Maybe a parser-side update
to `parse_return.py` so `if_easier: "none-this-time"` doesn't
trip the missing-IF exit-code-3. ~20 minutes.

## 3. README honesty pass — "advisory, not enforced" — LANDED 2026-05-02

**Surfaced by:** meta-critique. The README claims "machine-
checked grammar" but nothing actually forces the orchestrator
to *invoke* `dispatch.py`. The closure is on the orchestrator's
own discipline.

**Proposed:** add a paragraph naming this honestly. The script
is "a checklist with teeth, when run." We can't fully close the
loop (Claude Code has no pre-Agent-call hook), but we can avoid
overselling the enforcement.

**Why this is right:** the variance-surface frame applies
recursively. "Orchestrator intends to run script" vs "script
actually ran" is itself an open surface, invisible from the
receiving end (the meta-critique agent couldn't tell whether
the dispatch they were reading came from the script or was
hand-composed). Naming the surface is the honest move.

**Dependencies:** none. README edit. ~5 minutes.

## 4. `mode` slot — build / critique / discovery / sweep

**Surfaced by:** meta-critique (their strongest structural
critique). The current report-back contract is shaped for build
tasks: `Status`, `Files changed`, `Validation`. On a critique
task, two of those slots are vacuous (`Files changed: none`,
`Validation: none`) and the actual deliverable (the prose
critique itself) has nowhere to live — `parse_return.py`
silently drops everything outside the field grammar.

**Proposed:** add a `--mode` arg with values `{build, critique,
discovery, sweep}`. The dispatch text is mode-agnostic; the
report-back contract varies by mode:

- `build`: Status, Files changed, Validation, IF, Out-of-scope
- `critique`: Status, Findings, IF, Out-of-scope
- `discovery`: Status, Inventory, IF, Out-of-scope
- `sweep`: Status, Drift findings, Files patched, IF, Out-of-scope

`parse_return.py` would dispatch on the mode and apply the right
field grammar.

**Why this is right:** the contract is currently shaped for one
of four task types. The meta-critique agent's actual deliverable
(prose) had no home in the contract. The cleanest fix is making
the grammar mode-conditional rather than try to invent a slot
that fits all four shapes.

**Why it's deferred:** real expansion in scope. Multiple
grammars, mode-specific parsers, more code. Worth doing if we
believe the dispatch DSL has legs beyond the next few sessions;
not worth doing if we expect to abandon or replace it. Probably
the right move, but the conversation about it deserves time.

**Dependencies:** ties to #5. ~1-2 hours.

## 5. Mode-specific deliverable slot

**Surfaced by:** same meta-critique. Tied to #4. A critique's
deliverable is prose; a discovery's is a list; a sweep's is a
combination of findings + patches. None of these fit the build-
shaped contract.

**Two options:**

- **(a)** Add an optional `Findings:` / `Inventory:` field per
  mode (couples to #4).
- **(b)** Make `parse_return.py` preserve pre-field prose under a
  `body` key (decoupled from #4, simpler).

**Why this is right:** today, a critique agent has to choose
between filling the contract honestly (and losing their actual
work) or appending the work as free prose (and trusting the
parser to drop it). Neither is right.

**Why it's deferred:** option (b) is a quick patch we could land
independently. Option (a) is the disciplined version and ties to
the mode work in #4. Worth choosing deliberately.

**Dependencies:** option (b) is independent (~20 minutes); option
(a) couples to #4.

## 6. Provenance marker — was the dispatch generated by the script?

**Surfaced by:** meta-critique observation. The agent inferred
the dispatch they were reading was hand-composed (it wasn't —
`dispatch.py` produced it verbatim). From the receiving end,
there's no way to verify whether the script was used.

**Proposed (light):** add a comment line to the bottom of every
`dispatch.py`-generated dispatch:

```
<!-- generated by dispatch.py v1 (2026-05-01) -->
```

Lets a careful agent (or the human, scanning) confirm provenance.
Doesn't enforce anything, but closes a tiny visibility gap.

**Why it's deferred:** the value is small and easily mistaken for
ceremony. Worth doing only if we end up doing #4 / #5 anyway and
provenance becomes a real concern.

**Dependencies:** none. ~10 minutes if done in isolation.

## Note on prioritization

If you want a single suggestion: **#1 + #2 + #3 land in one
small commit (~45 minutes total)**, all are independent and
straightforwardly right. The conversation about #4 + #5 is
worth holding until we know whether the dispatch DSL is
something we keep using or replace with something Brandon-style
plan-executor-shaped after the cross-Claude exchange. #6 stays
parked until then.
