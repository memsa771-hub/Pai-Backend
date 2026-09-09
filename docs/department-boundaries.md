# Department boundaries

PAI remains one application, one repository and one PostgreSQL database. These
boundaries separate code ownership without adding services or network calls.

- `workflows/counseling` owns conversation orchestration, context assembly,
  initial messages and follow-up coordination. Previous Counselor module paths
  remain compatibility imports. Streaming deadlines and cancellation are retained.
- `domains/student/public.py` exposes owner-scoped Vault reads and evidence
  submission. `VaultSnapshot` contains data rather than ORM objects. Goal workers
  can inject a `VaultReader` implementation and must acquire its revision fence
  before publishing. Deleted owners cannot pass the fence.
- `domains/student/handlers` owns education, identity, skills, work, projects,
  certifications and test writes. `typed_apply.py` dispatches by schema storage.
  Pending writes remain evidence proposals and do not mutate canonical entities.
- Goals owns its ORM, legacy profile CRUD and profile projections. Student code
  requests Goal projections through `domains/goals/public.py`. Goals are excluded
  from Vault completion scoring and from student assessment inputs.
- Documents receives a `StudentIdentity` and submits `DocumentEvidence` through
  `VaultWriter`. Extraction no longer depends on Counselor. Existing document
  identity, grounding and reconciliation gates still control auto-application.
- Memory consumes `MemoryObservation`. The Vault outcome conversion and sensitive
  field filtering live in `workflows/student_learning/memory.py`; Memory formation
  does not import the student catalog or `VaultCandidate`. Legacy formation helper
  names resolve lazily for compatibility.
- Shared goal vocabulary, research results, memory observations and Vault contracts
  live under `kernel/contracts`. Search continues to use the shared capability.

Public methods receive an authenticated owner ID from the calling workflow or API;
they do not authenticate arbitrary client-supplied IDs. Callers retain transaction
ownership. The fake Vault reader is for isolated local development and does not
provide a production database lock.

`scripts/check_architecture.py` parses imports without loading the app or accessing
a database. CI rejects Goal access to student internals, Vault imports of Goal ORM,
Document imports of Counselor/student persistence, Counselor access to canonical
ORM, implementation imports from contracts, and Vault candidate coupling in Memory.
This is an import boundary check, not a general SQL or dynamic-import analyzer.

## Compatibility scope

Existing API routes and stored data remain readable. Legacy application target
fields (country, universities, intake and career interest) remain in the sparse
catalog so existing clients and evidence history are preserved. Consolidating
those historical values into particular Goals still requires an evidence-aware
migration: multiple goals make an automatic assignment unsafe. No data migration
or global education equivalency mapping is introduced here.

No tests, startup checks, migrations or database checks were run for this refactor,
as requested. Verification was limited to static correctness and import boundaries.
