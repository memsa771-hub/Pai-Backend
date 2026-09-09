# PAI Vault Structure & Testing Guide

This guide explains how to understand, trace, and test the complete Vault structure in the `monolith` branch.

The key idea is to treat the Vault not as one module, but as a **data pipeline with observable checkpoints**:

**Source → Intelligence → Candidate → Validation/Gate → Writer → Storage → Evidence/History → Consistency → Readback → Other Modules**

---

# 1. Complete Vault Structure as a Pipeline

| Checkpoint | What happens | Main code | What you should inspect |
|---|---|---|---|
| **0. Bootstrap** | Student + Vault are created | `person/service.py`, `person/models.py` | `persons`, `person_vaults`, catalog version, scopes |
| **1. Source** | Information enters from chat, onboarding, document, API | `workflows/onboarding/`, `intelligences/vault/sources/`, document pipeline | Original text/document, `source_reference`, source type |
| **2. Vault Intelligence** | PAI identifies possible student facts | `intelligences/vault/service.py`, `llm_extractor.py`, `boosters.py` | Raw extracted candidates |
| **3. Normalize / Ground / Merge** | Aliases corrected, evidence grounded, duplicates merged, non-Vault observations separated | `normalize.py`, `ground.py`, `merge.py`, `formation.py` | Final `VaultCandidate[]` |
| **4. Candidate Gate** | Determines whether candidate is valid Vault truth | `kernel/evidence/assertion.py`, `candidate_eval.py`, `policy/verifier.py` | `accept`, `reinforce`, `pending`, `conflict`, `reject` |
| **5. Writer** | Accepted candidate is dispatched to correct owner/storage | `student/public.py → VaultWriter`, `vault_apply.py` | Which storage path was selected |
| **6A. Sparse Write** | Simple field written to `vault_values` | `vault/service.py`, `vault_apply.py` | active/superseded `VaultValue` |
| **6B. Typed Write** | Education/work/tests/etc. written to native table | `typed_apply.py`, `handlers/*` | Education/Skill/TestAttempt/etc. row |
| **7. Evidence + History** | Provenance and changes are attached | `VaultEvidence`, `VaultHistory`, `student/evidence.py` | correct source, evidence text, entity target |
| **8. Consistency** | Completion, issues, timelines, Vault version updated | `vault/completion.py`, `education/timeline.py`, `issues/service.py` | completion %, issues, no duplicate entities |
| **9. Readback** | Unified student profile is reconstructed | `student/public.py`, `profile_snapshot.py` | `VaultSnapshot`, known facts, missing fields |
| **10. Consumers** | Counselor, Goals, Memory, Journey use changes | counseling workflow, goals, student-learning memory, journey | counselor sees update; goals stale appropriately; memory receives observation |

The Vault architecture is intentionally separated so that other modules interact through boundaries such as:

```text
VaultReader
VaultWriter
VaultSnapshot
```

instead of directly manipulating Student ORM objects.

---

# 2. Debug One Fact Through the Entire Pipeline

The most useful Vault test is to take **one real student statement** and follow the same fact from input all the way to downstream consumers.

Example input:

```text
I completed FSc Pre-Medical at Punjab College with 877/1100 in 2024.
```

## Checkpoint A — Did Intelligence Understand It?

Expected candidate should look approximately like:

```text
education.program
{
  degree: "FSc",
  major: "Pre-Medical",
  institution: "Punjab College",
  marks_obtained: 877,
  marks_total: 1100,
  graduation_year: 2024
}
```

Inspect:

```text
src/pai/intelligences/vault/
    service.py
    llm_extractor.py
    boosters.py
    normalize.py
    ground.py
    merge.py
    formation.py
```

If the candidate is already wrong here, the database is not the problem.

The issue is likely in:

- extraction
- prompt behavior
- normalization
- evidence grounding
- candidate merging

The current Vault Intelligence tests already cover:

- hallucination rejection
- empty-evidence rejection
- alias normalization
- deterministic vs LLM candidate merging
- keeping negated statements out of Vault
- keeping attributed statements out of the student's Vault
- separating non-Vault observations

---

## Checkpoint B — Did the Gate Accept It?

The candidate should then pass through the evaluation/policy layer.

Conceptually:

```text
candidate
   ↓
policy / assertion checks
   ↓
comparison with current Vault truth
   ↓
decision
```

Expected result for a clear explicit fact:

```text
outcome = accept
```

Main files:

```text
src/pai/kernel/evidence/assertion.py
src/pai/kernel/evidence/candidate_eval.py
src/pai/kernel/policy/verifier.py
```

Possible outcomes include:

```text
accept
reinforce
conflict
pending_confirmation
reject
```

Examples:

- explicit, well-grounded fact → `accept`
- same fact already stored → `reinforce`
- uncertain/inferred fact → `pending_confirmation`
- contradictory fact → `conflict`
- negated or attributed-to-someone-else fact → `reject`

If Intelligence produced the correct candidate but nothing gets written, this is one of the first places to inspect.

---

## Checkpoint C — Where Did the Writer Send It?

After acceptance, trace:

