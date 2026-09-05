# Graph Report - Pai-Backend  (2026-09-05)

## Corpus Check
- 266 files · ~98,953 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 2400 nodes · 6450 edges · 184 communities (133 shown, 51 thin omitted)
- Extraction: 93% EXTRACTED · 7% INFERRED · 0% AMBIGUOUS · INFERRED: 478 edges (avg confidence: 0.91)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `cd6ea9bf`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- resolver.py
- get_settings
- research/service.py
- api/documents.py
- test_document_intelligence.py
- comparators.py
- documents/pipeline.py
- iter_counselor_tokens
- memory/formation.py
- LLMGateway
- taxonomy.py
- test_goal_service.py
- test_memory_system_log_guard.py
- gateway.py
- queue.py
- ToolRegistry
- extractor.py
- test_goal_detection.py
- AuthError
- PersonMemoryService
- followup.py
- typed_apply.py
- goals/service.py
- VaultService
- Person
- FakeAuthProvider
- contracts/schemas.py
- normalize_phone
- VaultCandidate
- test_auth_api.py
- drafts_from_turn
- vault_apply.py
- get_session_factory
- select_discovery_candidates
- SupabaseAuthProvider
- contracts.py
- load_typed_profile_records
- api/goals.py
- apply_completion_to_vault
- routing.py
- PAIOrchestrator
- OnboardingSubmit
- app.py
- worker.py
- InvalidTokenError
- context.py
- test_chat_does_not_block.py
- test_person_vault.py
- PersonBootstrapService
- person.py
- test_conversation_stance.py
- SupabaseStorageProvider
- goals/pipeline.py
- test_memory_embeddings.py
- Any
- grounded_life_aim
- mark_intelligence_stale_for_vault_update
- _rank_entries
- PAI Intelligent Counselor Architecture
- .__init__
- agents.py
- api/chat.py
- matcher.py
- ingest.py
- Goals Domain
- PAI check workflow
- capabilities/__init__.py
- actions/__init__.py
- domains/documents/__init__.py
- domains/goals/__init__.py
- domains/__init__.py
- journey/__init__.py
- student/__init__.py
- student/normalization/__init__.py
- person/__init__.py
- student/vault/__init__.py
- pai/__init__.py
- integrations/__init__.py
- counselor/__init__.py
- intelligences/documents/__init__.py
- intelligences/goals/__init__.py
- intelligences/__init__.py
- sources/__init__.py
- interfaces/__init__.py
- contracts/__init__.py
- kernel/evidence/__init__.py
- kernel/__init__.py
- policy/__init__.py
- database/__init__.py
- platform/__init__.py
- llm/__init__.py
- platform/security/__init__.py
- storage/__init__.py
- workflows/__init__.py
- goals/conftest.py
- Goal Intelligence Pipeline
- Person Vault
- pai
- _extract_json_object
- test_pipeline_stages.py
- PAI Counselor Conversation Tone — Problem Analysis
- DigitizationResult
- test_reasoning_leak.py
- BaseModel
- rank_score
- 17. System Behavior Rules
- compose_opening
- 15. Component Responsibilities
- datetime
- Improve
- Onboarding fields
- 6. How the current system pushes toward execution (analysis)
- 18. What Should Be Avoided
- Placement AI (PAI) Backend
- pai/config.py
- db.py
- 22. Success Criteria
- ProviderUser
- 12. Counselor Context Requirements
- 16. Decision Examples
- 4. Counselor Responsibilities
- 6. Vault Priority Levels
- model_validator
- 4. Three failure modes (one root cause)
- test_phase3.py
- API overview
- Database connection troubleshooting
- test_profile_learning_flow.py
- PostgreSQL on Supabase (required for Phase 2)
- UserNotFoundError
- assertion_of
- AsyncSession
- LLMGateway
- Settings
- async_sessionmaker
- SemanticMemoryRow
- UUID
- .run_chat_turn
- Settings
- test_document_cv_extract.py
- analysis_worker.py
- SensitiveValueCodec
- evidence_grounded
- field_validator
- Self
- Any
- datetime
- Person
- onboarding/service.py
- test_supabase_provider.py
- .node_apply_vault_changes
- planner/service.py
- Any
- student/vault/service.py

## God Nodes (most connected - your core abstractions)
1. `Settings` - 140 edges
2. `Person` - 103 edges
3. `VaultCandidate` - 84 edges
4. `get_settings()` - 70 edges
5. `LLMGateway` - 69 edges
6. `AuthError` - 64 edges
7. `success()` - 51 edges
8. `get_db()` - 44 edges
9. `get_session_factory()` - 41 edges
10. `SupabaseAuthProvider` - 40 edges

## Surprising Connections (you probably didn't know these)
- `test_counselor_json_preamble_does_not_leak_into_reply()` --calls--> `_result_from_text()`  [INFERRED]
  tests/test_pai_orchestration.py → src/pai/intelligences/counselor/counselor_graph.py
- `test_tool_loop_reuses_plain_reply_without_second_llm()` --calls--> `_result_from_text()`  [INFERRED]
  tests/test_pai_orchestration.py → src/pai/intelligences/counselor/counselor_graph.py
