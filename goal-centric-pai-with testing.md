# Goal-Centric PAI — Requirements & Design Intent

This document captures the product and engineering requirements for making **Goals the center of PAI**. It is the canonical reference before implementation. Do not treat this as an implementation spec with file paths — it defines **what** PAI must do and **what to avoid**.

---

## 1. Product vision

PAI should clearly understand what the user is trying to achieve, know which goal they are currently talking about, allow multiple concurrent goals, and keep each goal's research, requirements, progress, plan, and next steps **separate**.

Once a goal is understood, PAI gradually builds useful intelligence around it:

- research options
- understand requirements
- compare requirements with the user's situation
- identify what is missing
- create a plan
- keep information updated when something relevant changes

Heavy research and analysis happen **in the background** so normal chat stays fast. PAI only does expensive work when the user actually needs it. The counselor uses a **short, reliable summary** of everything PAI knows about the **active goal** when answering.

**Conversion target:** from an agent-heavy, unpredictable, turn-by-turn reasoning system → to a **goal-centric, persistent, background-computed counseling system**.

---

## 2. Non-negotiable principles

### Do

- One **canonical way** to understand and update goals (single source of truth).
- **Fast chat path** — user message gets an immediate reply.
- **Background intelligence** — research/assessment/gaps/planning run asynchronously.
- **Incremental enrichment** — update only what needs updating when circumstances change.
- **Domain-agnostic goals** — admission (MS/BS/PhD, local/foreign), jobs, internships, and future types.
- **Additive evolution** — reuse existing Goal table, Vault, tasks, document worker pattern, chat orchestrator.
- **Chat survives background failure** — pipeline fail/slow ho to bhi chat chalti rahe.

### Do not (early)

- Rebuild everything from scratch.
- Create duplicate systems for goals, tasks, jobs, memory, and events.
- Turn every university, job, country, or idea the user mentions into a separate goal.
- Run multi-agent conversations (workers talking to each other).
- Run the full research-and-planning pipeline on every casual mention.
- Slow every chat message with mandatory extra AI reasoning before replying.
- Introduce workflow engines, elaborate milestone/progress frameworks, or large new architectures before the basic flow works.

### Basic flow (must work first)

```
understand the goal
  → keep the right goal active
  → gather useful information
  → assess the user against it
  → create useful next steps
  → update only what needs updating when circumstances change
```

---

## 3. High-level architecture

```
User message
  │
  ├─► [SYNC] Goal detect / switch / minimal create-update
  ├─► [SYNC] Attach active goal to conversation
  ├─► [SYNC] Counselor reply (Vault + active goal brief if available)
  │
  └─► [ASYNC] Enqueue goal intelligence job (if goal created/updated/activated)
           │
           ▼
      Research → Assessment → Gaps → Planning
           │
           ▼
      Compact goal intelligence summary saved
           │
           └─► Future chats reuse summary (no re-research unless stale)
```

**Rule:** Background pipeline output is an **enhancement**, not a **dependency** for chat.

---

## 4. Synchronous path (chat — must stay fast)

On every user message, only this runs inside the request:

### 4.1 Goal resolver

Decide:

- Does this relate to an **existing goal**?
- Does it introduce a **new goal**?
- Which goal should be **active** for this thread?

Use existing cheap signals where possible (fact extraction output, entity mentions, prior active goal). **No extra mandatory LLM call** for goal switching.

### 4.2 Minimal goal write

When a goal is detected with sufficient confidence:

- Create or update a **Goal record** immediately.
- Store only identity-level anchors: title, type, key fields (country, degree, role, company, intake, etc.).
- Set status: `draft` | `proposed` | `active`.

Do **not** run research, web search, or full assessment in this path.

### 4.3 Active goal link

Each conversation/thread carries an **active goal** pointer (e.g. `active_goal_id`).

- Default: continue with the current active goal.
- Switch: when the message clearly references another goal.
- Ambiguous: keep active goal; ask **at most one** clarifying question if needed.

### 4.4 Counselor reply

Counselor reads:

- Person Vault + typed profile (`known_facts`, `missing_critical_fields`)
- **Active goal brief** (if available)
- Active goal status (`draft`, `research_pending`, `ready`, `partial`, `stale`, `failed`)

If brief is not ready yet, counsel from known facts and goal anchors anyway — do not block or say "please wait."

---

## 5. Asynchronous path (background intelligence)

When a goal is created, materially updated, or activated:

1. Enqueue a **goal job** (same general pattern as document worker: DB-backed queue, poll loop, retries).
2. Run staged workers — **no worker-to-worker chat**.

### 5.1 Pipeline stages

| Stage | Input | Output |
|-------|--------|--------|
| **Research** | Goal anchors + template | Requirements, options, eligibility rules, deadlines (structured) |
| **Assessment** | Research output + Vault snapshot | User vs requirements match (structured) |
| **Gaps** | Assessment output | Missing items for this goal (structured) |
| **Planning** | Gaps + research | Ordered next steps / plan (structured) |

Each stage reads the **previous stage's structured JSON** and writes its own section to the goal intelligence store. Workers do not call each other conversationally.

### 5.2 Final artifact: goal intelligence summary

Persist a compact object per goal, e.g.:

```json
{
  "goal_id": "...",
  "template_type": "admission",
  "research": {},
  "assessment": {},
  "gaps": [],
  "plan": [],
  "counselor_brief": "5–10 lines max — what counselor uses every turn",
  "status": "ready | partial | failed",
  "freshness": {}
}
```

Counselor uses **`counselor_brief`** plus a small structured subset — not raw research dumps.

### 5.3 Failure and slowness

- Chat **never waits** for background completion.
- If pipeline fails: goal status = `partial` or `failed`; chat continues normally.
- Retry in background; do not surface internal errors to the user unless useful.
- Summary missing → counselor uses Vault + goal anchors + natural questions for obvious gaps.

---

## 6. Robust goal detection (avoid false goals)

Goal create/activate **only** when:

- User expresses clear pursuit intent: "I want MS in Germany", "looking for SWE internship", "applying for X".
- Strong structured signal with **high confidence**.

Do **not** create or switch active goal when:

- User only mentions a country, university, or job name without pursuit intent.
- Message is a casual question ("what is life like in Germany?").
- Message is about **steps inside a goal** ("should I take IELTS first or passport first?").
- Message is profile correction or fact sharing ("my CGPA is 3.4", "I got 7.5 in IELTS").

**Low confidence:** create `draft`/`proposed` only, or skip creation; do not switch active goal; one clarifying question at most.

---

## 7. Data ownership: Vault vs Goal

### 7.1 Vault (person-level, shared)

Facts about the **person**, not a specific pursuit:

- IELTS / TOEFL / GRE / other test scores
- CGPA, education history, skills, work history
- Nationality, current country/city, passport status
- General budget preference (when globally relevant)

**Rule:** IELTS score lives in Vault once. All goals that need it reuse it — user is not asked again.

### 7.2 Goal record (pursuit-specific)

Per goal:

- Target country / program / university / intake / budget (admission)
- Target role / company / location (job/internship)
- Goal-specific requirements snapshot (from research)
- Assessment, gaps, plan, next steps for **this goal only**
- Compact counselor brief

### 7.3 Selective refresh on Vault update

When Vault changes (e.g. new IELTS score):

1. Determine which goals are **affected** by that fact (e.g. goals whose requirements include language tests).
2. Re-run **Assessment → Gaps → Planning** (and Research only if stale) for those goals only.
3. Do not recompute unrelated goals or rerun full pipeline globally.

---

## 8. Multiple goals: independent but reusable

Three layers — do not mix them:

| Layer | Example | Behavior |
|-------|---------|----------|
| **Separate goals** | Germany MS, China MS, Dubai job | Independent records, summaries, plans |
| **Shared profile** | IELTS, CGPA, passport | Single Vault source |
| **Shared steps/tasks** | "Take IELTS", "Prepare CV" | One task/action, linked to multiple goals |

- "IELTS pehle ya passport pehle?" = **steps inside one goal's plan**, not a new goal.
- Germany and China = **two goals** even if both need IELTS.
- Shared task: created once, linked to all goals that need it; user not asked twice.

