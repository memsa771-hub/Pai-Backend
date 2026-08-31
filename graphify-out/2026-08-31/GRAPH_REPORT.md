# Graph Report - Pai-Backend  (2026-08-31)

## Corpus Check
- 256 files · ~90,718 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 2177 nodes · 6277 edges · 158 communities (123 shown, 35 thin omitted)
- Extraction: 93% EXTRACTED · 7% INFERRED · 0% AMBIGUOUS · INFERRED: 412 edges (avg confidence: 0.92)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `8244b426`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- api/documents.py
- auth.py
- worker.py
- chat
- get_session_factory
- test_document_intelligence.py
- documents/pipeline.py
- counselor_graph.py
- app.py
- LLMGateway
- taxonomy.py
- test_goal_service.py
- ToolContext
- gateway.py
- queue.py
- memory/formation.py
- VaultCandidate
- resolve
- AuthError
- postgres_store.py
- conversations/service.py
- typed_apply.py
- Goal
- VaultService
- context.py
- Person
- test_pai_orchestration.py
- normalize.py
- test_vault_intelligence.py
- test_auth_api.py
- vault_apply.py
- extractor.py
- Settings
- select_discovery_candidates
- SupabaseAuthProvider
- contracts.py
- student/vault/service.py
- InvalidTokenError
- completion.py
- routing.py
- PAIOrchestrator
- OnboardingSubmit
- AuthProvider
- api/goals.py
- jwt.py
- field_validator
- test_chat_does_not_block.py
- test_person_vault.py
- resolver.py
- person.py
- test_conversation_stance.py
- success
- api/chat.py
- compose_opening
- update_resource
- grounded_life_aim
- test_selective_refresh.py
- test_supabase_provider.py
- PAI Intelligent Counselor Architecture
- vault.py
- agents.py
- memory/__init__.py
- matcher.py
- AuthService
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
- dependencies.py
- analysis_worker.py
- PAI Counselor Conversation Tone — Problem Analysis
- pai/config.py
- drafts_from_turn
- candidate_eval.py
- SupabaseStorageProvider
- 17. System Behavior Rules
- test_document_cv_extract.py
- 15. Component Responsibilities
- onboarding.py
- Improve
- Onboarding fields
- 6. How the current system pushes toward execution (analysis)
- 18. What Should Be Avoided
- Placement AI (PAI) Backend
- orchestrator.py
- actions/service.py
- 22. Success Criteria
- .__init__
- 12. Counselor Context Requirements
- 16. Decision Examples
- 4. Counselor Responsibilities
- 6. Vault Priority Levels
- scanner.py
- 4. Three failure modes (one root cause)
- .dob
- API overview
- Database connection troubleshooting
- env.py
- PostgreSQL on Supabase (required for Phase 2)

## God Nodes (most connected - your core abstractions)
1. `Settings` - 149 edges
2. `Person` - 117 edges
3. `VaultCandidate` - 93 edges
4. `LLMGateway` - 84 edges
5. `get_settings()` - 65 edges
6. `AuthError` - 64 edges
7. `success()` - 51 edges
8. `get_db()` - 44 edges
9. `Goal` - 43 edges
10. `Base` - 42 edges

## Surprising Connections (you probably didn't know these)
- `test_education_payload_keeps_marks_and_rejects_orphan_gpa_fabrication()` --calls--> `_education_payload()`  [INFERRED]
  tests/test_profile_learning_flow.py → src/pai/domains/student/typed_apply.py
- `test_counselor_profile_surfaces_critical_verification()` --uses--> `CounselorContext`  [INFERRED]
  tests/test_document_intelligence.py → src/pai/intelligences/counselor/context.py
- `test_profile_block_falls_back_to_flat_gap_list_without_discovery_candidate()` --uses--> `CounselorContext`  [INFERRED]
  tests/test_profile_discovery.py → src/pai/intelligences/counselor/context.py
- `test_profile_block_renders_top_discovery_candidate_over_flat_gap_list()` --uses--> `CounselorContext`  [INFERRED]
  tests/test_profile_discovery.py → src/pai/intelligences/counselor/context.py