- `test_counselor_profile_surfaces_critical_verification()` --uses--> `CounselorContext`  [INFERRED]
  tests/test_document_intelligence.py → src/pai/intelligences/counselor/context.py
- `test_profile_block_falls_back_to_flat_gap_list_without_discovery_candidate()` --uses--> `CounselorContext`  [INFERRED]
  tests/test_profile_discovery.py → src/pai/intelligences/counselor/context.py
- `test_profile_block_renders_top_discovery_candidate_over_flat_gap_list()` --uses--> `CounselorContext`  [INFERRED]
  tests/test_profile_discovery.py → src/pai/intelligences/counselor/context.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Student Intelligence Loop** — src_pai_intelligences_vault, src_pai_domains_student, src_pai_intelligences_goals, src_pai_intelligences_counselor [EXTRACTED 0.90]

## Communities (184 total, 51 thin omitted)

### Community 0 - "resolver.py"
Cohesion: 0.14
Nodes (25): GoalJob, enqueue_goal_intelligence_job(), Stage a goal intelligence job. Idempotent: skip if a pending/running job…, _classify_goal_type(), _fold(), _goal_name_tokens(), GroundedLifeAim, _has_hard_conflict_on_goal() (+17 more)

### Community 1 - "get_settings"
Cohesion: 0.05
Nodes (84): alias, _bearer, Header, HTTPAuthorizationCredentials, get_settings(), get_person_by_auth(), Mark person deleted and purge vault values before auth deletion., soft_delete_person_data() (+76 more)

### Community 2 - "research/service.py"
Cohesion: 0.11
Nodes (19): Generic search action., Any, Generic search action. Provider-specific work lives in integrations., search(), Any, Tavily web search adapter. Callers go through capabilities.search., tavily_search(), Any (+11 more)

### Community 3 - "api/documents.py"
Cohesion: 0.06
Nodes (88): _database_url(), run_migrations_offline(), run_migrations_online(), DeclarativeBase, Document, DocumentCandidate, DocumentFact, DocumentParty (+80 more)

### Community 4 - "test_document_intelligence.py"
Cohesion: 0.25
Nodes (14): BaseModel, reconcile(), ReconcileInput, ReconcileResult, test_counselor_profile_surfaces_critical_verification(), test_generated_docs_are_not_evidence(), test_gpa_critical_conflict_does_not_auto_apply(), test_identity_mismatch_is_deterministic() (+6 more)

### Community 5 - "comparators.py"
Cohesion: 0.49
Nodes (8): _as_float(), gpa_on_4(), parse_gpa(), Any, _kind(), Any, relative_delta(), values_equivalent()

### Community 6 - "documents/pipeline.py"
Cohesion: 0.17
Nodes (23): DocumentAnalysisRun, DocumentJob, Immutable processing attempt. Never overwrite a completed run., policy(), Any, Load Document Intelligence taxonomy and policy from package data (not code)., _read(), field_criticality() (+15 more)

### Community 7 - "iter_counselor_tokens"
Cohesion: 0.16
Nodes (26): Any, ConversationResult, LLMMessage, LLMToolCall, PersonMemoryService, counselor_seed_messages(), _dict_to_llm_message(), _first_json_object() (+18 more)

### Community 8 - "memory/formation.py"
Cohesion: 0.14
Nodes (29): Action, datetime, apply_draft(), apply_memory_drafts(), _belongs_to(), embed_pending_memories(), format_for_recall(), _formation_blob() (+21 more)

### Community 9 - "LLMGateway"
Cohesion: 0.14
Nodes (23): OmnibusLLMExtractor, Single strong multi-domain LLM pass (AgentSpan-style specialist, one call)., _schema_source(), _task_for(), Vault Intelligence — multi-source, multi-domain Person understanding.…, PAI's strong profile-learning brain. Does not write Vault itself., VaultIntelligenceService, ChatSourceDomain (+15 more)

### Community 10 - "taxonomy.py"
Cohesion: 0.23
Nodes (16): classify_document(), _best_type(), _best_type_on_filename(), classify_from_name(), default_type(), _filename_tokens(), _generated_types(), known_types() (+8 more)

### Community 11 - "test_goal_service.py"
Cohesion: 0.10
Nodes (33): _has_hard_conflict(), True only when a stable anchor is present on both sides and disagrees. Missing…, _make_goal(), mock_session(), person_id(), asyncio, fixture, Goal (+25 more)

### Community 12 - "test_memory_system_log_guard.py"
Cohesion: 0.15
Nodes (16): is_system_log_text(), Stores non-vault insights. Does NOT mutate Person Vault., RecallSemanticMemoryTool, RememberInsightTool, _ctx(), _Memory, Memory holds facts about the student, never our own telemetry. An earlier…, False positives silently drop genuine student context. (+8 more)

### Community 13 - "gateway.py"
Cohesion: 0.08
Nodes (24): BaseModel, LLMProvider, BaseModel, Protocol, DeepSeekProvider, LLMProviderError, _parse_tool_call(), Any (+16 more)

### Community 14 - "queue.py"
Cohesion: 0.17
Nodes (19): run_intelligence_followup(), run_intelligence_worker_once(), PersonJob, Durable per-student work. Postgres is the queue until Temporal is worth running., claim_next_person_job(), enqueue_intelligence(), mark_job_done(), mark_job_failed() (+11 more)