---

## 9. Goal type templates

**Decision: hybrid — small template set + general fallback.** Not one generic template for everything; not dozens of templates upfront.

### MVP templates

| Type | Anchors (required-ish) | Notes |
|------|------------------------|--------|
| `admission` | degree level, country, program, intake, budget | MS/BS/PhD, local/foreign |
| `job` | role, location, company type, experience level | full-time, local/foreign |
| `internship` | role, location, duration, paid/unpaid | |
| `general` | title, description | **Fallback** for unknown types |

Templates guide:

- which fields to extract/store on the goal
- what Research/Assessment should look for
- how to structure gaps and plan

**Unknown type:** use `general` — no crash; broad research; simple plan. When a pattern repeats (e.g. PR/citizenship, business start), add a dedicated template later without migrating old data.

---

## 10. Chat and counselor integration

- Every reply is grounded in **active goal** context when a goal is active.
- Counselor prompt receives `active_goal_brief` (and status), not full raw pipeline output.
- Missing items from gaps → counselor asks **conversationally** (no hardcoded forms).
- Existing rules remain: do not re-ask `known_facts`; use `missing_critical_fields` when advice depends on a gap.
- `/chat` API shape and fast orchestrator path stay intact; context pack gains goal fields additively.

---

## 11. Fit with current codebase (reuse, don't duplicate)

| Existing piece | Role in goal-centric PAI |
|----------------|---------------------------|
| `goals` table (`Goal` model) | Canonical goal identity |
| Vault + typed profile | Person-level facts; selective refresh triggers |
| Chat orchestrator + counselor agent | Fast reply path unchanged |
| `document_worker_loop` + job queue pattern | Model for goal intelligence worker |
| `StudentTask` | Shared actions / next steps (link to goals) |
| Vault Intelligence / fact extraction | Cheap signals for goal resolver; not a second goal brain |
| Semantic memory | Insights/preferences — not replacement for goal summary |

**Known gap today:** typed apply may treat career interest as a single canonical goal — multi-goal design must evolve this without breaking chat.

---

## 12. MVP success criteria

1. User says "MS CS in Germany" → goal record created; chat replies immediately.
2. Thread stays on Germany goal until user mentions another pursuit.
3. Background job produces and saves goal intelligence summary.
4. Next message on same goal uses saved brief — no duplicate research.
5. User adds "MS in China" → separate goal; switch when context clear.
6. User gives IELTS score → Vault updated; Germany + China goals refresh assessment only.
7. Background pipeline fails or is slow → chat still works; counselor uses known facts.

---

## 13. Explicitly deferred (until MVP works)

- Workflow engines and complex milestone/progress systems
- Many specialized templates beyond admission / job / internship / general
- Multi-agent orchestration or agent-to-agent messaging
- Automatic goal creation from every entity mention
- Blocking chat on intelligence pipeline completion
- Replacing Vault, tasks, or memory with parallel goal-specific copies

---

## 14. Testing methodology

Once the goal-centric flow above is implemented, it should be tested in layers, each layer catching a different class of risk called out earlier in this document.

### 14.1 Goal detection — unit tests against a labeled fixture set

This is the highest-risk piece (section 6 — avoiding false goals), so it gets its own regression suite before anything else. Build a fixture file of representative messages with expected outcomes:

```python
# tests/goals/fixtures/detection_cases.json
[
  {"message": "I want to do MS CS in Germany", "expect": "create", "type": "admission"},
  {"message": "what is life like in Germany?", "expect": "none"},
  {"message": "should I take IELTS first or passport first?", "expect": "none"},  # step inside goal, not new goal
  {"message": "my CGPA is 3.4", "expect": "none"},  # vault fact, not goal
  {"message": "looking for a SWE internship in Dubai", "expect": "create", "type": "internship"},
  {"message": "actually thinking about China too", "expect": "create_secondary"}  # second goal, doesn't replace active
]
```

