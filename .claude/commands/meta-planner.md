---
description: Restructure plans into execution-ready format with master checklist, phase files, code-architect-grounded blueprint, verification hooks, and TaskCreate-driven execution
argument-hint: <path-to-plan-file-or-directory>
---

# /meta-planner — Restructure Plans for Automated Execution

Take an existing plan (single file, multiple files, or directory) and restructure it into an execution-ready format with a master checklist, discrete phase files, codebase-grounded architecture, built-in testing, code review gates, and pre/post verification hooks.

**Execution model:** TaskCreate-driven. Plans are executed by reading the master plan, mirroring every task into the in-session task tracker (TaskCreate/TaskUpdate), then walking the checklist. No ralph-loop, no completion-promise tags, no max-iterations math. Checkboxes in the master plan + task tracker entries are the dual source of truth.

## Usage

```
/meta-planner <path-to-plan>
/meta-planner plans/my-feature/
/meta-planner plans/2026-02-22-some-plan.md
```

## What This Skill Does

1. **Reads** the input plan(s) — single file, multiple files, or entire directory
2. **Analyzes** the plan structure, tasks, dependencies, and phases
3. **Dispatches `feature-dev:code-architect`** as a subagent to extract codebase patterns, similar features, and produce an implementation blueprint grounded in actual files
4. **Verifies against the codebase** — reads actual files referenced by the plan, extracts current signatures, validates paths exist
5. **Restructures** into execution-ready format with:
   - `00-master-plan.md` — master checklist + TaskCreate execution rules + cross-plan dependencies + agent tiers
   - Phase files (`YYYY-MM-DD-phase-N-description.md`) — discrete task groups with verification hooks
   - `.loop-gap-config.md` — pre-configured gap scanner settings for `/loop-gap`
   - Original reference preserved as-is (if large)
6. **Embeds verification hooks** — every task has `Verify-Before` (preconditions) and `Verify-After` (postconditions)
7. **Validates** every task has: agent tier, test command, file list, commit step, verification hooks
8. **Embeds test + code-review gates** after every phase

---

## Output Structure

```
plans/<plan-name>/
├── 00-master-plan.md                  ← Master checklist + TaskCreate execution rules
├── .loop-gap-config.md                ← Pre-configured gap scanner settings
├── YYYY-MM-DD-phase-1-*.md            ← Phase 1 tasks (detailed steps + hooks)
├── YYYY-MM-DD-phase-2-*.md            ← Phase 2 tasks
├── ...                                ← More phases as needed
└── YYYY-MM-DD-original-reference.md   ← Original plan preserved (if needed)
```

---

## Instructions

### Step 0: Read Learned Patterns

Before analyzing the input plan, read this command's `## Learned Patterns` section (at the bottom of this file). For each pattern:
- If the pattern's `Applies to` matches the current plan context, incorporate it as an additional requirement when generating phase files
- Patterns typically add verification hooks, require additional subtasks, or adjust phase sizing
- Cite the LP number in the generated phase file (e.g., "per LP-003")
- Patterns are cumulative — apply ALL that match, not just the first
- Document which patterns were applied in the master plan's `## Execution Notes` section (e.g., "Applied: LP-001, LP-003, LP-007")

### Stage 1: Read and Understand the Input

1. **Read all input files.** If given a directory, read every `.md` file in it.
2. **Detect the project context.** Read the project's CLAUDE.md (or the relevant child repo's CLAUDE.md) to determine:
   - The project root directory
   - The test framework and test commands (e.g., `pytest`, `vitest`, `npm test`, `svelte-check`)
   - The directory structure conventions
   - Build/run commands
3. **Inventory all tasks.** Extract every discrete unit of work — look for:
   - Numbered tasks/steps
   - Checkbox items (`- [ ]`)
   - Section headers describing work
   - Code blocks that need to be written
   - Test commands
4. **Map dependencies.** Which tasks must come before others?
5. **Identify phases.** Group related tasks into logical phases (3-8 tasks per phase max).

### Stage 1.5: Codebase Verification (Ground Truth Pass)

**Before writing any phase files**, verify the plan against the actual codebase. This prevents generating plans with stale assumptions, wrong file paths, or incorrect function signatures.

#### Step 1.5.1: Collect all file references

Scan the input plan for every file path mentioned in `- Files:`, `- Create:`, `- Modify:`, `- Test:` lines, code blocks, and prose. Build a **Codebase Reference Table**:

```
| File Path | Plan Says | Action | Exists? | Current Signature |
|-----------|-----------|--------|---------|-------------------|
```

#### Step 1.5.2: Read and verify each file

For each file in the reference table:

1. **Modify/Test (file should exist):** Read it. Extract relevant signatures the plan mentions. Compare against plan assumptions. Record current signature snapshot.
2. **Create (file will be made):** Verify parent directory exists. Check naming conflicts. Check whether downstream importers exist after the creation task.
3. **Test files:** If exists, verify test class/function names. If new, verify test framework matches project conventions.

