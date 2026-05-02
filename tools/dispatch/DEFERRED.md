# Deferred — dispatch DSL improvements

Items surfaced by the meta-critique on 2026-05-01 (a sub-agent
critiqued the dispatch DSL while playing by its rules; full
return preserved in conversation history). The act-tonight bugs
landed in commit `62294c9`.

**Update 2026-05-02 (later):** items 1, 2, 3, and 5 have landed.
Item 4 is partially landed (build + critique modes; discovery +
sweep stay deferred until a real task surfaces the need). Item
6 remains deferred. The items are roughly ordered by smallest-
to-largest scope.

**Trial-run validation:** the build/critique split was exercised
end-to-end on 2026-05-02 — a read-only TOP_DOWN_SWEEP of the
dispatch DSL itself (build mode), then a critique-mode audit of
the v1 TS BFS port. Both round-tripped cleanly through
`parse_return.py`. Findings:

- `--read-only` deters edits — both trial agents reported `Files
  changed: none` and flagged would-be-edits as out-of-scope
  rather than reaching for Edit.
- `IF: none-this-time` was used honestly on the first trial; the
  second trial surfaced real friction (an asked-for `PORT_STATUS.md`
  crosswalk doc), which was acted on immediately. No filler.
- The critique-mode `Findings` field captured 7400 chars of prose
  the build contract would have dropped silently.

The DSL is validated for the build/critique modes. Future
sub-agent work goes through `dispatch.py` by default; new modes
get added when a task shape surfaces the need, not on speculation.

## 1. `--read-only` flag — LANDED 2026-05-02

**Surfaced by:** meta-critique. Currently "do not edit anything"
gets fished out of free-form `--task` text.

**Proposed:** add a `--read-only` boolean to `dispatch.py`. When
set:

- `dispatch.py` refuses `--conformance` (mutually exclusive).
- `parse_return.py` warns + exits non-zero (code 4) if `Files
  changed` is non-empty.
- The dispatch text gains an explicit `## Read-only` section
  before bash discipline, naming the prohibition.

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
sibling, the `REPORT_BACK_TEMPLATE`. (No parser change needed —
any non-empty IF, including `none-this-time`, populates the
`if_easier` field and passes the missing-required check.)
~20 minutes.

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

## 4. `mode` slot — build / critique / discovery / sweep — IN PROGRESS

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

`parse_return.py` dispatches on the mode and applies the right
field grammar.

**Status 2026-05-02:** `build` and `critique` modes landed in
commit `3967ea4` and validated end-to-end (see top-of-file
trial-run section). `discovery` and `sweep` remain unstarted —
add them when a real task surfaces the need, not on speculation.

**Why this is right:** the contract was shaped for one of four
task types. The meta-critique agent's actual deliverable (prose)
had no home in the build contract. Making the grammar mode-
conditional rather than inventing a one-slot-fits-all field
proved out: the critique-mode `Findings` slot took 7400 chars of
prose cleanly on the first real audit.

## 5. Mode-specific deliverable slot — LANDED 2026-05-02 (option a)

**Surfaced by:** same meta-critique. Tied to #4. A critique's
deliverable is prose; a discovery's is a list; a sweep's is a
combination of findings + patches. None of these fit the build-
shaped contract.

**Resolution:** chose option (a) — added a `Findings` field to
the critique-mode contract (landed alongside #4 in commit
`3967ea4`). When discovery / sweep modes are added, each will
get its own deliverable slot (`Inventory`, `Drift findings`).
Option (b) — preserving free prose under a `body` key — is no
longer needed; the structured slot is the better answer.

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

## Note on what's left

Item 6 (provenance marker) is the only deferred item. It's a
small visibility nicety, not a bug. Hold it until either (a) a
real ambiguity surfaces about whether a dispatch came from the
script vs hand-composed, or (b) we add a second author of
dispatches and want a way to tell who emitted what.

Discovery and sweep modes (item 4 sub-items) wait for a real
task that needs them. Don't pre-build the grammar — the build
and critique shapes were both anchored in concrete pain, and
that's what kept them honest. Speculation invents fields nobody
fills.
