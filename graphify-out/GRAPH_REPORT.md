# Graph Report - Pai-Backend  (2026-09-01)

## Corpus Check
- 258 files · ~92,677 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 2232 nodes · 6255 edges · 156 communities (119 shown, 37 thin omitted)
- Extraction: 93% EXTRACTED · 7% INFERRED · 0% AMBIGUOUS · INFERRED: 449 edges (avg confidence: 0.92)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `3870502c`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- api/documents.py
- get_settings
- research/service.py
- chat
- get_session_factory
- test_document_intelligence.py
- documents/pipeline.py
- counselor_graph.py
- api/chat.py
- LLMGateway
- taxonomy.py
- test_goal_service.py
- ToolContext
- gateway.py
- queue.py
- app.py
- VaultCandidate
- test_goal_detection.py
- AuthError
- memory/formation.py
- conversations/service.py
- typed_apply.py
- api/goals.py
- VaultService
- context.py
- Person
- contracts/schemas.py
- normalize.py
- test_vault_intelligence.py
- test_auth_api.py
- tests/conftest.py
- extractor.py
- Settings
- select_discovery_candidates
- SupabaseAuthProvider
- contracts.py
- student/vault/service.py
- verification/service.py
- apply_completion_to_vault
- test_profile_learning_flow.py
- PAIState
- test_onboarding.py
- InvalidTokenError
- worker.py
- jwt.py
- _blank_to_none
- test_chat_does_not_block.py
- test_person_vault.py
- resolve
- person.py
- test_conversation_stance.py
- SupabaseStorageProvider
- goals/pipeline.py
- SensitiveValueCodec
- TaskProposal
- grounded_life_aim
- mark_intelligence_stale_for_vault_update
- test_supabase_provider.py
- PAI Intelligent Counselor Architecture
- .__init__
- extraction_catalog_hint
- PersonMemoryService
- matcher.py
- vault/catalog.py
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
- scanner.py
- test_pipeline_stages.py
- PAI Counselor Conversation Tone — Problem Analysis
- DigitizationResult
- test_score.py
- BaseModel
- policy
- 17. System Behavior Rules
- native.py
- 15. Component Responsibilities
- datetime
- Improve
- Onboarding fields
- 6. How the current system pushes toward execution (analysis)
- 18. What Should Be Avoided
- Placement AI (PAI) Backend
- env.py
- boosters.py
- 22. Success Criteria
- 12. Counselor Context Requirements
- 16. Decision Examples
- 4. Counselor Responsibilities
- 6. Vault Priority Levels
- .redirects_match_cors
- 4. Three failure modes (one root cause)
- OnboardingSubmit
- API overview
- Database connection troubleshooting
- PostgreSQL on Supabase (required for Phase 2)

## God Nodes (most connected - your core abstractions)
1. `Settings` - 142 edges
2. `Person` - 103 edges
3. `VaultCandidate` - 92 edges
4. `LLMGateway` - 81 edges
5. `AuthError` - 64 edges
6. `get_settings()` - 64 edges
7. `success()` - 51 edges
8. `get_db()` - 44 edges
9. `SupabaseAuthProvider` - 40 edges
10. `policy()` - 39 edges

## Surprising Connections (you probably didn't know these)
- `test_counselor_profile_surfaces_critical_verification()` --uses--> `CounselorContext`  [INFERRED]
  tests/test_document_intelligence.py → src/pai/intelligences/counselor/context.py
- `test_profile_block_falls_back_to_flat_gap_list_without_discovery_candidate()` --uses--> `CounselorContext`  [INFERRED]
  tests/test_profile_discovery.py → src/pai/intelligences/counselor/context.py
- `test_profile_block_renders_top_discovery_candidate_over_flat_gap_list()` --uses--> `CounselorContext`  [INFERRED]
  tests/test_profile_discovery.py → src/pai/intelligences/counselor/context.py
- `test_submit_schema_accepts_country_name_alias()` --uses--> `OnboardingSubmit`  [INFERRED]
  tests/test_onboarding.py → src/pai/workflows/onboarding/contracts.py