#### Step 1.5.3: Check for plan staleness

Run `git log --since={PLAN_DATE} --name-only -- {FILES}`. Files modified after plan date → flag as potentially stale. Read diffs to determine if assumptions hold. Document in `## Stale Alerts`.

#### Step 1.5.4: Discover callers and dependents

For each file the plan modifies, grep for importers:

```bash
grep -rn "from {module} import\|import {module}" --include="*.py" --include="*.ts" --include="*.svelte"
```

Record as **affected files** — they may need updates not in the plan. Include in `Verify-After` hooks.

#### Step 1.5.5: Resolve mismatches

- Wrong file path → fix in plan, document correction
- Wrong function signature → update plan steps to use actual signature
- Missing file → verify it's created by a prior task, or flag as gap
- Stale assumptions → update plan to match current state
- Unaccounted callers → add to affected files list

**Output:** A verified codebase reference table used downstream by Stage 1.5b and Stage 2.

### Stage 1.5b: Architect Dispatch (Codebase-Grounded Blueprint)

**Why this exists:** Stage 1.5 verifies *paths*. Stage 1.5b verifies *patterns* — does this plan match how the codebase actually does this kind of work? Catches: wrong abstraction layer, missed conventions, parallel feature already exists, untested integration points.

**When to apply:** Always, unless the plan is purely doc/config (no source code changes).

**How:** Dispatch the `feature-dev:code-architect` subagent with the plan summary + verified file reference table + project CLAUDE.md context. Ask for a blueprint covering:

- **Patterns & Conventions Found** — existing patterns with `file:line` references, similar features, key abstractions
- **Architecture Decision** — a confident chosen approach with rationale (single decision, not a menu)
- **Component Design** — each component with file path, responsibilities, dependencies, interfaces
- **Implementation Map** — specific files to create/modify with detailed change descriptions
- **Data Flow** — entry points → transformations → outputs
- **Build Sequence** — phased implementation steps as a checklist
- **Critical Details** — error handling, state management, testing, performance, security

**Agent tool call template:**

```
Agent({
  subagent_type: "feature-dev:code-architect",
  description: "Architecture blueprint for <feature>",
  prompt: """
    You are dispatched by /meta-planner to ground a plan against the codebase.

    Project root: {PROJECT_ROOT}
    Plan summary: {ONE_PARAGRAPH_SUMMARY}
    Plan file inventory (verified existence + current signatures from Stage 1.5):
    {CODEBASE_REFERENCE_TABLE}

    Read CLAUDE.md and the relevant .claude/context/*.md files. Read 2–4
    similar existing features in the codebase. Then deliver a complete
    architecture blueprint per your skill's output guidance.

    Be decisive. Pick one approach. Provide file:line references.
  """
})
```

**Use the architect's output to:**

1. **Re-shape phase boundaries** — adopt the architect's `Build Sequence` as the phase split heuristic (overrides "3–8 tasks per phase" defaulting if the architect proposes a cleaner cut)
2. **Lift exact file paths** — the architect's `Component Design` and `Implementation Map` provide canonical paths and signatures that flow into phase files' `Files:` lines and `Codebase Snapshot` blocks
3. **Inherit test commands** — the architect knows the project's test conventions; lift them verbatim into phase file `Test:` lines
4. **Reconcile mismatches** — if the architect's blueprint disagrees with the input plan (different file path, different abstraction), the architect's view wins by default. Document the deviation in the master plan's `## Architect Notes` section. Flag for user only if the deviation reverses a decision the input plan explicitly justified.

**Output:** Architect blueprint in memory for Stage 2 + a `## Architect Notes` block in the master plan summarizing patterns/conventions found and any input-plan deviations.

### Stage 1.6: API Contract Specification (MANDATORY for full-stack plans)

**Why this exists:** Frontend and backend are often built in separate phases by parallel agents. Each side is built against the *plan's* API contract, not against each other. Backend may make pragmatic deviations (different URL paths, response field names, pagination shapes) that the frontend never learns about. Result: 404s at runtime despite green unit tests. This step forces explicit contract definition as a first-class plan artifact.

**When to apply:** Any plan that touches BOTH backend (route handlers, API endpoints, response schemas) AND frontend (JS/TS API calls, templates that fetch data, extension webview calls). Skip for backend-only or frontend-only plans.

#### Step 1.6.1: Identify all API contracts

Scan the plan for every API interaction: new endpoints, modified endpoints, frontend components/templates that will call APIs, TypeScript interfaces or JS objects for responses, extension webview message contracts.

#### Step 1.6.2: Build the Contract Table

```markdown
## API Contract Specification

| Endpoint | Method | URL Path (as mounted) | Request Schema | Response Schema | Frontend Consumer |
|----------|--------|----------------------|----------------|-----------------|-------------------|
| List manuscripts | GET | /api/v1/manuscripts | `?page=int&per_page=int` | `{data: [...], meta: {total, page, per_page, pages}}` | `manuscripts.js`, `dashboard.html` |
| Run analysis | POST | /api/v1/analysis/run | `{codex_id: str, type: str}` | `{task_id: str, status: str}` | `analysis.js:runAnalysis()` |
```