### Community 15 - "ToolRegistry"
Cohesion: 0.14
Nodes (18): build_default_registry(), build_turn_registry(), Any, Deterministic per-turn tool set — avoid handing every tool to every request., ToolRegistry, Any, Protocol, ToolContext (+10 more)

### Community 16 - "extractor.py"
Cohesion: 0.11
Nodes (17): extract_candidates(), _try_typed(), DegreeExtraction, BaseModel, to_field_map(), PassportExtraction, BaseModel, to_field_map() (+9 more)

### Community 17 - "test_goal_detection.py"
Cohesion: 0.10
Nodes (28): GoalExtract, _extract_anchors_from_intent(), Normalize anchors from intent. Countries via student geo, not a handwritten…, conversation_id(), _make_active_goal(), _make_life_aim(), mock_session(), person_id() (+20 more)

### Community 18 - "AuthError"
Cohesion: 0.14
Nodes (12): Exception, AuthError, CsrfError, EmailAlreadyInUseError, EmailNotVerifiedError, ForbiddenError, IncorrectPasswordError, InvalidCredentialsError (+4 more)

### Community 19 - "PersonMemoryService"
Cohesion: 0.07
Nodes (21): async_sessionmaker, ConversationMemory, MemoryEntry, MemoryStore, SemanticMemory, SemanticMemoryRow, Long-term semantic + session conversation memory (AgentSpan-backed)., AsyncPostgresMemoryStore (+13 more)

### Community 20 - "followup.py"
Cohesion: 0.21
Nodes (24): Base, Conversation, Message, OrchestrationRun, begin_chat_turn(), ConversationNotFoundError, count_person_messages(), create_conversation() (+16 more)

### Community 21 - "typed_apply.py"
Cohesion: 0.20
Nodes (28): GoalType, Education, _apply_education_fields(), _apply_education_one(), apply_typed_candidate(), _as_items(), _education_payload(), _education_snapshot() (+20 more)

### Community 22 - "goals/service.py"
Cohesion: 0.16
Nodes (32): activate_goal(), _anchor_match_score(), _assert_no_vault_keys(), create_goal(), find_matching_goal(), get_active_goal(), get_conversation_active_goal(), get_goal_by_id() (+24 more)

### Community 23 - "VaultService"
Cohesion: 0.23
Nodes (11): _history_value(), Any, AsyncSession, UUID, Write many vault_value fields in one select + one flush, then evidence rows., Active vault_value map only — no completion scan or typed counts., VaultService, ConsentRequiredError (+3 more)

### Community 24 - "Person"
Cohesion: 0.25
Nodes (8): Person, OnboardingService, _present(), Any, AsyncSession, Map the starting profile into the Vault and mark onboarding complete.…, Extract CV facts into the vault and mark onboarding complete., _sparse_get()

### Community 25 - "FakeAuthProvider"
Cohesion: 0.19
Nodes (14): auth_headers(), bearer_token(), client(), complete_onboarding(), fake_provider(), FakeAuthProvider, onboarded_user(), _ping_db() (+6 more)

### Community 26 - "contracts/schemas.py"
Cohesion: 0.12
Nodes (22): FactExtractionAgent, Compatibility facade over VaultIntelligenceService (chat + document)., Only user-facing agent (PAI Student Counselor) with LangGraph tool loop., StudentConversationAgent, ConversationResult, FactExtractionResult, Any, SchemaRoutingMockProvider (+14 more)

### Community 27 - "normalize_phone"
Cohesion: 0.22
Nodes (7): normalize_phone(), Phone numbers via Google libphonenumber; stored as E.164., model_validator, test_coerce_country_accepts_iso_and_exonyms(), test_country_codes_from_value_keeps_compound_names(), test_extract_countries_uses_iso_alpha2_not_display_names(), test_normalize_phone_e164()