Run every case through the resolver and assert on the decision, not the exact wording of any generated text. This suite should be rerun on every change to detection logic — it is what actually validates "we don't create false goals" instead of just asserting it in a design doc. New misclassifications found in real use should be added here as regression cases rather than only fixed and forgotten.

### 14.2 `GoalService` — unit/service tests

Test the mutator directly, bypassing the LLM entirely (pass in a pre-decided detection result): create, update-in-place vs. create-new, activate, switch. Assert Vault-owned fields (IELTS, CGPA) never get written onto a Goal record — this is the section 7 boundary, and it is cheap to test with a simple "goal record must not contain these keys" assertion.

### 14.3 Pipeline stages — isolated fixture tests

Since each stage reads the previous stage's structured output and writes its own (section 5.1), they are naturally unit-testable in isolation without running the full worker:

```python
async def test_gaps_stage_flags_missing_ielts():
    assessment_output = {"ielts": {"required": 6.5, "user_has": None}}
    gaps = await run_gaps_stage(assessment_output)
    assert any(g["category"] == "test_score" and g["blocking"] for g in gaps)
```

Mock DeepSeek/Tavily at this layer with fixed responses so these tests are deterministic and do not burn API calls or flake on network.

### 14.4 Worker/queue integration

Mirror however the existing document worker is tested. Structure the goal worker with a directly-callable `process_job(job_id)` separate from the poll loop, and call it synchronously in tests — no sleeping, no waiting on a background thread:

```python
async def test_pipeline_produces_ready_summary(db_session):
    goal = await create_goal(db_session, ...)
    job = await enqueue_goal_job(db_session, goal.id)
    await process_job(job.id)  # runs all 4 stages synchronously
    summary = await get_goal_summary(db_session, goal.id)
    assert summary["status"] == "ready"
    assert len(summary["counselor_brief"].splitlines()) <= 10
```

The line-count assertion is worth keeping permanently — it is the one hard constraint from section 5.2 (5–10 lines) that is easy to silently violate later.

### 14.5 Chat must not block on the pipeline

Use a fake queue that records the enqueue call but never processes it, then assert the `/chat` response returns and contains a reply even though the job is still pending:

```python
async def test_chat_replies_before_pipeline_completes(client, fake_queue):
    resp = await client.post("/api/v1/chat", json={"message": "I want MS CS in Germany"})
    assert resp.status_code == 200
    assert resp.json()["data"]["reply"]  # got a reply
    assert fake_queue.enqueued  # job was queued
    assert not fake_queue.processed  # but not run inline
```

Also test the failure path explicitly: force the worker to raise, and assert chat on a follow-up message still responds normally with goal status `failed`/`partial` rather than propagating the error to the user (section 5.3).

### 14.6 Selective refresh — Vault → affected goals only

Create two goals (one that needs IELTS, one that does not), update the Vault's IELTS field, and assert only the dependent goal's Assessment/Gaps/Planning reran — check `updated_at` or a job-count counter on both goals to confirm the unaffected goal was not touched (section 7.3).

### 14.7 API/contract tests for goal endpoints

Standard request/response tests for the goal list/detail/activate endpoints, in the same pattern as existing onboarding/vault route tests. Explicitly assert response shape includes `feasibility` and typed `gaps` with `category`/`blocking` fields, since these are easy to omit in a serializer.

### 14.8 End-to-end scenario tests — the MVP success criteria

Section 12's success criteria are effectively acceptance criteria. Turn each into one integration test against a real (or test) Postgres, hitting `/chat` through the actual HTTP layer with DeepSeek mocked:

- goal created + immediate reply
- thread stays on goal until explicit switch
- background job produces summary
- second message reuses saved brief (assert no second pipeline run — mock call-count assertion)
- second goal created and switched to correctly
- IELTS update refreshes both dependent goals only
- pipeline failure does not break chat

Keep this layer small — one test per criterion, not a combinatorial explosion — and let the fixture-based unit tests in 14.1–14.3 carry the bulk of coverage.

---

## 15. One-line summary

PAI is a **multi-goal-aware counselor** with a **single canonical goal state**, **fast conversational path**, **on-demand background intelligence**, and a **small template set with general fallback** — chat always works; intelligence catches up in the background.