#### Step 1.6.3: Verify contracts against existing code

For each contract entry:

1. **Backend exists:** READ the actual route handler and response marshalling. Extract real URL path (incl. blueprint prefix), real response fields. Compare against plan assumptions. **Fix mismatches in the plan NOW** — code is the source of truth.
2. **Backend will be created:** Embed the exact ORM model / schema / response dict structure in the plan's phase file. Frontend agent uses this as source of truth.
3. **Frontend type already exists:** READ it. Compare field names and types against backend response. Fix mismatches.
4. **Pagination patterns:** Read all existing paginated endpoints. New endpoints MUST use the same shape. If frontend has a generic pagination handler, verify it matches actual backend pattern.

#### Step 1.6.4: Embed contracts in phase files

- Tasks creating/modifying an API endpoint MUST include the contract table entry
- Tasks creating/modifying a frontend API call MUST reference the contract table
- API task `Verify-After` MUST include: "Frontend JS/TS type matches backend response schema"
- Frontend task `Verify-After` MUST include: "API call URL matches the mounted backend route path"

**Output:** Contract table embedded in the plan. Phase files reference it. Verify-After hooks enforce it.

### Stage 2: Create the Phase Files

For each phase, create a file following this exact structure:

````markdown
# Phase N: Phase Title — Tasks X-Y

> **Reference:** [Link to original plan or section if applicable]

## Codebase Snapshot (at plan generation time)

Files this phase modifies with their current signatures:

```
{FILE_PATH}:
  - {function_name}({params}) -> {return_type}  [line {N}]
  - {class_name}.{method_name}({params})  [line {N}]
```

Callers of modified functions (may need updates):

```
{CALLER_FILE}:{LINE} — calls {function_name}()
{CALLER_FILE_2}:{LINE} — imports {class_name}
```

## Task X: Descriptive Task Title

**Files:**
- Create: `exact/path/to/new_file.py`
- Modify: `exact/path/to/existing.py`
- Test: `tests/exact/path/to/test_file.py`

**Verify-Before** (preconditions — check BEFORE starting):
- [ ] `exact/path/to/existing.py` exists and contains `def function_name(` at ~line N
- [ ] `from module import dependency` resolves
- [ ] Prior tasks 0-{X-1} are complete
- [ ] No uncommitted changes in files this task modifies

**Verify-After** (postconditions — check AFTER completing):
- [ ] `{PROJECT_TEST_COMMAND} tests/path/test.py -v` passes
- [ ] `exact/path/to/existing.py` now contains `def updated_function(`
- [ ] All callers of `function_name()` still work
- [ ] No type errors introduced: `{TYPE_CHECK_COMMAND}` (if applicable)
- [ ] Git diff shows ONLY expected changes

### Step X.1: Write the failing test

```python
def test_specific_behavior():
    result = function(input)
    assert result == expected
```

### Step X.2: Run test to verify it fails

Run: `{PROJECT_TEST_COMMAND} tests/path/test.py::test_name -v`
Expected: FAIL — "function not defined" or similar

### Step X.3: Write minimal implementation

```python
def function(input):
    return expected
```

### Step X.4: Run tests to verify pass

Run: `{PROJECT_TEST_COMMAND} tests/path/test.py -v`
Expected: PASS

### Step X.5: Verify postconditions

Run through each item in `Verify-After` above. Fix any failures before committing.

### Step X.6: Commit

```bash
git add tests/path/test.py src/path/file.py
git commit -m "feat: add specific feature"
```
````

**Phase file rules:**
- Every task MUST have a test command (even if manual verification)
- Every task MUST list exact file paths (Create/Modify/Test)
- Every task MUST have `Verify-Before` and `Verify-After` hooks
- Every task MUST end with a commit step
- Code blocks must be complete and copy-paste ready
- Steps follow TDD: test → fail → implement → pass → verify → commit
- **Detect project test commands** from CLAUDE.md or existing test infrastructure
- **Codebase Snapshot from actual file reads** — never guess signatures
- **File paths and signatures should match the architect's blueprint** (Stage 1.5b)

### Stage 3: Create the Master Plan

Create `00-master-plan.md` with this structure. **CRITICAL:** The master plan embeds test + code-review gates after every phase. The executor walks ALL tasks continuously without stopping.

````markdown
# [Feature Name] — Master Plan

> **For Claude:** This is an automated execution master plan. Read the Execution Rules below, then execute ALL unchecked tasks continuously using the in-session task tracker (TaskCreate/TaskUpdate).

## How to Start

Ask Claude to execute this plan:

```
Execute plans/<plan-name>/00-master-plan.md
```

Claude reads the Execution Rules below and follows them. All instructions are self-contained in this file. There is no external loop runner — execution is driven by the in-session task tracker plus the checkbox state in this file.