- `test_submit_schema_high_school_does_not_need_degree()` --uses--> `OnboardingSubmit`  [INFERRED]
  tests/test_onboarding.py → src/pai/workflows/onboarding/contracts.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Student Intelligence Loop** — src_pai_intelligences_vault, src_pai_domains_student, src_pai_intelligences_goals, src_pai_intelligences_counselor [EXTRACTED 0.90]

## Communities (156 total, 37 thin omitted)

### Community 0 - "api/documents.py"
Cohesion: 0.10
Nodes (61): DocumentRelation, MessageDocument, Chat references a Document Vault item. The file is not stored on the message., Polymorphic links: chat, goal, application, verification, lineage., add_relation(), AsyncSession, UUID, attach_documents_to_message() (+53 more)

### Community 1 - "get_settings"
Cohesion: 0.05
Nodes (86): alias, _bearer, Header, HTTPAuthorizationCredentials, get_settings(), get_person_by_auth(), Mark person deleted and purge vault values before auth deletion., soft_delete_person_data() (+78 more)

### Community 2 - "research/service.py"
Cohesion: 0.11
Nodes (19): Generic search action., Any, Generic search action. Provider-specific work lives in integrations., search(), Any, Tavily web search adapter. Callers go through capabilities.search., tavily_search(), Any (+11 more)

### Community 3 - "chat"
Cohesion: 0.23
Nodes (14): chat(), chat_stream(), ChatRequest, get_chat_messages(), _message_item(), _person_conversation(), AsyncSession, BaseModel (+6 more)

### Community 4 - "get_session_factory"
Cohesion: 0.07
Nodes (46): normalize_email(), PersonBootstrapService, Any, AsyncSession, UUID, Create the Person Vault on first verified auth; skip heavy work on later logins., process_candidates(), AsyncSession (+38 more)

### Community 5 - "test_document_intelligence.py"
Cohesion: 0.19
Nodes (17): BaseModel, reconcile(), ReconcileInput, ReconcileResult, _looks_like_docx(), _looks_like_text(), MIME sniff + size/extension checks. Claimed type must match bytes., sniff_mime() (+9 more)

### Community 6 - "documents/pipeline.py"
Cohesion: 0.17
Nodes (23): Document, DocumentAnalysisRun, DocumentCandidate, DocumentJob, DocumentParty, DocumentVersion, Immutable processing attempt. Never overwrite a completed run., Logical Document Vault item. File bytes live on DocumentVersion. (+15 more)

### Community 7 - "counselor_graph.py"
Cohesion: 0.18
Nodes (22): counselor_seed_messages(), _dict_to_llm_message(), _first_json_object(), iter_counselor_tokens(), _normalize_tool_call(), _parse_conversation_json(), public_reply(), Any (+14 more)

### Community 8 - "api/chat.py"
Cohesion: 0.19
Nodes (17): Base, One counselor transcript per person., Message, OrchestrationRun, save_assistant_message(), start_orchestration_run(), handle_user_message(), _payload_from_state() (+9 more)

### Community 9 - "LLMGateway"
Cohesion: 0.11
Nodes (24): OmnibusLLMExtractor, Single strong multi-domain LLM pass (AgentSpan-style specialist, one call)., _schema_source(), _task_for(), normalize_candidates(), Vault Intelligence — multi-source, multi-domain Person understanding.…, PAI's strong profile-learning brain. Does not write Vault itself., VaultIntelligenceService (+16 more)

### Community 10 - "taxonomy.py"
Cohesion: 0.21
Nodes (21): classify_document(), _best_type(), _best_type_on_filename(), classify_from_name(), default_type(), evidence_eligible(), _filename_tokens(), _generated_types() (+13 more)

### Community 11 - "test_goal_service.py"
Cohesion: 0.08
Nodes (42): _anchor_match_score(), _assert_no_vault_keys(), create_goal(), goal_fact_lines(), _has_hard_conflict(), _norm(), True only when a stable anchor is present on both sides and disagrees. Missing…, Create a brand-new goal record. Caller commits. (+34 more)