- `test_counselor_json_preamble_does_not_leak_into_reply()` --calls--> `_result_from_text()`  [INFERRED]
  tests/test_pai_orchestration.py → src/pai/intelligences/counselor/counselor_graph.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Student Intelligence Loop** — src_pai_intelligences_vault, src_pai_domains_student, src_pai_intelligences_goals, src_pai_intelligences_counselor [EXTRACTED 0.90]

## Communities (158 total, 35 thin omitted)

### Community 0 - "api/documents.py"
Cohesion: 0.08
Nodes (66): Document, DocumentCandidate, DocumentFact, DocumentRelation, MessageDocument, Chat references a Document Vault item. The file is not stored on the message., Polymorphic links: chat, goal, application, verification, lineage., Normalized evidence. Not Person Vault truth. (+58 more)

### Community 1 - "auth.py"
Cohesion: 0.14
Nodes (25): Mark person deleted and purge vault values before auth deletion., soft_delete_person_data(), ApiErrorBody, ApiErrorResponse, ApiSuccessResponse, AuthSessionPublic, EmailOnlyRequest, HealthData (+17 more)

### Community 2 - "worker.py"
Cohesion: 0.05
Nodes (69): Generic search action., Any, Generic search action. Provider-specific work lives in integrations., search(), GoalJob, Durable goal intelligence job. Same poll-loop pattern as PersonJob., Any, Tavily web search adapter. Callers go through capabilities.search. (+61 more)

### Community 3 - "chat"
Cohesion: 0.16
Nodes (18): ensure_thread_opening(), AsyncSession, UUID, Counselor decides PAI's first message. Conversation domain only persists it., chat(), chat_stream(), ChatRequest, get_chat_messages() (+10 more)

### Community 4 - "get_session_factory"
Cohesion: 0.05
Nodes (62): normalize_email(), PersonBootstrapService, Any, AsyncSession, UUID, Create the Person Vault on first verified auth; skip heavy work on later logins., _engine_connect_args(), get_db_session() (+54 more)

### Community 5 - "test_document_intelligence.py"
Cohesion: 0.21
Nodes (19): _as_float(), gpa_on_4(), parse_gpa(), Any, _kind(), Any, relative_delta(), values_equivalent() (+11 more)

### Community 6 - "documents/pipeline.py"
Cohesion: 0.21
Nodes (21): DocumentAnalysisRun, DocumentJob, DocumentParty, Immutable processing attempt. Never overwrite a completed run., policy(), field_criticality(), field_sensitivity(), rank() (+13 more)

### Community 7 - "counselor_graph.py"
Cohesion: 0.27
Nodes (17): counselor_seed_messages(), _dict_to_llm_message(), _first_json_object(), iter_counselor_tokens(), _normalize_tool_call(), _parse_conversation_json(), public_reply(), Any (+9 more)

### Community 8 - "app.py"
Cohesion: 0.18
Nodes (16): create_app(), create_app_from_env(), lifespan(), FastAPI, close_graph_checkpointer(), init_graph_checkpointer(), include_routers(), FastAPI (+8 more)

### Community 9 - "LLMGateway"
Cohesion: 0.14
Nodes (24): OmnibusLLMExtractor, Single strong multi-domain LLM pass (AgentSpan-style specialist, one call)., _schema_source(), _task_for(), normalize_candidates(), Vault Intelligence — multi-source, multi-domain Person understanding.…, PAI's strong profile-learning brain. Does not write Vault itself., VaultIntelligenceService (+16 more)

### Community 10 - "taxonomy.py"
Cohesion: 0.11
Nodes (31): DocumentVersion, classify_document(), _best_type(), _best_type_on_filename(), classify_from_name(), default_type(), _filename_tokens(), _generated_types() (+23 more)

### Community 11 - "test_goal_service.py"
Cohesion: 0.09
Nodes (40): _anchor_match_score(), _assert_no_vault_keys(), create_goal(), goal_fact_lines(), _has_hard_conflict(), _norm(), True only when a stable anchor is present on both sides and disagrees. Missing…, Create a brand-new goal record. Caller commits. (+32 more)

### Community 12 - "ToolContext"
Cohesion: 0.12
Nodes (23): Any, Stores non-vault insights. Does NOT mutate Person Vault., RecallSemanticMemoryTool, RememberInsightTool, build_default_registry(), build_turn_registry(), Any, Deterministic per-turn tool set — avoid handing every tool to every request. (+15 more)