---

## Execution Rules

**CRITICAL: Execute ALL tasks in one continuous run. NEVER stop between tasks.**

### Task Tracker Bootstrap (do this FIRST)

Before executing any task, scan this entire checklist and create a `TaskCreate` entry for EVERY task and CHECKPOINT. This gives the user a live progress dashboard. Do this FIRST, before claiming or executing anything.

```
For each task in the checklist:
  TaskCreate({
    subject: "Task N: <title>",
    description: "Phase N — <agent tier> — <files touched>",
    activeForm: "Working on Task N: <title>"
  })
For each CHECKPOINT:
  TaskCreate({
    subject: "CHECKPOINT Phase N: <description>",
    description: "Tests + code review gate",
    activeForm: "Running Phase N checkpoint"
  })
```

After bootstrap, set up dependencies via `TaskUpdate({ taskId, addBlockedBy: [...] })` so phase ordering is enforceable by the tracker (Phase N tasks blockedBy Phase N-1 CHECKPOINT).

As you work, update each task's status: `pending` → `in_progress` → `completed`. Update the task tracker BEFORE marking the checkbox in this master plan file. Both must move together — they are the dual source of truth.

### Anti-Stub Mandate

These rules exist because previous agents have falsely marked tasks DONE:

1. **NEVER mark a parent DONE until ALL children are DONE.** If a wave has 14 tasks, all 14 must be `[x]` AND `completed` in TaskList. Run: `grep -c '^\- \[ \]' {wave-plan}` — if > 0, the wave is NOT done.
2. **NEVER mark a task DONE without running its verification command.** Every task has a `Test:` or `Verify:` line. Run it. Paste the output. If it fails, the task is NOT done.
3. **NEVER mark a task DONE if the implementation is a stub.** A stub = hardcoded return, placeholder text, TODO comment, `pass`, `unimplemented!()`. Grep for these after implementation.
4. **For fractal plans:** Read the sub-plan, execute EACH internal task, check EACH internal box. The parent box changes to DONE only after the sub-plan's final summary fires.
5. **If you cannot complete a task:** Keep its TaskList status as `in_progress`, add diagnostic via `TaskUpdate({ description })`, escalate. Never mark `completed` if it isn't.

### Status Protocol

Tasks have inline status tags for parallel-safe execution. Status in this file mirrors the task tracker:

| Status | Meaning | Format |
|--------|---------|--------|
| `` `OPEN` `` | Available for pickup (TaskList: `pending`, no owner) | `- [ ] \`OPEN\` **Task N:** ...` |
| `` `CLAIMED` `` | Agent is working on it (TaskList: `in_progress`, owner set) | `- [ ] \`CLAIMED\` **Task N:** ...` |
| `` `DONE` `` | Verified complete (TaskList: `completed`) | `- [x] \`DONE\` **Task N:** ...` |
| `` `BLOCKED` `` | Dependency not met (TaskList: blockedBy non-empty) | `- [ ] \`BLOCKED\` **Task N:** ...` |
| `` `FAILED` `` | Attempted, needs attention (TaskList: `in_progress`, see description) | `- [ ] \`FAILED\` **Task N:** ...` |

**CLAIM BEFORE WORK:** Before starting ANY task:
1. `TaskUpdate({ taskId, status: "in_progress", owner: "<your-id>" })`
2. Edit this file to change `` `OPEN` `` to `` `CLAIMED` ``

**On success:** `` `DONE` `` in file + `TaskUpdate({ status: "completed" })`.
**On failure:** `` `FAILED` `` in file + leave `in_progress` in tracker with diagnostic in `description`.

**SKIP CLAIMED:** If you see `` `CLAIMED` `` — another agent owns it. Skip to the next `` `OPEN` `` task.

**DEPENDENCY SPEC:** Items with `| depends: X, Y` suffix are only dispatchable when X and Y are `` `DONE` ``. Mirror via `addBlockedBy`.

**AUTO-DISPATCH (fractal plans):** If this plan references sub-plans (other `00-wave-plan.md` files) and multiple items are dispatchable (deps met + status `` `OPEN` ``), spawn parallel agents — one per dispatchable item. Each agent claims its item, executes the sub-plan autonomously, and reports back. Max 6 concurrent agents.

### Walk Order

1. **Bootstrap the task tracker** (see above).
2. **Scan for dispatchable items** — all `` `OPEN` `` items whose dependencies are `` `DONE` ``.
3. **If 1 dispatchable:** Claim it (tracker + file) and execute directly.
4. **If 2+ dispatchable:** Spawn parallel background agents (one per item). Monitor via `TaskList`. Re-scan after each completion.
5. **For each task (sequential within a phase):**
   - Claim it: `` `OPEN` `` → `` `CLAIMED` ``, `TaskUpdate({ status: "in_progress" })`
   - Check the `Agent:` line — use the specified model tier.
   - Read the phase file referenced for full details.
   - **Check Verify-Before hooks** — if any fail, fix.
   - Execute using TDD (failing test → implement → verify).
   - Run the task-specific test command.
   - **Check Verify-After hooks** — if any fail, fix before committing.
   - If all pass, commit.
   - Mark done: `- [x] \`DONE\`` + `TaskUpdate({ status: "completed" })`.
   - Immediately continue to the next `` `OPEN` `` task.