### Community 12 - "ToolContext"
Cohesion: 0.12
Nodes (20): Any, Stores non-vault insights. Does NOT mutate Person Vault., RecallSemanticMemoryTool, RememberInsightTool, _counselor_web_note(), build_default_registry(), build_turn_registry(), Any (+12 more)

### Community 13 - "gateway.py"
Cohesion: 0.07
Nodes (27): LLMProvider, BaseModel, Protocol, DeepSeekProvider, LLMProviderError, _parse_tool_call(), Any, BaseModel (+19 more)

### Community 14 - "queue.py"
Cohesion: 0.14
Nodes (24): Background worker processes. Loops only; processing lives in intelligences., intelligence_worker_loop(), Event, run_intelligence_worker_once(), apply_failure(), AsyncSession, BaseException, reclaim_expired_leases() (+16 more)

### Community 15 - "app.py"
Cohesion: 0.18
Nodes (16): create_app(), create_app_from_env(), lifespan(), FastAPI, close_graph_checkpointer(), init_graph_checkpointer(), include_routers(), FastAPI (+8 more)

### Community 16 - "VaultCandidate"
Cohesion: 0.12
Nodes (40): _content_for(), _draft_from_candidate(), importance_of(), memory_key_for(), _observed_status(), _slug(), get_catalog_field(), partition_candidates() (+32 more)

### Community 17 - "test_goal_detection.py"
Cohesion: 0.09
Nodes (30): GoalExtract, parametrize, _extract_anchors_from_intent(), Normalize anchors from intent. Countries via student geo, not a handwritten…, conversation_id(), _make_active_goal(), _make_life_aim(), mock_session() (+22 more)

### Community 18 - "AuthError"
Cohesion: 0.14
Nodes (11): Exception, AuthError, EmailAlreadyInUseError, EmailNotVerifiedError, ForbiddenError, IncorrectPasswordError, InvalidCredentialsError, ProviderUnavailableError (+3 more)

### Community 19 - "memory/formation.py"
Cohesion: 0.06
Nodes (55): Action, ConversationMemory, MemoryEntry, MemoryStore, SemanticMemory, apply_draft(), apply_memory_drafts(), _belongs_to() (+47 more)

### Community 20 - "conversations/service.py"
Cohesion: 0.20
Nodes (19): Conversation, begin_chat_turn(), ConversationNotFoundError, count_person_messages(), create_conversation(), get_conversation_owned(), get_latest_active_conversation(), get_or_create_person_conversation() (+11 more)

### Community 21 - "typed_apply.py"
Cohesion: 0.15
Nodes (32): GoalType, GoalWriteAction, StrEnum, Canonical goal vocabulary. Intelligence classifies; this module validates., normalize_phone(), Phone numbers via Google libphonenumber; stored as E.164., _apply_education_fields(), _apply_education_one() (+24 more)

### Community 22 - "api/goals.py"
Cohesion: 0.14
Nodes (37): GoalIntelligence, activate_goal(), find_matching_goal(), get_active_goal(), get_conversation_active_goal(), get_goal_by_id(), get_goal_intelligence(), goal_to_public() (+29 more)

### Community 23 - "VaultService"
Cohesion: 0.20
Nodes (12): mask_value(), _history_value(), Any, AsyncSession, UUID, Write many vault_value fields in one select + one flush, then evidence rows., Active vault_value map only — no completion scan or typed counts., VaultService (+4 more)

### Community 24 - "context.py"
Cohesion: 0.09
Nodes (41): BaseModel, _advice_gaps(), build_chat_starters(), build_counselor_context(), build_known_facts(), build_person_context_pack(), build_student_context_pack(), chat_stay_payload() (+33 more)

### Community 25 - "Person"
Cohesion: 0.25
Nodes (8): Person, OnboardingService, _present(), Any, AsyncSession, Map the starting profile into the Vault and mark onboarding complete.…, Extract CV facts into the vault and mark onboarding complete., _sparse_get()