### Community 13 - "gateway.py"
Cohesion: 0.07
Nodes (25): BaseModel, LLMProvider, BaseModel, Protocol, DeepSeekProvider, LLMProviderError, _parse_tool_call(), Any (+17 more)

### Community 14 - "queue.py"
Cohesion: 0.15
Nodes (22): run_intelligence_followup(), Background worker processes. Loops only; processing lives in intelligences., intelligence_worker_loop(), Event, run_intelligence_worker_once(), PersonJob, Durable per-student work. Postgres is the queue until Temporal is worth running., claim_next_person_job() (+14 more)

### Community 15 - "memory/formation.py"
Cohesion: 0.17
Nodes (26): Action, apply_draft(), apply_memory_drafts(), _belongs_to(), _draft_from_candidate(), _formation_blob(), _jaccard(), _link_turn() (+18 more)

### Community 16 - "VaultCandidate"
Cohesion: 0.15
Nodes (23): _content_for(), importance_of(), _observed_status(), partition_candidates(), Separate extraction from memory selection. Recall-first extractors may emit…, field_validator, VaultCandidate, assertion_of() (+15 more)

### Community 17 - "resolve"
Cohesion: 0.11
Nodes (29): _extract_anchors_from_intent(), Normalize anchors from intent. Countries via student geo, not a handwritten…, Decide what to do with the goal signal from this turn. Called synchronously…, resolve(), GoalExtract, Living brief in the student's words — language-agnostic, not an enum., conversation_id(), _make_active_goal() (+21 more)

### Community 18 - "AuthError"
Cohesion: 0.14
Nodes (12): Exception, AuthError, CsrfError, EmailAlreadyInUseError, EmailNotVerifiedError, ForbiddenError, IncorrectPasswordError, InvalidCredentialsError (+4 more)

### Community 19 - "postgres_store.py"
Cohesion: 0.11
Nodes (16): MemoryEntry, MemoryStore, format_for_recall(), record_from_row(), Persisted memory scoped to a person. Unstructured notes (AgentSpan remember())…, SemanticMemoryRow, AsyncPostgresMemoryStore, InProcessMemoryStore (+8 more)

### Community 20 - "conversations/service.py"
Cohesion: 0.31
Nodes (14): Conversation, ConversationNotFoundError, count_person_messages(), create_conversation(), get_conversation_owned(), get_latest_active_conversation(), get_or_create_person_conversation(), list_person_messages() (+6 more)

### Community 21 - "typed_apply.py"
Cohesion: 0.19
Nodes (27): normalize_phone(), Phone numbers via Google libphonenumber; stored as E.164., _apply_education_fields(), _apply_education_one(), apply_typed_candidate(), _as_items(), _education_payload(), _education_snapshot() (+19 more)

### Community 22 - "Goal"
Cohesion: 0.17
Nodes (27): Goal, Canonical goal identity record — one row per distinct pursuit., activate_goal(), enqueue_goal_intelligence_job(), find_matching_goal(), get_active_goal(), get_conversation_active_goal(), get_goal_by_id() (+19 more)

### Community 23 - "VaultService"
Cohesion: 0.21
Nodes (13): get_catalog_field(), mask_value(), _history_value(), Any, AsyncSession, UUID, Write many vault_value fields in one select + one flush, then evidence rows., Active vault_value map only — no completion scan or typed counts. (+5 more)

### Community 24 - "context.py"
Cohesion: 0.18
Nodes (21): _advice_gaps(), build_counselor_context(), build_person_context_pack(), build_student_context_pack(), context_pack_to_json(), CounselorContext, _dedupe_goal_lines(), _fact_after() (+13 more)

### Community 25 - "Person"
Cohesion: 0.25
Nodes (8): Person, OnboardingService, _present(), Any, AsyncSession, Map the starting profile into the Vault and mark onboarding complete.…, Extract CV facts into the vault and mark onboarding complete., _sparse_get()