6. **For CHECKPOINT tasks:**
   - Run the test suite specified.
   - If tests FAIL: fix, re-run, commit fixes.
   - Run code review via `superpowers:requesting-code-review`.
   - Only mark `` `DONE` `` when BOTH tests AND review pass.
7. **Compact aggressively** after each task or task group.
8. **NEVER stop between tasks.** Only stop for impossible blockers or user interruption.

### Completion

When every task and checkpoint is `` `DONE` `` (file) and `completed` (TaskList):
- Final task outputs a one-paragraph completion summary covering: feature shipped, tests passing, commits, follow-ups
- No `<promise>` tag, no max-iterations check, no external loop runner
- The combination of all-`[x]` checkboxes + all-`completed` tracker entries IS the completion signal

---

## Overview

**Goal:** [One sentence]

**Architecture:** [2-3 sentences — pulled from the architect's blueprint]

**Original Reference:** [Link to original plan file(s) if preserved]

---

## Architect Notes

Patterns and conventions surfaced by `feature-dev:code-architect` during Stage 1.5b:

- **Patterns found:** {bullets with file:line references}
- **Similar features referenced:** {paths}
- **Architecture decision:** {one decisive choice}
- **Deviations from input plan:** {if any — what changed and why}

(If empty: "Plan was doc/config only — architect dispatch skipped.")

---

## Cross-Plan Dependencies

Plans this feature depends on or blocks:

| Plan | Relationship | Status | Impact |
|------|-------------|--------|--------|
| `plans/path/to/dependency.md` | Depends on | Done/Active/Blocked | What this plan needs from it |
| `plans/path/to/blocked.md` | Blocks | Pending | What it needs from this plan |

**Dependency verification (at plan generation time):**
- [x] All `Depends on` plans exist and are in correct state
- [x] No circular dependencies detected
- [x] Blocking plan outputs are available

---

## Stale Alerts

Files modified in git AFTER this plan was created ({PLAN_DATE}):

| File | Last Modified | Commit | Impact |
|------|--------------|--------|--------|
| `path/to/file.py` | YYYY-MM-DD | `abc1234: "commit msg"` | May affect Task N — verify assumption X |

If empty: "No files modified since plan creation. Codebase assumptions are current."

---

## Task Checklist

### Phase 1: Phase Title (`YYYY-MM-DD-phase-1-description.md`)

- [ ] `OPEN` **Task 0:** [S] Short descriptive title (parallel)
  - Agent: `model: "sonnet"` — straightforward implementation
  - Test: `exact test command`
  - Files: `file1.py`, `file2.py`
  - Hooks: 2 pre / 3 post

- [ ] `OPEN` **Task 1:** [S] Short descriptive title (parallel)
  - Agent: `model: "sonnet"` — test + implementation
  - Test: `exact test command`
  - Files: `file1.py`, `tests/test_file.py`
  - Hooks: 2 pre / 3 post

- [ ] `OPEN` **CHECKPOINT Phase 1:** [O] Run tests + code review
  - Agent: `model: "opus"` — cross-file review requires architectural judgment
  - Test: `{PROJECT_TEST_COMMAND} tests/<relevant>/ -v`
  - Review: Run `superpowers:requesting-code-review` for all Phase 1 files
  - **Gate:** Do NOT proceed to Phase 2 until tests pass AND review is clean

### Phase 2: Phase Title (`YYYY-MM-DD-phase-2-description.md`) | depends: Phase 1

- [ ] `OPEN` **Task 2:** [S] Short descriptive title
  - Agent: `model: "sonnet"` — single-file implementation
  - Test: `exact test command`
  - Files: `file.py`
  - Hooks: 1 pre / 2 post

- [ ] `OPEN` **CHECKPOINT Phase 2:** [O] Run tests + code review
  - Agent: `model: "opus"` — cumulative review across phases
  - Test: `{PROJECT_TEST_COMMAND} (cumulative — includes earlier phases)`
  - Review: Run `superpowers:requesting-code-review` for all Phase 2 files
  - **Gate:** Do NOT proceed to Phase 3 until tests pass AND review is clean

[... more phases ...]

### Final Phase: Verification (`YYYY-MM-DD-phase-N-verification.md`)

- [ ] **Task N-1:** [S] Full regression suite
  - Agent: `model: "sonnet"` — running tests is mechanical
  - Test: Full project verification commands

- [ ] **FINAL CHECKPOINT:** [O] Full test suite + final code review
  - Agent: `model: "opus"` — final review must be highest quality
  - Test: `{PROJECT_TEST_COMMAND} (full suite)`
  - Review: Run `superpowers:requesting-code-review` for ALL changed files
  - **Gate:** ALL tests must pass AND review must be 100% clean

- [ ] **Task N:** [H] Output completion summary
  - Agent: `model: "haiku"` — trivial output task
  - When ALL tasks AND ALL checkpoints pass: print a one-paragraph summary covering shipped feature, tests, commits, follow-ups. No promise tag.

---

## Execution Notes

- **Branch:** Stay on current branch — NEVER switch branches
- **Each task:** TDD (write failing test → implement → verify hooks → commit)
- **Verification hooks:** Check `Verify-Before` BEFORE each task, `Verify-After` AFTER each task
- **Phase gates:** Tests + code review must BOTH pass before crossing phase boundary
- **Phase dependencies:** [Document which phases depend on which]
- **NEVER STOP:** Execute all tasks continuously. Only stop for truly impossible blockers.

## Agent Delegation

**Every task in the master plan MUST specify its agent model tier.** Assign the cheapest model that can handle the task — use Opus only when the task requires complex reasoning or cross-file architectural judgment.

| Tier | Model | Use For |
|------|-------|---------|
| **H** | Haiku | File reads, formatting checks, collecting info, simple search |
| **S** | Sonnet | Code generation, test writing, single-file edits, small reviews |
| **O** | Opus | Architecture decisions, cross-file integration, final reviews, plan hardening |

**Task format with agent tier:**
```
- [ ] **Task N:** [S] Short descriptive title
  - Agent: `model: "sonnet"` — reason for tier choice
  - Test: `exact test command`
  - Files: `file1.py`, `file2.py`
  - Hooks: N pre / M post
```

**Parallelism rules:**
- Tasks within a phase that don't depend on each other → launch as parallel agents in a single message
- Mark parallel-safe tasks with `(parallel)` in the master checklist
- CHECKPOINT tasks are always sequential (they gate the next phase)
- Prefer N parallel Sonnet agents over fewer sequential Opus agents

**Tier assignment guidelines:**
- Writing a test file → **S** (Sonnet)
- Implementing a function/class → **S** (Sonnet)
- Wiring an API endpoint → **S** (Sonnet)
- Adding type definitions → **S** (Sonnet), or **H** (Haiku) if purely mechanical
- Reading files to collect info for a task → **H** (Haiku)
- Cross-file refactor touching 5+ files → **O** (Opus)
- CHECKPOINT (test + review as single task) → **O** (Opus) — review requires cross-file judgment
- Final integration review → **O** (Opus)
- Resolving conflicting patterns across modules → **O** (Opus)
````

**Master plan rules:**
- **The kickoff prompt MUST be a single concise line** — just `"Execute plans/<plan-name>/00-master-plan.md"`. All execution logic goes in the "Execution Rules" section of the master plan file itself.
- Every task has: checkbox, status tag, bold task number, agent tier `[H|S|O]`, title, agent line, test command, file list, hook counts
- **CHECKPOINT** tasks are BLOCKING GATES — tests pass + code review clean before next phase
- Final checkpoint reviews ALL changed files across entire feature
- Last task outputs a completion summary (no `<promise>` tag, no `ALL X COMPLETE` sentinel)
- **Test commands must match the project's actual test infrastructure** — detect from CLAUDE.md, existing test configs, or directory structure
- **No external loop runner** — no `/ralph-loop`, no `/meta-loop`, no `--max-iterations`, no `--completion-promise`. Execution is the in-session walk plus the task tracker.

### Stage 3.5: Generate Loop-Gap Configuration

Create `.loop-gap-config.md` in the plan directory. This file pre-configures `/loop-gap` so it can scan this plan with zero manual setup.

````markdown
# Loop-Gap Configuration for {PLAN_NAME}

> Auto-generated by `/meta-planner`. Used by `/loop-gap` when scanning this plan directory.

## Scan Settings

```yaml
mode: plan
target: plans/<plan-name>/
plan_date: YYYY-MM-DD
git_baseline: {SHA_AT_GENERATION}
```

## Codebase Verification Targets

| File | Referenced By | Action | Signature Snapshot |
|------|-------------|--------|-------------------|
| `app/services/foo.py` | phase-1, Task 0 | Modify | `def process(data: dict) -> bool` [line 42] |
| `tests/test_foo.py` | phase-1, Task 0 | Test | `class TestFoo` [line 8] |
| `app/models/bar.py` | phase-2, Task 3 | Create | (new file) |

## Affected Files (callers/dependents of modified files)

| File | Depends On | Relationship |
|------|-----------|-------------|
| `app/routes/api.py` | `app/services/foo.py` | `from app.services.foo import process` [line 5] |

## Verification Hooks Summary

| Phase | Tasks | Pre-hooks | Post-hooks |
|-------|-------|-----------|------------|
| Phase 1 | 3 | 6 | 9 |
| Phase 2 | 2 | 4 | 6 |
| **Total** | **N** | **M** | **K** |

## Role Agent Focus Areas

| Role | Focus |
|------|-------|
| Implementer | {specific areas where instructions may be ambiguous} |
| Tester | {specific test coverage concerns — edge cases, error paths} |
| Consumer | {specific API contracts or interfaces this plan exposes} |

## Gap Categories to Prioritize

```
{PRIORITIZED_CATEGORIES}
```

(e.g., template-heavy plan → prioritize `codebase_mismatch`, `stale_assumption`; new APIs → prioritize `contract`, `test_validity`, `import_chain`)
````

**Loop-gap config rules:**
- **Signature snapshots from actual file reads** — never guess
- **Affected files from actual grep results** — never assume
- **Role focus areas specific** — not generic "check for bugs"
- **Prioritized categories match plan character**

### Stage 4: Validate the Output

Before presenting the restructured plan, verify:

**Structural:**

1. Every task has a test command
2. Every task has file paths
3. Phase files match master checklist
4. **No external loop runner referenced** — no `/ralph-loop`, `/meta-loop`, `--max-iterations`, `--completion-promise`, `<promise>` tags
5. Kickoff prompt is a single short line — all logic in master plan file
6. Dependencies respected — prerequisites come first
7. No orphan tasks — every phase-file task appears in master checklist
8. Commit messages follow convention (`feat:`, `fix:`, `refactor:`, `test:`)
9. Every phase has a checkpoint
10. Checkpoint test commands are phase-cumulative
11. Final checkpoint reviews ALL files
12. Test commands are project-appropriate
13. Every task has an agent tier `[H]`/`[S]`/`[O]`
14. Agent tiers are appropriate
15. Parallel-safe tasks marked `(parallel)`

**Architect grounding:**

16. `## Architect Notes` section exists (or "skipped — doc-only")
17. File paths in phase files match architect's Implementation Map
18. Phase boundaries reflect architect's Build Sequence

**Codebase verification:**

19. Every `Modify:` file exists
20. Every `Create:` file's parent directory exists
21. Function/class signatures match codebase
22. All callers of modified functions documented
23. Stale alerts populated (or explicit "no stale files")

**Verification hooks:**

24. Every task has Verify-Before hooks
25. Every task has Verify-After hooks
26. Verify-Before for Task N references outputs of Task N-1
27. Verify-After includes caller checks

**Loop-gap config:**

28. `.loop-gap-config.md` exists
29. Signature snapshots from actual reads
30. Affected files from actual grep
31. Role focus areas specific

**API contract (full-stack only):**

32. Contract table exists
33. Every endpoint has both sides
34. Pagination pattern consistent
35. Verify-After hooks reference contracts
36. Existing endpoints verified against code

**Execution model:**

37. Master plan instructs TaskCreate bootstrap
38. Dual source of truth wired (checkbox + tracker)

### Stage 5: Present Result

After creating all files, output:

```
Plan restructured into execution-ready format:

Master plan: plans/<name>/00-master-plan.md
Phase files: N files created
Total tasks: N tasks + M checkpoints across P phases
Quality gates: M test+review checkpoints embedded
Verification hooks: X pre-hooks + Y post-hooks across all tasks
Codebase files verified: Z files read and validated
Architect blueprint: applied (or skipped — doc-only plan)
Affected files tracked: W callers/dependents documented
Loop-gap config: plans/<name>/.loop-gap-config.md (ready for /loop-gap)
Execution model: TaskCreate-driven, dual source of truth (file checkboxes + task tracker)
Stale alerts: K files modified since plan date (or "none")

To execute:
  1. Run /loop-gap plans/<name>/ to harden the plan
  2. When clean, ask Claude to: "Execute plans/<name>/00-master-plan.md"
```

---

## Task Granularity Guidelines

**Each task should be 2-5 minutes of focused work:**
- "Write the failing test for X" — one task
- "Implement minimal code to pass the test" — one task
- "Add type definitions" — one task
- "Wire the API endpoint" — one task

**NOT acceptable:**
- "Implement the entire backend" — too big, split
- "Fix everything" — not specific
- "Write tests" — which tests?

**Splitting heuristic:** If a task touches more than 3 files, consider splitting.

---

## Verification Hook Guidelines

**Verify-Before (preconditions):**

| Hook Type | Example | When |
|-----------|---------|------|
| File exists | `app/services/foo.py` exists | Every `Modify:` file |
| Signature check | `def process(data: dict)` at ~line 42 | When modifying a specific function |
| Import resolves | `from app.models import Bar` resolves | When task depends on another module |
| Prior task complete | Tasks 0-2 are complete | When task has dependencies |
| No uncommitted changes | `git status` clean for task files | Always |
| External dependency | Database migration N applied | When task depends on external state |

**Verify-After (postconditions):**

| Hook Type | Example | When |
|-----------|---------|------|
| Tests pass | `{PROJECT_TEST_COMMAND} tests/test_foo.py -v` | Always |
| Signature updated | `def process(data: dict, mode: str)` now exists | When modifying signatures |
| Callers work | All importers of `process()` still pass tests | When modifying public interfaces |
| Type check | `{TYPE_CHECK_COMMAND}` passes | When changing types/interfaces |
| No unintended changes | `git diff` shows only expected files | Always |
| No regressions | Broader test suite still passes | When changes might cascade |

**Hook writing rules:**
- Be specific — `def process(data: dict)` not "the process function"
- Include line numbers where possible — `at ~line 42`
- Reference actual codebase state — from Stage 1.5 + 1.5b
- Keep hooks checkable in < 5 seconds each
- Group related hooks — don't have 10 when 3 cover the same ground

---

## Handling Different Input Formats

### Single monolithic plan file
- Split into phases by logical groupings (informed by architect's Build Sequence)
- Preserve original as `YYYY-MM-DD-original-reference.md`
- Create phase files with extracted tasks
- Run Stage 1.5 + 1.5b on all referenced files

### Multiple unstructured files
- Read all, merge understanding
- Identify the canonical task list
- Restructure into phase files + master plan
- Run Stage 1.5 + 1.5b — collect file references from ALL input files

### Already-structured plan directory
- Read all files, assess structure
- If already execution-ready: report "Plan already structured" and suggest improvements only
- If partially structured: fill gaps (missing tests, file paths, commits, checkpoints, **verification hooks**, **codebase snapshots**, **architect notes**, **TaskCreate bootstrap rules**)
- If contains ralph-loop / meta-loop / `<promise>` artifacts: strip them, replace with TaskCreate execution rules

### Plans without test commands
- Detect project test infrastructure from CLAUDE.md, `package.json`, `pyproject.toml`, `Makefile`, or existing test files
- Infer test commands from file paths and task types
- If truly untestable: `Test: Manual — [specific verification step]`

---

## Learned Patterns

<!-- Auto-maintained by the improvement loop. Generalized only — no project-specific entries. -->
<!-- Max 20 patterns per command. meta-audit enforces cap via consolidation. -->
<!-- Append-only for this command — only meta-audit removes patterns. -->

(No patterns yet. Patterns are added automatically when downstream commands detect recurring issues across 3+ separate plans.)

---

## Phase Checkpoint Details

Phase checkpoints are quality gates ensuring:

1. All tests pass — phase-specific regression suite
2. Code review clean — `superpowers:requesting-code-review`
3. No regressions — later checkpoints include earlier suites
4. All Verify-After hooks passed

**Checkpoint behavior:**
- If tests fail: fix, re-run, commit fix — KEEP GOING
- If review has findings: fix, re-test, re-review — KEEP GOING
- Only check off when BOTH tests AND review pass
- NEVER stop after a checkpoint — continue to next phase

**Checkpoint test escalation:**
```
Phase 1: {PROJECT_TEST_COMMAND} tests/test_feature_*.py -v        (narrow)
Phase 2: {PROJECT_TEST_COMMAND} tests/test_feature_*.py tests/test_api_*.py -v  (wider)
Phase 3: {PROJECT_TEST_COMMAND} tests/ -v                         (full suite)
Final:   {PROJECT_TEST_COMMAND} (everything) + type checks
```

---

## Cross-Plan Dependency Validation

When generating the master plan, check for cross-plan dependencies:

1. Read plan frontmatter for `Depends on:` and `Blocks:`
2. Verify each dependency exists
3. Check status: Done → OK; Active → risk; Blocked → blocker; missing → critical gap
4. Check for circular dependencies (A→B→A)
5. Verify dependency outputs available (files exist, APIs deployed, etc.)
6. Document in master plan's `## Cross-Plan Dependencies` table

---

## Example: Restructuring a Flat Plan

**Input:** A single `2026-02-22-add-widget.md` with 12 tasks in a flat list

**Output:**
```
plans/add-widget/
├── 00-master-plan.md                          (checklist + TaskCreate execution rules)
├── .loop-gap-config.md                        (gap scanner config)
├── 2026-02-22-phase-1-backend-model.md        (Tasks 0-2: models)
├── 2026-02-22-phase-2-backend-api.md          (Tasks 3-5: API endpoints)
├── 2026-02-22-phase-3-frontend-types.md       (Tasks 6-7: types)
├── 2026-02-22-phase-4-frontend-ui.md          (Tasks 8-10: components)
├── 2026-02-22-phase-5-verification.md         (Tasks 11-12: integration tests)
└── 2026-02-22-original-reference.md           (original plan preserved)
```

Master checklist: 12 tasks + 5 phase checkpoints + 1 final = 18 checklist items
Execution: Self-contained master plan, TaskCreate-driven, dual source of truth (file checkboxes + task tracker)
Architect blueprint: applied (Stage 1.5b)
Verification hooks: ~36 pre-hooks + ~48 post-hooks
Codebase files verified: 15 files read
Loop-gap config: ready for `/loop-gap plans/add-widget/`