### Community 28 - "VaultCandidate"
Cohesion: 0.09
Nodes (36): country_codes_from_value(), extract_countries_from_text(), High-recall ISO alpha-2 codes mentioned in free text (names, not 2-letter…, Pull ISO alpha-2 codes from a string, list, or already-normalized code., _cand(), _normalize_stream(), Any, Deterministic high-precision extractors — never miss clear GPA/marks/countries. (+28 more)

### Community 29 - "test_auth_api.py"
Cohesion: 0.11
Nodes (10): _signup_body(), test_resend_verification(), test_session_from_verification_tokens(), test_session_rejects_unverified_tokens(), test_signup_does_not_require_phone(), test_signup_duplicate_email(), test_signup_flow(), test_signup_invalid_email() (+2 more)

### Community 30 - "drafts_from_turn"
Cohesion: 0.38
Nodes (11): drafts_from_turn(), _cand(), Memory formation: strengthen on repeat, version on change, don't dump blobs., test_conflict_does_not_share_live_semantic_key(), test_hypothetical_stays_candidate(), test_memory_key_stable_for_catalog_facts(), test_observed_negation_is_not_vault_semantic_key(), test_rank_prefers_query_match_and_skips_unrelated() (+3 more)

### Community 31 - "vault_apply.py"
Cohesion: 0.16
Nodes (26): CatalogField, _fields(), get_catalog_field(), Person Vault field registry (C / I / E priorities)., CandidateResult, evaluate_candidate(), evaluate_candidate_with_context(), evaluate_candidates_batch() (+18 more)

### Community 32 - "get_session_factory"
Cohesion: 0.12
Nodes (28): get_db_session(), get_session_factory(), AsyncSession, reset_engine_for_tests(), _truncate_all(), vault_client(), asyncio, test_person_always_gets_the_same_conversation() (+20 more)

### Community 33 - "select_discovery_candidates"
Cohesion: 0.06
Nodes (62): _aware(), DiscoveryCandidate, DiscoveryResult, explain(), _goal_relevance(), _message_relevance(), CatalogField, Profile Discovery / Gap Selection — deterministic ranking of missing Vault… (+54 more)

### Community 35 - "contracts.py"
Cohesion: 0.18
Nodes (26): _country_names(), country_options(), ISO 3166-1 countries via pycountry — not a handwritten country table., (casefolded name, alpha_2), longest first — no giant regex compile., BudgetBand, CurrentStatus, EducationLevel, EmploymentType (+18 more)

### Community 36 - "load_typed_profile_records"
Cohesion: 0.32
Nodes (12): _cert_dict(), _edu_dict(), _goal_dict(), load_typed_profile_records(), _project_dict(), Any, AsyncSession, UUID (+4 more)

### Community 37 - "api/goals.py"
Cohesion: 0.29
Nodes (15): GoalIntelligence, get_goal_intelligence(), activate_goal_endpoint(), get_active_goal_endpoint(), get_goal_detail(), list_student_goals(), Any, AsyncSession (+7 more)

### Community 38 - "apply_completion_to_vault"
Cohesion: 0.29
Nodes (18): PersonVault, Priority, apply_completion_to_vault(), build_vault_status(), compute_completion(), compute_completion_from_snapshot(), field_is_present_in_snapshot(), _field_label() (+10 more)

### Community 39 - "routing.py"
Cohesion: 0.19
Nodes (12): classify_turn(), counseling_reply_max_tokens(), _has_profile_signal(), is_greeting(), Hi / thanks / ok — not a real counseling turn., Greetings stay tiny so DeepSeek cannot spend 15s writing an essay., Cheap turn kind. Not a second LLM call., Extract statements. Skip greetings, acknowledgements, and advice-only questions. (+4 more)

### Community 40 - "PAIOrchestrator"
Cohesion: 0.24
Nodes (5): PAIState, PAIOrchestrator, Counselor reply only. Extraction/Vault run after the user has the text., Vault/memory/tasks after the student already has the reply., Counselor coordinator. Does not own Vault/Goals/Documents writes.

### Community 41 - "OnboardingSubmit"
Cohesion: 0.07
Nodes (19): coerce_country(), Normalize to ISO 3166-1 alpha-2 (code, alpha-3, English name, or common exonym)., normalize_country_code(), _blank_to_none(), _linkedin_url(), OnboardingSubmit, date, field_validator (+11 more)

### Community 42 - "app.py"
Cohesion: 0.16
Nodes (18): create_app(), create_app_from_env(), lifespan(), FastAPI, close_graph_checkpointer(), init_graph_checkpointer(), include_routers(), FastAPI (+10 more)

### Community 43 - "worker.py"
Cohesion: 0.16
Nodes (21): Goal, GoalIntelligence, GoalJob, Canonical goal identity record — one row per distinct pursuit., Background-computed intelligence summary for one goal. One row per goal., Durable goal intelligence job. Same poll-loop pattern as PersonJob., _build_vault_snapshot(), claim_next_goal_job() (+13 more)

### Community 44 - "InvalidTokenError"
Cohesion: 0.18
Nodes (16): InvalidTokenError, _fetch_jwks(), _jwks_url(), _key_for_token(), Any, Response, Access-token verification for Supabase (HS256 legacy + ES256/RS256 JWKS)., Network verification fallback for asymmetric JWTs. (+8 more)

### Community 45 - "context.py"
Cohesion: 0.16
Nodes (25): BaseModel, _advice_gaps(), build_counselor_context(), build_known_facts(), build_person_context_pack(), build_student_context_pack(), context_pack_to_json(), CounselorContext (+17 more)

### Community 46 - "test_chat_does_not_block.py"
Cohesion: 0.12
Nodes (15): fake_queue(), FakeQueue, _make_fake_goal(), asyncio, fixture, Tests that chat reply path is never blocked by the goal intelligence pipeline.…, CounselorContext.profile_block() must work when active_goal_brief is None., When active_goal_brief is present, it replaces the legacy goal line. (+7 more)

### Community 48 - "PersonBootstrapService"
Cohesion: 0.27
Nodes (8): PersonVault, normalize_email(), PersonBootstrapService, Any, AsyncSession, UUID, Create the Person Vault on first verified auth; skip heavy work on later logins., update_person_profile()

### Community 49 - "person.py"
Cohesion: 0.08
Nodes (51): PersonEvent, append_event(), event_to_public(), goal_fact_lines(), list_recent_events(), Any, AsyncSession, UUID (+43 more)

### Community 50 - "test_conversation_stance.py"
Cohesion: 0.16
Nodes (20): Phase, compute_stance(), ConversationStance, Conversation stance — deterministic, per-turn counselor posture. The…, Decide the counselor's posture for this turn. Defaults are conservative: when…, _stance(), _phase(), Conversation stance: deterministic counselor posture per turn (no LLM). (+12 more)

### Community 51 - "SupabaseStorageProvider"
Cohesion: 0.27
Nodes (3): UUID, StorageAccessError, SupabaseStorageProvider

### Community 52 - "goals/pipeline.py"
Cohesion: 0.22
Nodes (20): ResearchResult, build_counselor_brief(), _goal_guidance(), _llm_json(), Any, LLMGateway, Settings, Goal intelligence pipeline — four stages run sequentially, each isolated.… (+12 more)

### Community 53 - "test_memory_embeddings.py"
Cohesion: 0.11
Nodes (22): Protocol, EmbeddingProvider, get_embedding_provider(), OpenAIEmbeddingProvider, Process-wide provider, or None when embeddings are off/unconfigured., OpenAI embeddings (text-embedding-3-small, 1536 dims by default)., reset_embedding_provider(), _warn_once() (+14 more)

### Community 55 - "grounded_life_aim"
Cohesion: 0.18
Nodes (15): grounded_life_aim(), LLM classified life_aim only if evidence is a span of the student text., GoalExtract, field_validator, Living brief in the student's words — language-agnostic, not an enum., test_goal_type_aliases_match_intelligence_vocabulary(), _extract(), test_english_life_aim_is_stored() (+7 more)

### Community 56 - "mark_intelligence_stale_for_vault_update"
Cohesion: 0.21
Nodes (13): mark_intelligence_stale_for_vault_update(), When a Vault field changes, mark affected goal summaries stale and re-enqueue.…, _mock_goal(), asyncio, Selective Vault→Goals refresh tests. Verifies that when a Vault field changes:…, Spot-check that key Vault fields are in the map., Updating application.test_scores must stale + enqueue admission goals., Updating a field not in VAULT_FIELDS_THAT_AFFECT_GOALS must not touch any goal. (+5 more)

### Community 57 - "_rank_entries"
Cohesion: 0.29
Nodes (8): _rank_entries(), Order candidates. When `semantic` is set, `rows` are (row, similarity) pairs…, A plain min-max rescale pins the only candidate at relevance 0. Vector search…, When everything is equally close, no candidate may be zeroed out., Detached SemanticMemoryRow — ranking never touches the session., _row(), test_near_identical_similarities_do_not_collapse(), test_single_candidate_is_not_scored_as_irrelevant()

### Community 58 - "PAI Intelligent Counselor Architecture"
Cohesion: 0.11
Nodes (19): 10. Goals and Counselor Relationship, 11. Current-Turn and Deferred Intelligence Behavior, 13. Counselor Judgment Layer, 14. Ideal Message Flow, 1. Purpose, 20. Suggested Profile Discovery Logic, 21. Desired Counselor Behavior Over Time, 23. Final Target Model (+11 more)

### Community 59 - ".__init__"
Cohesion: 0.16
Nodes (11): BaseCheckpointSaver, FactExtractionAgent, get_graph_checkpointer(), build_pai_graph(), LLMGateway, Settings, PAIState, StateGraph (+3 more)

### Community 60 - "agents.py"
Cohesion: 0.18
Nodes (13): Environment, extraction_catalog_hint(), Compact writable field list for the fact-extraction LLM (exact keys only)., _env(), render_template(), validate_prompt_templates(), _render(), test_catalog_tells_llm_about_career_writes() (+5 more)

### Community 61 - "api/chat.py"
Cohesion: 0.15
Nodes (19): One counselor transcript per person., ensure_thread_opening(), AsyncSession, UUID, Counselor decides PAI's first message. Conversation domain only persists it., chat(), chat_stream(), ChatRequest (+11 more)

### Community 62 - "matcher.py"
Cohesion: 0.23
Nodes (11): match_student(), fold_name(), name_tokens(), names_match(), parse_date(), Any, normalize_field(), Any (+3 more)

### Community 63 - "ingest.py"
Cohesion: 0.18
Nodes (15): DocumentVersion, evidence_eligible(), normalize_created_by(), normalize_source_type(), create_document_upload(), AsyncSession, Upload-time document ingest. Classification/scan/storage happen here; domain…, Malware scan hook. Default is a no-op until DOCUMENT_MALWARE_SCAN_PROVIDER is… (+7 more)

### Community 64 - "Goals Domain"
Cohesion: 0.29
Nodes (7): Goals Domain, Student Domain, Counselor Intelligence, Goal Intelligence, Vault Intelligence, Kernel Write Gates, Onboarding Workflow

### Community 65 - "PAI check workflow"
Cohesion: 0.13
Nodes (15): 0. Start the server, Automated check (no Swagger), PAI check workflow, Route map (student-facing), Story 10 — I patch a vault field myself, Story 1 — I sign up and log in, Story 2 — Chat is locked until I onboard, Story 3 — I complete the starting profile (form path) (+7 more)

### Community 123 - "_extract_json_object"
Cohesion: 0.13
Nodes (22): _extract_json_object(), _first_json_object(), Pull a JSON object out of a model response. The model sometimes wraps JSON in…, First balanced {...} in the text, ignoring braces inside strings., Goal intelligence must survive a model that does not return bare JSON. The…, The fence and the JSON on one line. Stripping the fence by dropping the first…, The failure seen in production: a sentence, then the JSON., Cut off by max_tokens — unrecoverable, must not raise. (+14 more)

### Community 126 - "test_pipeline_stages.py"
Cohesion: 0.21
Nodes (16): _fake_gateway(), _live_research(), asyncio, Pipeline stage isolation tests — no LLM API calls. Each stage is tested with a…, The spec's canonical test: missing IELTS must appear as a blocking gap., Brief must never exceed _BRIEF_MAX_LINES lines — hard constraint from spec., Full pipeline with mocked LLM must produce status='ready' and a brief., Create a gateway mock that returns a fixed JSON or text. (+8 more)

### Community 127 - "PAI Counselor Conversation Tone — Problem Analysis"
Cohesion: 0.12
Nodes (14): 10. Likely fix surface (conceptual only), 11. Success criteria (product), 12. Open questions, 1. Summary, 2. What good counseling sounds like, 3. Two kinds of certainty (often confused), 5. What a real counselor does before “completion”, 7. Missing concept: goal comprehension maturity (+6 more)

### Community 128 - "DigitizationResult"
Cohesion: 0.14
Nodes (19): DigitizationResult, BaseModel, digitize_bytes(), DocumentOCRProvider, Protocol, ocr_provider(), NativeDocumentProvider, _merge_usage() (+11 more)

### Community 129 - "test_reasoning_leak.py"
Cohesion: 0.11
Nodes (25): parametrize, looks_like_reasoning(), True when the model narrated its deliberation instead of replying. A reasoning-…, _drain(), The student must never receive the model's deliberation. A reasoning-capable…, Run _yield_student_text against a fake stream., Once a token is sent it cannot be unsent, so the opening is buffered.…, A greeting reply ends before the guard window fills. (+17 more)

### Community 131 - "rank_score"
Cohesion: 0.13
Nodes (22): MemoryRecord, _jaccard(), rank_score(), Blend relevance with how settled a memory is. `semantic_similarity` is cosine…, Relevance leads, but structure must still decide between close matches., Jaccard spreads far wider than cosine; its balance is unchanged., A rejected claim must not outrank settled truth just because it is close., Out-of-range similarity must not produce a runaway score. (+14 more)

### Community 132 - "17. System Behavior Rules"
Cohesion: 0.18
Nodes (11): 17. System Behavior Rules, Rule 10 — Keep intelligence supporting the counselor, Rule 1 — Never reason from the latest message alone, Rule 2 — User preference is evidence, not truth, Rule 3 — Active Goal is not a command, Rule 4 — Vault completion is continuous, Rule 5 — Never turn counseling into a questionnaire, Rule 6 — Prefer one high-value question (+3 more)

### Community 133 - "compose_opening"
Cohesion: 0.18
Nodes (16): build_chat_starters(), chat_stay_payload(), compose_opening(), one_gap_question(), _opening_facts(), _pack_get(), Any, Tap-to-send prompts so the student has a next chat, not a blank box. (+8 more)

### Community 134 - "15. Component Responsibilities"
Cohesion: 0.22
Nodes (9): 15. Component Responsibilities, Goal Intelligence, Goal Resolver, Goal Service, Memory, `PAIOrchestrator`, Profile Discovery / Gap Selection, `StudentConversationAgent` (+1 more)

### Community 136 - "Improve"
Cohesion: 0.25
Nodes (8): 19. Minimal Implementation Direction, A. Counselor context builder, B. Profile Discovery / Gap Selection service, C. Counselor instructions, D. Context refresh, E. Observability, Improve, Keep

### Community 137 - "Onboarding fields"
Cohesion: 0.18
Nodes (11): Conditional (send if known), Frontend hints, Minimal payload (unlocks chat), Onboarding fields, Optional, `otherLevelLabel`, Required, `skills[]` (+3 more)

### Community 138 - "6. How the current system pushes toward execution (analysis)"
Cohesion: 0.29
Nodes (7): 6.1 Goal capture is fast; comprehension is not modeled, 6.2 `pursuing` vs `exploring` does not drive conversation, 6.3 Prompt optimizes for advising, not understanding, 6.4 Profile context is rendered as instructions, 6.5 Emotional understanding is narrow, 6.6 Discovery and goal intelligence assume the goal is already “the work”, 6. How the current system pushes toward execution (analysis)

### Community 139 - "18. What Should Be Avoided"
Cohesion: 0.29
Nodes (7): 18. What Should Be Avoided, Avoid: Blind user obedience, Avoid: Creating an unnecessary "judgment agent" too early, Avoid: Form-style Vault completion, Avoid: Goal-only behavior, Avoid: Passing the entire Vault to every LLM turn, Avoid: Separate user-facing agents

### Community 140 - "Placement AI (PAI) Backend"
Cohesion: 0.18
Nodes (11): After the user clicks “verify email”, Development, Docker (API only), Out of scope (Phase 4+), Placement AI (PAI) Backend, Quick start, Security notes, Stack (+3 more)

### Community 141 - "pai/config.py"
Cohesion: 0.16
Nodes (10): main(), Backfill embeddings for memories written before the vector column existed.…, main(), Measure recall quality: does the counselor get the right memory back? Runs…, Persisted memory scoped to a person. Unstructured notes (AgentSpan remember())…, SemanticMemoryRow, embedding_text(), Embedding provider for semantic memory recall. Recall matched shared words… (+2 more)

### Community 142 - "db.py"
Cohesion: 0.43
Nodes (7): _engine_connect_args(), get_engine(), _ipv4_for_host(), _is_remote_postgres(), async_sessionmaker, A-record only. Windows often stalls ~5s on a dead AAAA before falling back., warmup_database()

### Community 143 - "22. Success Criteria"
Cohesion: 0.33
Nodes (6): 22. Success Criteria, Architecture, Counselor intelligence, Goal behavior, Question quality, User understanding

### Community 144 - "ProviderUser"
Cohesion: 0.15
Nodes (6): Auth domain: signup/login, JWT, Supabase provider., AuthProvider, ProviderSession, ProviderUser, Protocol, SignupResult

### Community 145 - "12. Counselor Context Requirements"
Cohesion: 0.40
Nodes (5): 12. Counselor Context Requirements, Goal context, Person understanding, Profile discovery, Turn context

### Community 146 - "16. Decision Examples"
Cohesion: 0.40
Nodes (5): 16. Decision Examples, Example A — Prestige-driven university request, Example B — Missing budget, Example C — Field choice, Example D — Simple factual request

### Community 147 - "4. Counselor Responsibilities"
Cohesion: 0.40
Nodes (5): 4.1 Understand the person, 4.2 Understand the user's goals, 4.3 Form an independent judgment, 4.4 Move the user forward, 4. Counselor Responsibilities

### Community 148 - "6. Vault Priority Levels"
Cohesion: 0.40
Nodes (5): 6. Vault Priority Levels, Critical, Enrichment, Important, Priority is not a rigid sequence

### Community 150 - "4. Three failure modes (one root cause)"
Cohesion: 0.50
Nodes (4): 4. Three failure modes (one root cause), A. Uncertain users → mechanistic checklist, B. Confident users → premature execution, C. Well-known users → overconfident, transactional tone

### Community 152 - "test_phase3.py"
Cohesion: 0.15
Nodes (9): BaseModel, RecordingMockProvider, test_claim_job_skip_locked(), test_gateway_provider_switch_without_changing_orchestration(), test_gateway_uses_registered_mock_provider(), test_policy_high_confidence_non_sensitive_accepts(), test_policy_sensitive_requires_confirmation(), test_prompt_templates_validate_at_startup() (+1 more)

### Community 153 - "API overview"
Cohesion: 0.33
Nodes (6): API overview, Auth (Phase 1), Counselor & documents (PAI), Health, Onboarding (lightweight seed after first verified login), Person & Vault (Phase 2)

### Community 154 - "Database connection troubleshooting"
Cohesion: 0.33
Nodes (6): `Can't load plugin: sqlalchemy.dialects:driver`, Database connection troubleshooting, `getaddrinfo failed` for `db.PROJECT_REF.supabase.co`, `tenant/user postgres.PROJECT_REF not found`, Verified auth users but empty `persons` table, Workaround without local DB connectivity

### Community 155 - "test_profile_learning_flow.py"
Cohesion: 0.21
Nodes (15): StudentTask, is_fact_recording_task(), list_tasks_for_person(), process_task_proposals(), AsyncSession, UUID, TaskProposal, TaskResult (+7 more)

### Community 156 - "PostgreSQL on Supabase (required for Phase 2)"
Cohesion: 0.50
Nodes (4): Environment variables, How to set `DATABASE_URL` correctly, PostgreSQL on Supabase (required for Phase 2), Run migrations

### Community 159 - "assertion_of"
Cohesion: 0.27
Nodes (14): _content_for(), _draft_from_candidate(), importance_of(), memory_key_for(), _observed_status(), _slug(), partition_candidates(), Separate extraction from memory selection. Recall-first extractors may emit… (+6 more)

### Community 166 - ".run_chat_turn"
Cohesion: 0.15
Nodes (10): Message, OrchestrationRun, Person, _counselor_web_note(), AsyncSession, UUID, Persist which gap was surfaced this turn (doc §7 Rule 7 — don't keep re-…, counselor_web_search_enabled() (+2 more)

### Community 167 - "Settings"
Cohesion: 0.15
Nodes (8): BaseSettings, field_validator, model_validator, Self, Settings, AsyncClient, fixture, supabase_settings()

### Community 168 - "test_document_cv_extract.py"
Cohesion: 0.27
Nodes (9): _docx_text(), extract_text_from_bytes(), pdf_page_texts(), _pdf_text(), Pull plain text from uploaded CV/documents. Empty string means unreadable., _docx_with_text(), CV/document text extraction — PDF and DOCX must yield real text, not a…, test_binary_placeholder_is_gone() (+1 more)

### Community 169 - "analysis_worker.py"
Cohesion: 0.19
Nodes (13): claim_next_job(), document_worker_loop(), process_document_job(), AsyncSession, Event, Document intelligence worker: claim jobs, run analysis, persist via the domain., run_document_worker_once(), Start/consume the document intelligence worker. (+5 more)

### Community 170 - "SensitiveValueCodec"
Cohesion: 0.29
Nodes (3): Any, Fernet-based encoding for sensitive vault payloads (no custom crypto)., SensitiveValueCodec

### Community 171 - "evidence_grounded"
Cohesion: 0.39
Nodes (7): compact_span(), evidence_grounded(), extraction_confidence(), fold_span(), page_for_span(), Evidence must appear in digitized text. Hallucinated spans are not document…, test_evidence_must_appear_in_digitized_text()

### Community 178 - "onboarding/service.py"
Cohesion: 0.33
Nodes (4): GoalWriteAction, StrEnum, Canonical goal vocabulary. Intelligence classifies; this module validates., Seed a small Person profile. Chat, documents, and later updates enrich the…

### Community 179 - "test_supabase_provider.py"
Cohesion: 0.33
Nodes (9): asyncio, _settings_kwargs(), test_redirect_origin_must_be_in_cors(), test_redirect_url_cannot_be_site_root(), test_supabase_login_incorrect_password(), test_supabase_login_unknown_email(), test_supabase_signup_rejects_existing_email(), test_supabase_signup_without_session() (+1 more)

### Community 180 - ".node_apply_vault_changes"
Cohesion: 0.40
Nodes (5): invalidate_counselor_cache(), PendingConfirmation, BaseModel, RunError, VaultChange

### Community 181 - "planner/service.py"
Cohesion: 0.50
Nodes (3): Planner intelligence. Proposes actions; Kernel + domains persist them., plan_next_actions(), Planner intelligence — next actions. Does not persist or execute them.

### Community 183 - "student/vault/service.py"
Cohesion: 0.24
Nodes (13): Certification, PersonConsent, Project, Skill, VaultEvidence, VaultHistory, VaultValue, WorkExperience (+5 more)

## Knowledge Gaps
- **135 isolated node(s):** `pai`, `10. Likely fix surface (conceptual only)`, `11. Success criteria (product)`, `12. Open questions`, `1. Summary` (+130 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **51 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Settings` connect `Settings` to `DigitizationResult`, `get_settings`, `api/documents.py`, `documents/pipeline.py`, `LLMGateway`, `pai/config.py`, `queue.py`, `ToolRegistry`, `db.py`, `gateway.py`, `AuthError`, `PersonMemoryService`, `followup.py`, `VaultService`, `Person`, `FakeAuthProvider`, `contracts/schemas.py`, `get_session_factory`, `SupabaseAuthProvider`, `api/goals.py`, `.run_chat_turn`, `routing.py`, `analysis_worker.py`, `app.py`, `SensitiveValueCodec`, `worker.py`, `InvalidTokenError`, `PersonBootstrapService`, `onboarding/service.py`, `SupabaseStorageProvider`, `test_supabase_provider.py`, `test_memory_embeddings.py`, `student/vault/service.py`, `agents.py`, `api/chat.py`, `ingest.py`?**
  _High betweenness centrality (0.107) - this node is a cross-community bridge._
- **Why does `VaultCandidate` connect `VaultCandidate` to `get_session_factory`, `api/documents.py`, `documents/pipeline.py`, `LLMGateway`, `vault_apply.py`, `extractor.py`, `.node_apply_vault_changes`, `typed_apply.py`, `grounded_life_aim`, `test_phase3.py`, `contracts/schemas.py`, `test_profile_learning_flow.py`, `agents.py`, `drafts_from_turn`, `assertion_of`?**
  _High betweenness centrality (0.060) - this node is a cross-community bridge._
- **Why does `LLMGateway` connect `LLMGateway` to `get_settings`, `documents/pipeline.py`, `Settings`, `analysis_worker.py`, `app.py`, `worker.py`, `gateway.py`, `queue.py`, `ToolRegistry`, `extractor.py`, `AuthError`, `followup.py`, `test_phase3.py`, `contracts/schemas.py`, `agents.py`?**
  _High betweenness centrality (0.047) - this node is a cross-community bridge._
- **Are the 84 inferred relationships involving `Settings` (e.g. with `create_app()` and `lifespan()`) actually correct?**
  _`Settings` has 84 INFERRED edges - model-reasoned connections that need verification._
- **Are the 8 inferred relationships involving `get_settings()` (e.g. with `_database_url()` and `main()`) actually correct?**
  _`get_settings()` has 8 INFERRED edges - model-reasoned connections that need verification._
- **Are the 34 inferred relationships involving `LLMGateway` (e.g. with `lifespan()` and `FactExtractionAgent`) actually correct?**
  _`LLMGateway` has 34 INFERRED edges - model-reasoned connections that need verification._
- **What connects `pai`, `10. Likely fix surface (conceptual only)`, `11. Success criteria (product)` to the rest of the system?**
  _135 weakly-connected nodes found - possible documentation gaps or missing edges._