### Community 26 - "test_pai_orchestration.py"
Cohesion: 0.09
Nodes (25): BaseCheckpointSaver, PersonMemoryService, Facade: conversation window + formed long-term memory per student. Agents may…, FactExtractionAgent, Compatibility facade over VaultIntelligenceService (chat + document)., Only user-facing agent (PAI Student Counselor) with LangGraph tool loop., StudentConversationAgent, get_graph_checkpointer() (+17 more)

### Community 27 - "normalize.py"
Cohesion: 0.12
Nodes (17): coerce_country(), country_codes_from_value(), _country_names(), country_options(), ISO 3166-1 countries via pycountry — not a handwritten country table., Normalize to ISO 3166-1 alpha-2 (code, alpha-3, English name, or common exonym)., Pull ISO alpha-2 codes from a string, list, or already-normalized code., (casefolded name, alpha_2), longest first — no giant regex compile. (+9 more)

### Community 28 - "test_vault_intelligence.py"
Cohesion: 0.09
Nodes (27): extract_countries_from_text(), High-recall ISO alpha-2 codes mentioned in free text (names, not 2-letter…, _cand(), _normalize_stream(), Any, Deterministic high-precision extractors — never miss clear GPA/marks/countries., Return (candidates, hit labels). High precision only., run_deterministic_boosters() (+19 more)

### Community 29 - "test_auth_api.py"
Cohesion: 0.11
Nodes (10): _signup_body(), test_resend_verification(), test_session_from_verification_tokens(), test_session_rejects_unverified_tokens(), test_signup_does_not_require_phone(), test_signup_duplicate_email(), test_signup_flow(), test_signup_invalid_email() (+2 more)

### Community 30 - "vault_apply.py"
Cohesion: 0.17
Nodes (10): Any, Fernet-based encoding for sensitive vault payloads (no custom crypto)., SensitiveValueCodec, apply_vault_candidate(), process_candidates(), AsyncSession, BaseModel, VaultApplyResult (+2 more)

### Community 31 - "extractor.py"
Cohesion: 0.09
Nodes (24): compact_span(), evidence_grounded(), extraction_confidence(), fold_span(), page_for_span(), Evidence must appear in digitized text. Hallucinated spans are not document…, extract_candidates(), _try_typed() (+16 more)

### Community 32 - "Settings"
Cohesion: 0.14
Nodes (16): BaseSettings, get_settings(), field_validator, model_validator, Self, Settings, confirm_email_verification(), establish_session() (+8 more)

### Community 33 - "select_discovery_candidates"
Cohesion: 0.11
Nodes (29): _aware(), DiscoveryCandidate, DiscoveryResult, explain(), _goal_relevance(), _message_relevance(), datetime, Profile Discovery / Gap Selection — deterministic ranking of missing Vault… (+21 more)

### Community 34 - "SupabaseAuthProvider"
Cohesion: 0.20
Nodes (3): Any, AsyncClient, SupabaseAuthProvider

### Community 35 - "contracts.py"
Cohesion: 0.29
Nodes (18): BudgetBand, CurrentStatus, EducationLevel, EmploymentType, FieldOfStudy, Gender, IntakeSeason, StrEnum (+10 more)

### Community 36 - "student/vault/service.py"
Cohesion: 0.18
Nodes (25): DeclarativeBase, Goal, GoalIntelligence, and GoalJob. Tables unchanged (goals,…, Certification, Education, PersonConsent, Project, Skill, VaultEvidence (+17 more)

### Community 37 - "InvalidTokenError"
Cohesion: 0.19
Nodes (4): InvalidTokenError, UserNotFoundError, ProviderSession, FakeAuthProvider

### Community 38 - "completion.py"
Cohesion: 0.16
Nodes (24): Priority, PersonVault, update_person_profile(), CatalogField, _fields(), Person Vault field registry (C / I / E priorities)., apply_completion_to_vault(), build_vault_status() (+16 more)

### Community 39 - "routing.py"
Cohesion: 0.15
Nodes (17): classify_turn(), counseling_reply_max_tokens(), counselor_web_search_enabled(), _has_profile_signal(), is_greeting(), Offer web_search; the counselor LLM decides whether to call it., Hi / thanks / ok — not a real counseling turn., Greetings stay tiny so DeepSeek cannot spend 15s writing an essay. (+9 more)

### Community 40 - "PAIOrchestrator"
Cohesion: 0.16
Nodes (9): PAIOrchestrator, AsyncSession, UUID, Counselor reply only. Extraction/Vault run after the user has the text., Vault/memory/tasks after the student already has the reply., Persist which gap was surfaced this turn (doc §7 Rule 7 — don't keep re-…, Counselor coordinator. Does not own Vault/Goals/Documents writes., PAIState (+1 more)

### Community 41 - "OnboardingSubmit"
Cohesion: 0.10
Nodes (13): OnboardingSubmit, model_validator, Starting profile. Categorical fields are closed enums; GET /onboarding returns…, test_enum_catalog_exposes_dropdown_ids(), test_submit_schema_accepts_country_name_alias(), test_submit_schema_high_school_does_not_need_degree(), test_submit_schema_minimal_criticals_are_enough(), test_submit_schema_normalizes_phone_to_e164() (+5 more)

### Community 42 - "AuthProvider"
Cohesion: 0.13
Nodes (5): Auth domain: signup/login, JWT, Supabase provider., AuthProvider, GenericActionResult, Protocol, SignupResult

### Community 43 - "api/goals.py"
Cohesion: 0.28
Nodes (16): GoalIntelligence, Background-computed intelligence summary for one goal. One row per goal., get_goal_intelligence(), activate_goal_endpoint(), get_active_goal_endpoint(), get_goal_detail(), list_student_goals(), Any (+8 more)

### Community 44 - "jwt.py"
Cohesion: 0.21
Nodes (15): _fetch_jwks(), _jwks_url(), _key_for_token(), Any, Response, Access-token verification for Supabase (HS256 legacy + ES256/RS256 JWKS)., Network verification fallback for asymmetric JWTs., Verify Supabase user JWT (HS256 secret or ES256/RS256 via JWKS). (+7 more)

### Community 45 - "field_validator"
Cohesion: 0.20
Nodes (7): _blank_to_none(), _linkedin_url(), OnboardingSkillItem, OnboardingTestScoreItem, OnboardingWorkItem, BaseModel, field_validator

### Community 46 - "test_chat_does_not_block.py"
Cohesion: 0.12
Nodes (15): fake_queue(), FakeQueue, _make_fake_goal(), asyncio, fixture, Tests that chat reply path is never blocked by the goal intelligence pipeline.…, CounselorContext.profile_block() must work when active_goal_brief is None., When active_goal_brief is present, it replaces the legacy goal line. (+7 more)

### Community 48 - "resolver.py"
Cohesion: 0.10
Nodes (27): parametrize, GoalType, GoalWriteAction, StrEnum, Canonical goal vocabulary. Intelligence classifies; this module validates., _classify_goal_type(), _fold(), _goal_name_tokens() (+19 more)

### Community 49 - "person.py"
Cohesion: 0.09
Nodes (44): PersonDecision, PersonEvent, append_event(), event_to_public(), goal_fact_lines(), list_recent_events(), Any, AsyncSession (+36 more)

### Community 50 - "test_conversation_stance.py"
Cohesion: 0.16
Nodes (20): Phase, compute_stance(), ConversationStance, Conversation stance — deterministic, per-turn counselor posture. The…, Decide the counselor's posture for this turn. Defaults are conservative: when…, _stance(), _phase(), Conversation stance: deterministic counselor posture per turn (no LLM). (+12 more)

### Community 51 - "success"
Cohesion: 0.27
Nodes (21): get_person_by_auth(), change_password(), _clear_session_cookies(), delete_account(), forgot_password(), logout(), me(), AsyncSession (+13 more)

### Community 52 - "api/chat.py"
Cohesion: 0.28
Nodes (10): One counselor transcript per person., Message, OrchestrationRun, begin_chat_turn(), One commit: user message + orchestration run. Caller already owns the…, save_assistant_message(), handle_user_message(), _payload_from_state() (+2 more)

### Community 53 - "compose_opening"
Cohesion: 0.15
Nodes (19): build_chat_starters(), build_known_facts(), chat_stay_payload(), compose_opening(), one_gap_question(), _opening_facts(), _pack_get(), Any (+11 more)

### Community 54 - "update_resource"
Cohesion: 0.50
Nodes (8): create_resource(), delete_resource(), list_resources(), Any, AsyncSession, UUID, update_resource(), _resource_router()

### Community 55 - "grounded_life_aim"
Cohesion: 0.38
Nodes (11): grounded_life_aim(), LLM classified life_aim only if evidence is a span of the student text., _extract(), test_english_life_aim_is_stored(), test_exploring_and_pivot_come_from_the_classifier(), test_mixed_aim_and_attach_keeps_only_the_aim(), test_model_cannot_invent_a_goal_not_in_the_message(), test_questions_and_greetings_are_not_goals() (+3 more)

### Community 56 - "test_selective_refresh.py"
Cohesion: 0.23
Nodes (11): _mock_goal(), asyncio, Selective Vault→Goals refresh tests. Verifies that when a Vault field changes:…, Spot-check that key Vault fields are in the map., Updating application.test_scores must stale + enqueue admission goals., Updating a field not in VAULT_FIELDS_THAT_AFFECT_GOALS must not touch any goal., Create two goals (admission + job). Update IELTS (test_scores). Only admission…, test_test_score_update_marks_admission_stale() (+3 more)

### Community 57 - "test_supabase_provider.py"
Cohesion: 0.26
Nodes (11): asyncio, fixture, _settings_kwargs(), supabase_settings(), test_redirect_origin_must_be_in_cors(), test_redirect_url_cannot_be_site_root(), test_supabase_login_incorrect_password(), test_supabase_login_unknown_email() (+3 more)

### Community 58 - "PAI Intelligent Counselor Architecture"
Cohesion: 0.11
Nodes (19): 10. Goals and Counselor Relationship, 11. Current-Turn and Deferred Intelligence Behavior, 13. Counselor Judgment Layer, 14. Ideal Message Flow, 1. Purpose, 20. Suggested Profile Discovery Logic, 21. Desired Counselor Behavior Over Time, 23. Final Target Model (+11 more)

### Community 59 - "vault.py"
Cohesion: 0.30
Nodes (14): delete_field(), field_history(), get_catalog(), get_field(), get_vault(), patch_field(), AsyncSession, BaseModel (+6 more)

### Community 60 - "agents.py"
Cohesion: 0.17
Nodes (14): Environment, extraction_catalog_hint(), Compact writable field list for the fact-extraction LLM (exact keys only)., _env(), render_template(), validate_prompt_templates(), _render(), test_catalog_tells_llm_about_career_writes() (+6 more)

### Community 62 - "matcher.py"
Cohesion: 0.18
Nodes (14): evidence_eligible(), match_student(), fold_name(), name_tokens(), names_match(), parse_date(), Any, normalize_field() (+6 more)

### Community 63 - "AuthService"
Cohesion: 0.18
Nodes (3): AuthService, Turn tokens from the email-verification redirect into a PAI session., SessionBundle

### Community 64 - "Goals Domain"
Cohesion: 0.29
Nodes (7): Goals Domain, Student Domain, Counselor Intelligence, Goal Intelligence, Vault Intelligence, Kernel Write Gates, Onboarding Workflow

### Community 65 - "PAI check workflow"
Cohesion: 0.13
Nodes (15): 0. Start the server, Automated check (no Swagger), PAI check workflow, Route map (student-facing), Story 10 — I patch a vault field myself, Story 1 — I sign up and log in, Story 2 — Chat is locked until I onboard, Story 3 — I complete the starting profile (form path) (+7 more)

### Community 123 - "dependencies.py"
Cohesion: 0.24
Nodes (13): alias, _bearer, Header, HTTPAuthorizationCredentials, _constant_time_equals(), get_auth_provider(), get_current_access_token(), get_validated_access_token() (+5 more)

### Community 126 - "analysis_worker.py"
Cohesion: 0.23
Nodes (12): claim_next_job(), document_worker_loop(), process_document_job(), AsyncSession, Event, Document intelligence worker: claim jobs, run analysis, persist via the domain., run_document_worker_once(), Start/consume the document intelligence worker. (+4 more)

### Community 127 - "PAI Counselor Conversation Tone — Problem Analysis"
Cohesion: 0.12
Nodes (14): 10. Likely fix surface (conceptual only), 11. Success criteria (product), 12. Open questions, 1. Summary, 2. What good counseling sounds like, 3. Two kinds of certainty (often confused), 5. What a real counselor does before “completion”, 7. Missing concept: goal comprehension maturity (+6 more)

### Community 128 - "pai/config.py"
Cohesion: 0.14
Nodes (19): DigitizationResult, BaseModel, digitize_bytes(), DocumentOCRProvider, Protocol, ocr_provider(), NativeDocumentProvider, _merge_usage() (+11 more)

### Community 129 - "drafts_from_turn"
Cohesion: 0.33
Nodes (12): drafts_from_turn(), _kind_for(), _cand(), Memory formation: strengthen on repeat, version on change, don't dump blobs., test_conflict_does_not_share_live_semantic_key(), test_hypothetical_stays_candidate(), test_memory_key_stable_for_catalog_facts(), test_observed_negation_is_not_vault_semantic_key() (+4 more)

### Community 130 - "candidate_eval.py"
Cohesion: 0.33
Nodes (11): CandidateResult, evaluate_candidate(), evaluate_candidate_with_context(), evaluate_candidates_batch(), load_candidate_validation_context(), _normalize(), Any, AsyncSession (+3 more)

### Community 131 - "SupabaseStorageProvider"
Cohesion: 0.27
Nodes (3): UUID, StorageAccessError, SupabaseStorageProvider

### Community 132 - "17. System Behavior Rules"
Cohesion: 0.18
Nodes (11): 17. System Behavior Rules, Rule 10 — Keep intelligence supporting the counselor, Rule 1 — Never reason from the latest message alone, Rule 2 — User preference is evidence, not truth, Rule 3 — Active Goal is not a command, Rule 4 — Vault completion is continuous, Rule 5 — Never turn counseling into a questionnaire, Rule 6 — Prefer one high-value question (+3 more)

### Community 133 - "test_document_cv_extract.py"
Cohesion: 0.27
Nodes (9): _docx_text(), extract_text_from_bytes(), pdf_page_texts(), _pdf_text(), Pull plain text from uploaded CV/documents. Empty string means unreadable., _docx_with_text(), CV/document text extraction — PDF and DOCX must yield real text, not a…, test_binary_placeholder_is_gone() (+1 more)

### Community 134 - "15. Component Responsibilities"
Cohesion: 0.22
Nodes (9): 15. Component Responsibilities, Goal Intelligence, Goal Resolver, Goal Service, Memory, `PAIOrchestrator`, Profile Discovery / Gap Selection, `StudentConversationAgent` (+1 more)

### Community 135 - "onboarding.py"
Cohesion: 0.32
Nodes (11): get_onboarding(), AsyncSession, Depends, get, JSONResponse, post, Request, UploadFile (+3 more)

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

### Community 141 - "orchestrator.py"
Cohesion: 0.22
Nodes (13): build_pai_graph(), _counselor_web_note(), Planner intelligence. Proposes actions; Kernel + domains persist them., plan_next_actions(), Planner intelligence — next actions. Does not persist or execute them., PendingConfirmation, BaseModel, RunError (+5 more)

### Community 142 - "actions/service.py"
Cohesion: 0.42
Nodes (7): StudentTask, is_fact_recording_task(), list_tasks_for_person(), process_task_proposals(), AsyncSession, UUID, test_fact_recording_tasks_are_rejected()

### Community 143 - "22. Success Criteria"
Cohesion: 0.33
Nodes (6): 22. Success Criteria, Architecture, Counselor intelligence, Goal behavior, Question quality, User understanding

### Community 144 - ".__init__"
Cohesion: 0.29
Nodes (5): ConversationMemory, SemanticMemory, async_sessionmaker, AsyncSession, UUID

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

### Community 149 - "scanner.py"
Cohesion: 0.50
Nodes (3): Malware scan hook. Default is a no-op until DOCUMENT_MALWARE_SCAN_PROVIDER is…, scan_bytes(), ScanResult

### Community 150 - "4. Three failure modes (one root cause)"
Cohesion: 0.50
Nodes (4): 4. Three failure modes (one root cause), A. Uncertain users → mechanistic checklist, B. Confident users → premature execution, C. Well-known users → overconfident, transactional tone

### Community 153 - "API overview"
Cohesion: 0.33
Nodes (6): API overview, Auth (Phase 1), Counselor & documents (PAI), Health, Onboarding (lightweight seed after first verified login), Person & Vault (Phase 2)

### Community 154 - "Database connection troubleshooting"
Cohesion: 0.33
Nodes (6): `Can't load plugin: sqlalchemy.dialects:driver`, Database connection troubleshooting, `getaddrinfo failed` for `db.PROJECT_REF.supabase.co`, `tenant/user postgres.PROJECT_REF not found`, Verified auth users but empty `persons` table, Workaround without local DB connectivity

### Community 155 - "env.py"
Cohesion: 0.83
Nodes (3): _database_url(), run_migrations_offline(), run_migrations_online()

### Community 156 - "PostgreSQL on Supabase (required for Phase 2)"
Cohesion: 0.50
Nodes (4): Environment variables, How to set `DATABASE_URL` correctly, PostgreSQL on Supabase (required for Phase 2), Run migrations

## Knowledge Gaps
- **135 isolated node(s):** `pai`, `1. Purpose`, `2. Core Philosophy`, `3. Target System Hierarchy`, `4.1 Understand the person` (+130 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **35 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Settings` connect `Settings` to `pai/config.py`, `auth.py`, `worker.py`, `chat`, `get_session_factory`, `api/documents.py`, `documents/pipeline.py`, `counselor_graph.py`, `app.py`, `onboarding.py`, `taxonomy.py`, `LLMGateway`, `ToolContext`, `orchestrator.py`, `queue.py`, `gateway.py`, `.__init__`, `AuthError`, `SupabaseStorageProvider`, `scanner.py`, `VaultService`, `context.py`, `Person`, `test_pai_orchestration.py`, `SupabaseAuthProvider`, `student/vault/service.py`, `routing.py`, `PAIOrchestrator`, `api/goals.py`, `jwt.py`, `success`, `api/chat.py`, `test_supabase_provider.py`, `agents.py`, `dependencies.py`, `analysis_worker.py`?**
  _High betweenness centrality (0.169) - this node is a cross-community bridge._
- **Why does `Person` connect `Person` to `api/documents.py`, `auth.py`, `worker.py`, `chat`, `get_session_factory`, `candidate_eval.py`, `documents/pipeline.py`, `onboarding.py`, `taxonomy.py`, `orchestrator.py`, `actions/service.py`, `conversations/service.py`, `typed_apply.py`, `VaultService`, `context.py`, `vault_apply.py`, `Settings`, `student/vault/service.py`, `completion.py`, `PAIOrchestrator`, `success`, `api/chat.py`, `update_resource`, `matcher.py`, `dependencies.py`?**
  _High betweenness centrality (0.079) - this node is a cross-community bridge._
- **Why does `LLMGateway` connect `LLMGateway` to `Settings`, `worker.py`, `get_session_factory`, `documents/pipeline.py`, `counselor_graph.py`, `app.py`, `PAIOrchestrator`, `onboarding.py`, `orchestrator.py`, `queue.py`, `gateway.py`, `AuthError`, `api/chat.py`, `test_pai_orchestration.py`, `agents.py`, `analysis_worker.py`, `extractor.py`?**
  _High betweenness centrality (0.054) - this node is a cross-community bridge._
- **Are the 90 inferred relationships involving `Settings` (e.g. with `create_app()` and `lifespan()`) actually correct?**
  _`Settings` has 90 INFERRED edges - model-reasoned connections that need verification._
- **Are the 45 inferred relationships involving `LLMGateway` (e.g. with `lifespan()` and `FactExtractionAgent`) actually correct?**
  _`LLMGateway` has 45 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `get_settings()` (e.g. with `_database_url()` and `test_live_deepseek_structured_smoke()`) actually correct?**
  _`get_settings()` has 2 INFERRED edges - model-reasoned connections that need verification._
- **What connects `pai`, `1. Purpose`, `2. Core Philosophy` to the rest of the system?**
  _135 weakly-connected nodes found - possible documentation gaps or missing edges._