### Community 26 - "contracts/schemas.py"
Cohesion: 0.13
Nodes (21): FactExtractionAgent, Compatibility facade over VaultIntelligenceService (chat + document)., Only user-facing agent (PAI Student Counselor) with LangGraph tool loop., StudentConversationAgent, ConversationResult, FactExtractionResult, Any, SchemaRoutingMockProvider (+13 more)

### Community 27 - "normalize.py"
Cohesion: 0.14
Nodes (18): coerce_country(), country_codes_from_value(), _country_names(), extract_countries_from_text(), ISO 3166-1 countries via pycountry — not a handwritten country table., High-recall ISO alpha-2 codes mentioned in free text (names, not 2-letter…, Normalize to ISO 3166-1 alpha-2 (code, alpha-3, English name, or common exonym)., Pull ISO alpha-2 codes from a string, list, or already-normalized code. (+10 more)

### Community 28 - "test_vault_intelligence.py"
Cohesion: 0.11
Nodes (23): _normalize_stream(), Return (candidates, hit labels). High precision only., run_deterministic_boosters(), evidence_in_source(), _fold(), ground_candidates(), Drop LLM facts that are not grounded in the source text., merge_candidates() (+15 more)

### Community 29 - "test_auth_api.py"
Cohesion: 0.11
Nodes (10): _signup_body(), test_resend_verification(), test_session_from_verification_tokens(), test_session_rejects_unverified_tokens(), test_signup_does_not_require_phone(), test_signup_duplicate_email(), test_signup_flow(), test_signup_invalid_email() (+2 more)

### Community 30 - "tests/conftest.py"
Cohesion: 0.23
Nodes (15): auth_headers(), bearer_token(), client(), complete_onboarding(), fake_provider(), onboarded_user(), _ping_db(), postgres_ready() (+7 more)

### Community 31 - "extractor.py"
Cohesion: 0.10
Nodes (21): compact_span(), evidence_grounded(), extraction_confidence(), fold_span(), page_for_span(), Evidence must appear in digitized text. Hallucinated spans are not document…, extract_candidates(), _try_typed() (+13 more)

### Community 32 - "Settings"
Cohesion: 0.12
Nodes (17): BaseSettings, field_validator, Settings, digitize_bytes(), ocr_provider(), NativeDocumentProvider, claim_next_job(), document_worker_loop() (+9 more)

### Community 33 - "select_discovery_candidates"
Cohesion: 0.06
Nodes (63): datetime, _aware(), DiscoveryCandidate, DiscoveryResult, explain(), _goal_relevance(), _message_relevance(), CatalogField (+55 more)

### Community 35 - "contracts.py"
Cohesion: 0.27
Nodes (19): country_options(), BudgetBand, CurrentStatus, EducationLevel, EmploymentType, FieldOfStudy, Gender, IntakeSeason (+11 more)

### Community 36 - "student/vault/service.py"
Cohesion: 0.17
Nodes (30): DeclarativeBase, Goal, Goal, GoalIntelligence, and GoalJob. Tables unchanged (goals,…, Canonical goal identity record — one row per distinct pursuit., Certification, Education, PersonConsent, PersonVault (+22 more)

### Community 37 - "verification/service.py"
Cohesion: 0.27
Nodes (12): DocumentFact, Normalized evidence. Not Person Vault truth., Persistent conflict. Counselor chat and Document Vault resolve through one…, VerificationCase, CaseNotFoundError, close_open_cases_for_fields(), list_open_cases(), open_case() (+4 more)

### Community 38 - "apply_completion_to_vault"
Cohesion: 0.19
Nodes (23): PersonVault, Priority, update_person_profile(), apply_completion_to_vault(), build_vault_status(), compute_completion(), compute_completion_from_snapshot(), field_is_present_in_snapshot() (+15 more)

### Community 39 - "test_profile_learning_flow.py"
Cohesion: 0.13
Nodes (19): classify_turn(), counseling_reply_max_tokens(), counselor_web_search_enabled(), _has_profile_signal(), is_greeting(), Offer web_search; the counselor LLM decides whether to call it., Hi / thanks / ok — not a real counseling turn., Greetings stay tiny so DeepSeek cannot spend 15s writing an essay. (+11 more)

### Community 40 - "PAIState"
Cohesion: 0.12
Nodes (12): invalidate_counselor_cache(), build_pai_graph(), Counselor reply only. Extraction/Vault run after the user has the text., Vault/memory/tasks after the student already has the reply., PAIState, PendingConfirmation, BaseModel, RunError (+4 more)

### Community 41 - "test_onboarding.py"
Cohesion: 0.10
Nodes (10): test_enum_catalog_exposes_dropdown_ids(), test_submit_schema_accepts_country_name_alias(), test_submit_schema_high_school_does_not_need_degree(), test_submit_schema_minimal_criticals_are_enough(), test_submit_schema_normalizes_phone_to_e164(), test_submit_schema_optional_fields_can_be_omitted(), test_submit_schema_rejects_unknown_country(), test_submit_schema_rejects_vague_primary_goal() (+2 more)

### Community 42 - "InvalidTokenError"
Cohesion: 0.09
Nodes (8): InvalidTokenError, Auth domain: signup/login, JWT, Supabase provider., AuthProvider, GenericActionResult, ProviderSession, Protocol, SignupResult, FakeAuthProvider

### Community 43 - "worker.py"
Cohesion: 0.17
Nodes (19): GoalIntelligence, GoalJob, Background-computed intelligence summary for one goal. One row per goal., Durable goal intelligence job. Same poll-loop pattern as PersonJob., _build_vault_snapshot(), claim_next_goal_job(), goal_worker_loop(), _load_goal_and_intel() (+11 more)

### Community 44 - "jwt.py"
Cohesion: 0.21
Nodes (15): _fetch_jwks(), _jwks_url(), _key_for_token(), Any, Response, Access-token verification for Supabase (HS256 legacy + ES256/RS256 JWKS)., Network verification fallback for asymmetric JWTs., Verify Supabase user JWT (HS256 secret or ES256/RS256 via JWKS). (+7 more)

### Community 45 - "_blank_to_none"
Cohesion: 0.32
Nodes (5): _blank_to_none(), OnboardingSkillItem, OnboardingTestScoreItem, OnboardingWorkItem, BaseModel

### Community 46 - "test_chat_does_not_block.py"
Cohesion: 0.12
Nodes (15): fake_queue(), FakeQueue, _make_fake_goal(), asyncio, fixture, Tests that chat reply path is never blocked by the goal intelligence pipeline.…, CounselorContext.profile_block() must work when active_goal_brief is None., When active_goal_brief is present, it replaces the legacy goal line. (+7 more)

### Community 48 - "resolve"
Cohesion: 0.16
Nodes (23): GoalJob, enqueue_goal_intelligence_job(), Stage a goal intelligence job. Idempotent: skip if a pending/running job…, _classify_goal_type(), _fold(), _goal_name_tokens(), _has_hard_conflict_on_goal(), _maybe_enqueue() (+15 more)

### Community 49 - "person.py"
Cohesion: 0.08
Nodes (52): PersonDecision, PersonEvent, append_event(), event_to_public(), goal_fact_lines(), list_recent_events(), Any, AsyncSession (+44 more)

### Community 50 - "test_conversation_stance.py"
Cohesion: 0.16
Nodes (20): Phase, compute_stance(), ConversationStance, Conversation stance — deterministic, per-turn counselor posture. The…, Decide the counselor's posture for this turn. Defaults are conservative: when…, _stance(), _phase(), Conversation stance: deterministic counselor posture per turn (no LLM). (+12 more)

### Community 51 - "SupabaseStorageProvider"
Cohesion: 0.27
Nodes (3): UUID, StorageAccessError, SupabaseStorageProvider

### Community 52 - "goals/pipeline.py"
Cohesion: 0.23
Nodes (17): build_counselor_brief(), _goal_guidance(), _llm_json(), Any, Goal intelligence pipeline — four stages run sequentially, each isolated.…, Ground requirements/options/deadlines in live Research Intelligence, then…, Compare user's profile against research output. Input: research JSON + vault…, Identify missing items for this goal. Input: assessment JSON Output: list of… (+9 more)

### Community 53 - "SensitiveValueCodec"
Cohesion: 0.22
Nodes (3): Any, Fernet-based encoding for sensitive vault payloads (no custom crypto)., SensitiveValueCodec

### Community 54 - "TaskProposal"
Cohesion: 0.28
Nodes (5): Planner intelligence. Proposes actions; Kernel + domains persist them., plan_next_actions(), Planner intelligence — next actions. Does not persist or execute them., TaskProposal, test_needs_intelligence_skips_greetings()

### Community 55 - "grounded_life_aim"
Cohesion: 0.19
Nodes (15): grounded_life_aim(), GroundedLifeAim, LLM classified life_aim only if evidence is a span of the student text., GoalExtract, field_validator, Living brief in the student's words — language-agnostic, not an enum., _extract(), test_english_life_aim_is_stored() (+7 more)

### Community 56 - "mark_intelligence_stale_for_vault_update"
Cohesion: 0.21
Nodes (13): mark_intelligence_stale_for_vault_update(), When a Vault field changes, mark affected goal summaries stale and re-enqueue.…, _mock_goal(), asyncio, Selective Vault→Goals refresh tests. Verifies that when a Vault field changes:…, Spot-check that key Vault fields are in the map., Updating application.test_scores must stale + enqueue admission goals., Updating a field not in VAULT_FIELDS_THAT_AFFECT_GOALS must not touch any goal. (+5 more)

### Community 57 - "test_supabase_provider.py"
Cohesion: 0.33
Nodes (9): asyncio, _settings_kwargs(), test_redirect_origin_must_be_in_cors(), test_redirect_url_cannot_be_site_root(), test_supabase_login_incorrect_password(), test_supabase_login_unknown_email(), test_supabase_signup_rejects_existing_email(), test_supabase_signup_without_session() (+1 more)

### Community 58 - "PAI Intelligent Counselor Architecture"
Cohesion: 0.11
Nodes (19): 10. Goals and Counselor Relationship, 11. Current-Turn and Deferred Intelligence Behavior, 13. Counselor Judgment Layer, 14. Ideal Message Flow, 1. Purpose, 20. Suggested Profile Discovery Logic, 21. Desired Counselor Behavior Over Time, 23. Final Target Model (+11 more)

### Community 59 - ".__init__"
Cohesion: 0.29
Nodes (6): BaseCheckpointSaver, FactExtractionAgent, LLMGateway, get_graph_checkpointer(), Settings, StudentConversationAgent

### Community 60 - "extraction_catalog_hint"
Cohesion: 0.25
Nodes (9): Environment, extraction_catalog_hint(), Compact writable field list for the fact-extraction LLM (exact keys only)., _render(), test_catalog_tells_llm_about_career_writes(), test_omnibus_cv_prompt_asks_for_full_resume(), test_prompt_render_student_conversation(), test_extraction_catalog_lists_admissions_keys() (+1 more)

### Community 61 - "PersonMemoryService"
Cohesion: 0.17
Nodes (8): Long-term semantic + session conversation memory (AgentSpan-backed)., PersonMemoryService, UUID, Facade: conversation window + formed long-term memory per student. Agents may…, asyncio, test_semantic_memory_roundtrip(), test_tool_registry_lists_openai_schemas(), test_web_search_degrades_without_api_key()

### Community 62 - "matcher.py"
Cohesion: 0.21
Nodes (12): match_student(), fold_name(), name_tokens(), names_match(), parse_date(), Any, normalize_field(), Any (+4 more)

### Community 63 - "vault/catalog.py"
Cohesion: 0.33
Nodes (5): CatalogField, _fields(), Person Vault field registry (C / I / E priorities)., test_grow_vault_schema_is_idempotent(), test_vault_catalog_covers_guidance_core()

### Community 64 - "Goals Domain"
Cohesion: 0.29
Nodes (7): Goals Domain, Student Domain, Counselor Intelligence, Goal Intelligence, Vault Intelligence, Kernel Write Gates, Onboarding Workflow

### Community 65 - "PAI check workflow"
Cohesion: 0.13
Nodes (15): 0. Start the server, Automated check (no Swagger), PAI check workflow, Route map (student-facing), Story 10 — I patch a vault field myself, Story 1 — I sign up and log in, Story 2 — Chat is locked until I onboard, Story 3 — I complete the starting profile (form path) (+7 more)

### Community 123 - "scanner.py"
Cohesion: 0.50
Nodes (3): Malware scan hook. Default is a no-op until DOCUMENT_MALWARE_SCAN_PROVIDER is…, scan_bytes(), ScanResult

### Community 126 - "test_pipeline_stages.py"
Cohesion: 0.21
Nodes (16): _fake_gateway(), _live_research(), asyncio, Pipeline stage isolation tests — no LLM API calls. Each stage is tested with a…, The spec's canonical test: missing IELTS must appear as a blocking gap., Brief must never exceed _BRIEF_MAX_LINES lines — hard constraint from spec., Full pipeline with mocked LLM must produce status='ready' and a brief., Create a gateway mock that returns a fixed JSON or text. (+8 more)

### Community 127 - "PAI Counselor Conversation Tone — Problem Analysis"
Cohesion: 0.12
Nodes (14): 10. Likely fix surface (conceptual only), 11. Success criteria (product), 12. Open questions, 1. Summary, 2. What good counseling sounds like, 3. Two kinds of certainty (often confused), 5. What a real counselor does before “completion”, 7. Missing concept: goal comprehension maturity (+6 more)

### Community 128 - "DigitizationResult"
Cohesion: 0.14
Nodes (16): DigitizationResult, BaseModel, DocumentOCRProvider, Protocol, _merge_usage(), OpenAIVisionProvider, _page_marker(), pages_for_vision() (+8 more)

### Community 129 - "test_score.py"
Cohesion: 0.67
Nodes (3): BaseModel, TestScoreExtraction, to_field_map()

### Community 131 - "policy"
Cohesion: 0.22
Nodes (15): policy(), Any, Load Document Intelligence taxonomy and policy from package data (not code)., _read(), field_criticality(), field_sensitivity(), rank(), _as_float() (+7 more)

### Community 132 - "17. System Behavior Rules"
Cohesion: 0.18
Nodes (11): 17. System Behavior Rules, Rule 10 — Keep intelligence supporting the counselor, Rule 1 — Never reason from the latest message alone, Rule 2 — User preference is evidence, not truth, Rule 3 — Active Goal is not a command, Rule 4 — Vault completion is continuous, Rule 5 — Never turn counseling into a questionnaire, Rule 6 — Prefer one high-value question (+3 more)

### Community 133 - "native.py"
Cohesion: 0.27
Nodes (9): _docx_text(), extract_text_from_bytes(), pdf_page_texts(), _pdf_text(), Pull plain text from uploaded CV/documents. Empty string means unreadable., _docx_with_text(), CV/document text extraction — PDF and DOCX must yield real text, not a…, test_binary_placeholder_is_gone() (+1 more)

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

### Community 141 - "env.py"
Cohesion: 0.28
Nodes (10): _database_url(), run_migrations_offline(), run_migrations_online(), StudentTask, is_fact_recording_task(), list_tasks_for_person(), process_task_proposals(), AsyncSession (+2 more)

### Community 142 - "boosters.py"
Cohesion: 0.50
Nodes (3): _cand(), Any, Deterministic high-precision extractors — never miss clear GPA/marks/countries.

### Community 143 - "22. Success Criteria"
Cohesion: 0.33
Nodes (6): 22. Success Criteria, Architecture, Counselor intelligence, Goal behavior, Question quality, User understanding

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

### Community 152 - "OnboardingSubmit"
Cohesion: 0.18
Nodes (7): _linkedin_url(), OnboardingSubmit, date, field_validator, model_validator, Starting profile. Categorical fields are closed enums; GET /onboarding returns…, _reasonable_dob()

### Community 153 - "API overview"
Cohesion: 0.33
Nodes (6): API overview, Auth (Phase 1), Counselor & documents (PAI), Health, Onboarding (lightweight seed after first verified login), Person & Vault (Phase 2)

### Community 154 - "Database connection troubleshooting"
Cohesion: 0.33
Nodes (6): `Can't load plugin: sqlalchemy.dialects:driver`, Database connection troubleshooting, `getaddrinfo failed` for `db.PROJECT_REF.supabase.co`, `tenant/user postgres.PROJECT_REF not found`, Verified auth users but empty `persons` table, Workaround without local DB connectivity

### Community 156 - "PostgreSQL on Supabase (required for Phase 2)"
Cohesion: 0.50
Nodes (4): Environment variables, How to set `DATABASE_URL` correctly, PostgreSQL on Supabase (required for Phase 2), Run migrations

## Knowledge Gaps
- **135 isolated node(s):** `1. Purpose`, `2. Core Philosophy`, `3. Target System Hierarchy`, `4.1 Understand the person`, `4.2 Understand the user's goals` (+130 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **37 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Settings` connect `Settings` to `DigitizationResult`, `get_settings`, `api/documents.py`, `chat`, `get_session_factory`, `test_document_intelligence.py`, `documents/pipeline.py`, `counselor_graph.py`, `api/chat.py`, `LLMGateway`, `taxonomy.py`, `ToolContext`, `gateway.py`, `queue.py`, `app.py`, `AuthError`, `memory/formation.py`, `.redirects_match_cors`, `api/goals.py`, `VaultService`, `Person`, `contracts/schemas.py`, `tests/conftest.py`, `SupabaseAuthProvider`, `student/vault/service.py`, `test_profile_learning_flow.py`, `worker.py`, `jwt.py`, `SupabaseStorageProvider`, `goals/pipeline.py`, `SensitiveValueCodec`, `test_supabase_provider.py`, `PersonMemoryService`, `scanner.py`?**
  _High betweenness centrality (0.150) - this node is a cross-community bridge._
- **Why does `Person` connect `Person` to `api/documents.py`, `get_settings`, `student/vault/service.py`, `get_session_factory`, `apply_completion_to_vault`, `documents/pipeline.py`, `api/chat.py`, `verification/service.py`, `taxonomy.py`, `worker.py`, `env.py`, `VaultCandidate`, `person.py`, `conversations/service.py`, `typed_apply.py`, `VaultService`, `matcher.py`?**
  _High betweenness centrality (0.063) - this node is a cross-community bridge._
- **Why does `build_counselor_context()` connect `context.py` to `api/documents.py`, `get_settings`, `select_discovery_candidates`, `student/vault/service.py`, `verification/service.py`, `test_profile_learning_flow.py`, `api/chat.py`, `test_goal_service.py`, `test_conversation_stance.py`, `conversations/service.py`, `api/goals.py`, `VaultService`?**
  _High betweenness centrality (0.052) - this node is a cross-community bridge._
- **Are the 86 inferred relationships involving `Settings` (e.g. with `create_app()` and `lifespan()`) actually correct?**
  _`Settings` has 86 INFERRED edges - model-reasoned connections that need verification._
- **Are the 44 inferred relationships involving `LLMGateway` (e.g. with `lifespan()` and `FactExtractionAgent`) actually correct?**
  _`LLMGateway` has 44 INFERRED edges - model-reasoned connections that need verification._
- **Are the 11 inferred relationships involving `AuthError` (e.g. with `create_app()` and `LinkedInSourceDomain`) actually correct?**
  _`AuthError` has 11 INFERRED edges - model-reasoned connections that need verification._
- **What connects `1. Purpose`, `2. Core Philosophy`, `3. Target System Hierarchy` to the rest of the system?**
  _135 weakly-connected nodes found - possible documentation gaps or missing edges._