```text
VaultWriter
    ↓
process_candidates()
    ↓
catalog.storage
```

The catalog determines where the field belongs.

For:

```text
education.program
```

the write should go through:

```text
vault_apply.py
    ↓
typed_apply.py
    ↓
handlers/education.py
    ↓
educations table
```

For a simple sparse field such as:

```text
preferences.preferred_language
```

the write should go through:

```text
vault_apply.py
    ↓
VaultValue
    ↓
vault_values table
```

This distinction is very important.

If a field is not present in `vault_values`, that does **not** automatically mean the Vault failed.

Examples of typed storage:

```text
Education      → educations
Work           → work_experiences
Skills         → skills
Tests          → test_attempts
Projects       → projects
Certifications → certifications
Identity       → persons / related typed fields
```

---

# 3. After Every Write, Check Four Things

Do not only check whether the final value exists.

For every accepted Vault fact, verify these four things:

```text
VALUE
EVIDENCE
HISTORY
PROJECTION
```

Example for an education fact:

```text
educations
    ↓
VaultEvidence
    ↓
VaultHistory
    ↓
VaultSnapshot / completion
```

This allows you to identify very different classes of bugs.

Examples:

```text
Value saved           ✅
Evidence missing      ❌
```

This means persistence worked, but provenance failed.

```text
Value saved           ✅
History missing       ❌
```

This means current state is correct, but longitudinal tracking failed.

```text
DB correct            ✅
Vault snapshot stale  ❌
```

This means persistence worked, but the read/projection layer is stale or incomplete.

```text
Snapshot correct      ✅
Counselor sees old    ❌
```

This means Vault itself is fine, but downstream context generation/cache is wrong.

For typed entities, evidence and history should be attached to the correct entity and, where appropriate, the correct attribute.

---


When a real chat message fails, you currently have to manually determine which layer caused the problem.

What you really want is a trace like:

```text
SOURCE
  ✅ received message

INTELLIGENCE
  ✅ extracted education.program

NORMALIZATION
  ✅ normalized candidate

GROUNDING
  ✅ evidence found

GATE
  ✅ accepted

DISPATCH
  ✅ educations

ENTITY RESOLUTION
  ✅ matched Education #abc

WRITE
  ✅ percentage 79.73

EVIDENCE
  ✅ chat message m-123

HISTORY
  ✅ created

COMPLETION
  ✅ recomputed

SNAPSHOT
  ✅ shows FSc

COUNSELOR
  ✅ sees FSc
```

If something fails:

```text
SOURCE
  ✅

INTELLIGENCE
  ✅

GROUNDING
  ✅

GATE
  ❌ pending_confirmation

Reason:
candidate assertion_status = inferred
```

That immediately identifies the failure point.

This is much more useful than only seeing:

```text
AssertionError: expected 887, got 877
```

---

# 4. Add One Vault End-to-End Diagnostic Test

Add a dedicated diagnostic file:

```text
tests/test_vault_end_to_end_diagnostic.py
```

Its purpose should not only be to assert the final database state.

It should capture the complete trace for a fact.

Suggested diagnostic structure:

```json
{
  "input": "...",
  "source_reference": "...",
  "extraction": {},
  "normalized_candidates": [],
  "grounded_candidates": [],
  "gate_results": [],
  "writer_results": [],
  "db_state": {},
  "evidence": [],
  "history": [],
  "completion": {},
  "snapshot": {},
  "consumer_context": {}
}
```

Use the same:

```text
source_reference
message_id
document_id
```

where applicable across the entire trace.

Then every Vault failure becomes a sequence of simple questions:

```text
Was the input received?

Was the fact extracted?

Was the field key correct?

Was the candidate normalized?

Was its evidence grounded?

Did policy reject it?

Did candidate evaluation accept it?

Where did the catalog route it?

Did entity resolution match the correct record?

Was the database write successful?

Was evidence attached?

Was history written?

Was completion recalculated?

Was the snapshot rebuilt?

Did the Counselor see the new truth?

Were Goals invalidated if required?

Did Memory receive the correct observation?
```

---

# Final Mental Model

Keep this model in mind whenever debugging Vault behavior:

```text
                         ┌─ sparse → VaultValue
                         │
Source → Intelligence → Gate → Writer
                         │
                         └─ typed → Education / Work /
                                    Skills / Tests / etc.
                                      │
                           Evidence + History
                                      │
                       Completion / Issues / Version
                                      │
                              VaultReader
                       ┌──────────────┼─────────────┐
                   Counselor        Goals        Memory
```

## Debugging Rule

Always find the **first failed checkpoint**.

Do not start debugging the database if extraction already failed.

Do not debug Intelligence if the correct candidate was produced but the policy gate rejected it.

Do not debug Vault persistence if the database is correct but the Counselor context is stale.

The Vault becomes much easier to understand once every fact is traced through the same checkpoints:

```text
SOURCE
→ INTELLIGENCE
→ CANDIDATE
→ GROUNDING
→ GATE
→ DISPATCH
→ WRITE
→ EVIDENCE
→ HISTORY
→ CONSISTENCY
→ SNAPSHOT
→ CONSUMERS
```
