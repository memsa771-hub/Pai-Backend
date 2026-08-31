# Graph Report - Pai-Backend  (2026-08-31)

## Corpus Check
- 258 files · ~92,373 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 2212 nodes · 6367 edges · 157 communities (122 shown, 35 thin omitted)
- Extraction: 93% EXTRACTED · 7% INFERRED · 0% AMBIGUOUS · INFERRED: 414 edges (avg confidence: 0.92)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `8244b426`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- api/documents.py
- auth.py
- research/service.py
- chat
- get_session_factory
- test_document_intelligence.py
- documents/pipeline.py
- counselor_graph.py
- PersonBootstrapService
- LLMGateway
- taxonomy.py
- test_goal_service.py
- ToolContext
- LLMMessage
- app.py
- memory/formation.py
- VaultCandidate
- test_goal_detection.py
- AuthError
- postgres_store.py
- api/chat.py
- typed_apply.py
- goals/service.py
- student/vault/service.py
- context.py
- Person
- test_pai_orchestration.py
- normalize.py
- test_vault_intelligence.py
- test_auth_api.py
- upsert_goal_from_anchors
- extractor.py
- Settings
- select_discovery_candidates
- SupabaseAuthProvider
- contracts.py
- person/models.py
- InvalidTokenError
- completion.py
- routing.py
- PAIOrchestrator
- test_onboarding.py
- AuthProvider
- worker.py
- jwt.py
- _blank_to_none
- test_chat_does_not_block.py
- test_person_vault.py
- Goal
- person.py
- test_conversation_stance.py
- delete_account
- goals/pipeline.py
- opening.py
- apply_completion_to_vault
- grounded_life_aim
- mark_intelligence_stale_for_vault_update
- test_supabase_provider.py
- PAI Intelligent Counselor Architecture
- get_db
- extraction_catalog_hint
- pai/config.py
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
- test_pipeline_stages.py
- PAI Counselor Conversation Tone — Problem Analysis
- DigitizationResult
- drafts_from_turn
- engine.py
- 17. System Behavior Rules
- test_document_cv_extract.py
- 15. Component Responsibilities
- ground.py
- Improve
- Onboarding fields
- 6. How the current system pushes toward execution (analysis)
- 18. What Should Be Avoided
- Placement AI (PAI) Backend
- orchestrator.py
- boosters.py
- 22. Success Criteria
- ._goal_type_token
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

## Communities (157 total, 35 thin omitted)

### Community 0 - "api/documents.py"
Cohesion: 0.08
Nodes (72): Document, DocumentCandidate, DocumentFact, DocumentJob, DocumentRelation, DocumentVersion, MessageDocument, Chat references a Document Vault item. The file is not stored on the message. (+64 more)

### Community 1 - "auth.py"
Cohesion: 0.16
Nodes (23): ApiErrorBody, ApiErrorResponse, ApiSuccessResponse, AuthSessionPublic, EmailOnlyRequest, HealthData, LoginRequest, LoginResponseData (+15 more)

### Community 2 - "research/service.py"
Cohesion: 0.11
Nodes (19): Generic search action., Any, Generic search action. Provider-specific work lives in integrations., search(), Any, Tavily web search adapter. Callers go through capabilities.search., tavily_search(), Any (+11 more)

### Community 3 - "chat"
Cohesion: 0.23
Nodes (14): chat(), chat_stream(), ChatRequest, get_chat_messages(), _message_item(), _person_conversation(), AsyncSession, BaseModel (+6 more)

### Community 4 - "get_session_factory"
Cohesion: 0.06
Nodes (58): process_candidates(), AsyncSession, _engine_connect_args(), get_db_session(), get_engine(), get_session_factory(), _ipv4_for_host(), _is_remote_postgres() (+50 more)

### Community 5 - "test_document_intelligence.py"
Cohesion: 0.20
Nodes (17): BaseModel, reconcile(), ReconcileInput, ReconcileResult, _looks_like_docx(), _looks_like_text(), MIME sniff + size/extension checks. Claimed type must match bytes., sniff_mime() (+9 more)

### Community 6 - "documents/pipeline.py"
Cohesion: 0.19
Nodes (22): DocumentAnalysisRun, DocumentParty, Immutable processing attempt. Never overwrite a completed run., policy(), field_criticality(), field_sensitivity(), rank(), extraction_confidence() (+14 more)

### Community 7 - "counselor_graph.py"
Cohesion: 0.17
Nodes (23): counselor_seed_messages(), _dict_to_llm_message(), _first_json_object(), iter_counselor_tokens(), _normalize_tool_call(), _parse_conversation_json(), public_reply(), Any (+15 more)

### Community 8 - "PersonBootstrapService"
Cohesion: 0.23
Nodes (10): PersonVault, normalize_email(), PersonBootstrapService, Any, AsyncSession, UUID, Create the Person Vault on first verified auth; skip heavy work on later logins., update_person_profile() (+2 more)

### Community 9 - "LLMGateway"
Cohesion: 0.14
Nodes (22): OmnibusLLMExtractor, Single strong multi-domain LLM pass (AgentSpan-style specialist, one call)., _schema_source(), _task_for(), Vault Intelligence — multi-source, multi-domain Person understanding.…, PAI's strong profile-learning brain. Does not write Vault itself., VaultIntelligenceService, ChatSourceDomain (+14 more)

### Community 10 - "taxonomy.py"
Cohesion: 0.19
Nodes (18): classify_document(), _best_type(), _best_type_on_filename(), classify_from_name(), default_type(), _filename_tokens(), _generated_types(), known_types() (+10 more)

### Community 11 - "test_goal_service.py"
Cohesion: 0.11
Nodes (31): _anchor_match_score(), _has_hard_conflict(), True only when a stable anchor is present on both sides and disagrees. Missing…, Return 0-1 similarity of new anchors against existing goal. Matching key types:…, _make_goal(), mock_session(), person_id(), asyncio (+23 more)

### Community 12 - "ToolContext"
Cohesion: 0.12
Nodes (23): Any, Stores non-vault insights. Does NOT mutate Person Vault., RecallSemanticMemoryTool, RememberInsightTool, build_default_registry(), build_turn_registry(), Any, Deterministic per-turn tool set — avoid handing every tool to every request. (+15 more)

### Community 13 - "LLMMessage"
Cohesion: 0.07
Nodes (26): BaseModel, LLMProvider, BaseModel, Protocol, DeepSeekProvider, LLMProviderError, _parse_tool_call(), Any (+18 more)

### Community 14 - "app.py"
Cohesion: 0.05
Nodes (54): BaseCheckpointSaver, create_app(), create_app_from_env(), lifespan(), FastAPI, close_graph_checkpointer(), get_graph_checkpointer(), init_graph_checkpointer() (+46 more)

### Community 15 - "memory/formation.py"
Cohesion: 0.16
Nodes (27): Action, apply_draft(), apply_memory_drafts(), _belongs_to(), _draft_from_candidate(), _formation_blob(), importance_of(), _jaccard() (+19 more)

### Community 16 - "VaultCandidate"
Cohesion: 0.14
Nodes (33): _content_for(), _kind_for(), _observed_status(), partition_candidates(), Separate extraction from memory selection. Recall-first extractors may emit…, CandidateResult, VaultCandidate, assertion_of() (+25 more)

### Community 17 - "test_goal_detection.py"
Cohesion: 0.09
Nodes (30): parametrize, _extract_anchors_from_intent(), Normalize anchors from intent. Countries via student geo, not a handwritten…, GoalExtract, Living brief in the student's words — language-agnostic, not an enum., _make_active_goal(), _make_life_aim(), mock_session() (+22 more)

### Community 18 - "AuthError"
Cohesion: 0.23
Nodes (14): Exception, Malware scan hook. Default is a no-op until DOCUMENT_MALWARE_SCAN_PROVIDER is…, scan_bytes(), ScanResult, AuthError, CsrfError, EmailAlreadyInUseError, EmailNotVerifiedError (+6 more)

### Community 19 - "postgres_store.py"
Cohesion: 0.09
Nodes (20): ConversationMemory, MemoryEntry, MemoryStore, SemanticMemory, format_for_recall(), record_from_row(), Persisted memory scoped to a person. Unstructured notes (AgentSpan remember())…, SemanticMemoryRow (+12 more)

### Community 20 - "api/chat.py"
Cohesion: 0.18
Nodes (25): One counselor transcript per person., Conversation, Message, OrchestrationRun, begin_chat_turn(), ConversationNotFoundError, count_person_messages(), create_conversation() (+17 more)

### Community 21 - "typed_apply.py"
Cohesion: 0.19
Nodes (28): normalize_phone(), Phone numbers via Google libphonenumber; stored as E.164., Education, _apply_education_fields(), _apply_education_one(), apply_typed_candidate(), _as_items(), _education_payload() (+20 more)

### Community 22 - "goals/service.py"
Cohesion: 0.16
Nodes (31): activate_goal(), get_active_goal(), get_conversation_active_goal(), get_goal_by_id(), get_goal_intelligence(), goal_fact_lines(), goal_to_public(), list_goals() (+23 more)

### Community 23 - "student/vault/service.py"
Cohesion: 0.12
Nodes (25): VaultEvidence, VaultHistory, VaultValue, get_catalog_field(), Person Vault field registry (C / I / E priorities)., mask_value(), Any, Fernet-based encoding for sensitive vault payloads (no custom crypto). (+17 more)

### Community 24 - "context.py"
Cohesion: 0.13
Nodes (31): _advice_gaps(), build_chat_starters(), build_counselor_context(), build_known_facts(), build_person_context_pack(), build_student_context_pack(), chat_stay_payload(), context_pack_to_json() (+23 more)

### Community 25 - "Person"
Cohesion: 0.23
Nodes (9): Person, OnboardingService, _present(), Any, AsyncSession, Seed a small Person profile. Chat, documents, and later updates enrich the…, Map the starting profile into the Vault and mark onboarding complete.…, Extract CV facts into the vault and mark onboarding complete. (+1 more)

### Community 26 - "test_pai_orchestration.py"
Cohesion: 0.14
Nodes (20): FactExtractionAgent, Compatibility facade over VaultIntelligenceService (chat + document)., Only user-facing agent (PAI Student Counselor) with LangGraph tool loop., StudentConversationAgent, ConversationResult, FactExtractionResult, Any, SchemaRoutingMockProvider (+12 more)

### Community 27 - "normalize.py"
Cohesion: 0.14
Nodes (18): coerce_country(), country_codes_from_value(), _country_names(), extract_countries_from_text(), ISO 3166-1 countries via pycountry — not a handwritten country table., High-recall ISO alpha-2 codes mentioned in free text (names, not 2-letter…, Normalize to ISO 3166-1 alpha-2 (code, alpha-3, English name, or common exonym)., Pull ISO alpha-2 codes from a string, list, or already-normalized code. (+10 more)

### Community 28 - "test_vault_intelligence.py"
Cohesion: 0.14
Nodes (18): _normalize_stream(), Return (candidates, hit labels). High precision only., run_deterministic_boosters(), merge_candidates(), _merge_key(), _norm_val(), Any, Merge LLM + booster candidates; prefer higher confidence / corrections. (+10 more)

### Community 29 - "test_auth_api.py"
Cohesion: 0.11
Nodes (10): _signup_body(), test_resend_verification(), test_session_from_verification_tokens(), test_session_rejects_unverified_tokens(), test_signup_does_not_require_phone(), test_signup_duplicate_email(), test_signup_flow(), test_signup_invalid_email() (+2 more)

### Community 30 - "upsert_goal_from_anchors"
Cohesion: 0.17
Nodes (18): _assert_no_vault_keys(), create_goal(), find_matching_goal(), Any, Find an existing (non-archived) goal that is the same pursuit as the incoming…, Create a brand-new goal record. Caller commits., Merge new anchors into goal. Returns True if anything changed., Find-or-create. Returns (goal, GoalWriteAction value). Switch is decided by the… (+10 more)

### Community 31 - "extractor.py"
Cohesion: 0.09
Nodes (23): compact_span(), evidence_grounded(), fold_span(), page_for_span(), Evidence must appear in digitized text. Hallucinated spans are not document…, extract_candidates(), _try_typed(), DegreeExtraction (+15 more)

### Community 32 - "Settings"
Cohesion: 0.15
Nodes (28): BaseSettings, get_settings(), field_validator, Settings, change_password(), _clear_session_cookies(), confirm_email_verification(), establish_session() (+20 more)

### Community 33 - "select_discovery_candidates"
Cohesion: 0.06
Nodes (62): _aware(), DiscoveryCandidate, DiscoveryResult, explain(), _goal_relevance(), _message_relevance(), datetime, Profile Discovery / Gap Selection — deterministic ranking of missing Vault… (+54 more)

### Community 34 - "SupabaseAuthProvider"
Cohesion: 0.20
Nodes (3): Any, AsyncClient, SupabaseAuthProvider

### Community 35 - "contracts.py"
Cohesion: 0.27
Nodes (19): country_options(), BudgetBand, CurrentStatus, EducationLevel, EmploymentType, FieldOfStudy, Gender, IntakeSeason (+11 more)

### Community 36 - "person/models.py"
Cohesion: 0.13
Nodes (26): _database_url(), run_migrations_offline(), run_migrations_online(), DeclarativeBase, Goal, GoalIntelligence, and GoalJob. Tables unchanged (goals,…, PersonDecision, Certification, PersonConsent (+18 more)

### Community 37 - "InvalidTokenError"
Cohesion: 0.19
Nodes (4): InvalidTokenError, UserNotFoundError, ProviderSession, FakeAuthProvider

### Community 38 - "completion.py"
Cohesion: 0.28
Nodes (16): Priority, CatalogField, _fields(), build_vault_status(), compute_completion(), compute_completion_from_snapshot(), field_is_present_in_snapshot(), _field_label() (+8 more)

### Community 39 - "routing.py"
Cohesion: 0.15
Nodes (17): classify_turn(), counseling_reply_max_tokens(), counselor_web_search_enabled(), _has_profile_signal(), is_greeting(), Offer web_search; the counselor LLM decides whether to call it., Hi / thanks / ok — not a real counseling turn., Greetings stay tiny so DeepSeek cannot spend 15s writing an essay. (+9 more)

### Community 40 - "PAIOrchestrator"
Cohesion: 0.12
Nodes (13): build_pai_graph(), PAIOrchestrator, AsyncSession, UUID, Counselor reply only. Extraction/Vault run after the user has the text., Vault/memory/tasks after the student already has the reply., Persist which gap was surfaced this turn (doc §7 Rule 7 — don't keep re-…, Counselor coordinator. Does not own Vault/Goals/Documents writes. (+5 more)

### Community 41 - "test_onboarding.py"
Cohesion: 0.10
Nodes (10): test_enum_catalog_exposes_dropdown_ids(), test_submit_schema_accepts_country_name_alias(), test_submit_schema_high_school_does_not_need_degree(), test_submit_schema_minimal_criticals_are_enough(), test_submit_schema_normalizes_phone_to_e164(), test_submit_schema_optional_fields_can_be_omitted(), test_submit_schema_rejects_unknown_country(), test_submit_schema_rejects_vague_primary_goal() (+2 more)

### Community 42 - "AuthProvider"
Cohesion: 0.13
Nodes (5): Auth domain: signup/login, JWT, Supabase provider., AuthProvider, GenericActionResult, Protocol, SignupResult

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

### Community 48 - "Goal"
Cohesion: 0.16
Nodes (23): Goal, Canonical goal identity record — one row per distinct pursuit., enqueue_goal_intelligence_job(), Stage a goal intelligence job. Idempotent: skip if a pending/running job…, GoalWriteAction, Canonical goal vocabulary. Intelligence classifies; this module validates., _fold(), _goal_name_tokens() (+15 more)

### Community 49 - "person.py"
Cohesion: 0.10
Nodes (43): PersonEvent, append_event(), event_to_public(), goal_fact_lines(), list_recent_events(), Any, AsyncSession, UUID (+35 more)

### Community 50 - "test_conversation_stance.py"
Cohesion: 0.16
Nodes (20): Phase, compute_stance(), ConversationStance, Conversation stance — deterministic, per-turn counselor posture. The…, Decide the counselor's posture for this turn. Defaults are conservative: when…, _stance(), _phase(), Conversation stance: deterministic counselor posture per turn (no LLM). (+12 more)

### Community 51 - "delete_account"
Cohesion: 0.33
Nodes (6): get_person_by_auth(), Mark person deleted and purge vault values before auth deletion., soft_delete_person_data(), delete_account(), AsyncSession, delete

### Community 52 - "goals/pipeline.py"
Cohesion: 0.23
Nodes (17): build_counselor_brief(), _goal_guidance(), _llm_json(), Any, Goal intelligence pipeline — four stages run sequentially, each isolated.…, Ground requirements/options/deadlines in live Research Intelligence, then…, Compare user's profile against research output. Input: research JSON + vault…, Identify missing items for this goal. Input: assessment JSON Output: list of… (+9 more)

### Community 53 - "opening.py"
Cohesion: 0.17
Nodes (13): compose_opening(), _opening_facts(), Vault-grounded first message. Unique facts, goal/education first., Dedupe by label and by value; rank by known-fact kind, not a country list., ensure_thread_opening(), AsyncSession, UUID, Counselor decides PAI's first message. Conversation domain only persists it. (+5 more)

### Community 54 - "apply_completion_to_vault"
Cohesion: 0.47
Nodes (10): create_resource(), delete_resource(), list_resources(), Any, AsyncSession, UUID, update_resource(), apply_completion_to_vault() (+2 more)

### Community 55 - "grounded_life_aim"
Cohesion: 0.33
Nodes (12): grounded_life_aim(), GroundedLifeAim, LLM classified life_aim only if evidence is a span of the student text., _extract(), test_english_life_aim_is_stored(), test_exploring_and_pivot_come_from_the_classifier(), test_mixed_aim_and_attach_keeps_only_the_aim(), test_model_cannot_invent_a_goal_not_in_the_message() (+4 more)

### Community 56 - "mark_intelligence_stale_for_vault_update"
Cohesion: 0.21
Nodes (13): mark_intelligence_stale_for_vault_update(), When a Vault field changes, mark affected goal summaries stale and re-enqueue.…, _mock_goal(), asyncio, Selective Vault→Goals refresh tests. Verifies that when a Vault field changes:…, Spot-check that key Vault fields are in the map., Updating application.test_scores must stale + enqueue admission goals., Updating a field not in VAULT_FIELDS_THAT_AFFECT_GOALS must not touch any goal. (+5 more)

### Community 57 - "test_supabase_provider.py"
Cohesion: 0.26
Nodes (11): asyncio, fixture, _settings_kwargs(), supabase_settings(), test_redirect_origin_must_be_in_cors(), test_redirect_url_cannot_be_site_root(), test_supabase_login_incorrect_password(), test_supabase_login_unknown_email() (+3 more)

### Community 58 - "PAI Intelligent Counselor Architecture"
Cohesion: 0.11
Nodes (19): 10. Goals and Counselor Relationship, 11. Current-Turn and Deferred Intelligence Behavior, 13. Counselor Judgment Layer, 14. Ideal Message Flow, 1. Purpose, 20. Suggested Profile Discovery Logic, 21. Desired Counselor Behavior Over Time, 23. Final Target Model (+11 more)

### Community 59 - "get_db"
Cohesion: 0.16
Nodes (28): get_db(), AsyncSession, resolve_person_from_token(), get_onboarding(), AsyncSession, Depends, get, JSONResponse (+20 more)

### Community 60 - "extraction_catalog_hint"
Cohesion: 0.25
Nodes (9): Environment, extraction_catalog_hint(), Compact writable field list for the fact-extraction LLM (exact keys only)., _render(), test_catalog_tells_llm_about_career_writes(), test_omnibus_cv_prompt_asks_for_full_resume(), test_prompt_render_student_conversation(), test_extraction_catalog_lists_admissions_keys() (+1 more)

### Community 61 - "pai/config.py"
Cohesion: 0.16
Nodes (4): Long-term semantic + session conversation memory (AgentSpan-backed)., PersonMemoryService, UUID, Facade: conversation window + formed long-term memory per student. Agents may…

### Community 62 - "matcher.py"
Cohesion: 0.18
Nodes (14): evidence_eligible(), match_student(), fold_name(), name_tokens(), names_match(), parse_date(), Any, normalize_field() (+6 more)

### Community 63 - "AuthService"
Cohesion: 0.17
Nodes (4): _session_json(), AuthService, Turn tokens from the email-verification redirect into a PAI session., SessionBundle

### Community 64 - "Goals Domain"
Cohesion: 0.29
Nodes (7): Goals Domain, Student Domain, Counselor Intelligence, Goal Intelligence, Vault Intelligence, Kernel Write Gates, Onboarding Workflow

### Community 65 - "PAI check workflow"
Cohesion: 0.13
Nodes (15): 0. Start the server, Automated check (no Swagger), PAI check workflow, Route map (student-facing), Story 10 — I patch a vault field myself, Story 1 — I sign up and log in, Story 2 — Chat is locked until I onboard, Story 3 — I complete the starting profile (form path) (+7 more)

### Community 123 - "dependencies.py"
Cohesion: 0.22
Nodes (13): alias, _bearer, Header, HTTPAuthorizationCredentials, _constant_time_equals(), get_auth_provider(), get_current_access_token(), get_validated_access_token() (+5 more)

### Community 126 - "test_pipeline_stages.py"
Cohesion: 0.21
Nodes (16): _fake_gateway(), _live_research(), asyncio, Pipeline stage isolation tests — no LLM API calls. Each stage is tested with a…, The spec's canonical test: missing IELTS must appear as a blocking gap., Brief must never exceed _BRIEF_MAX_LINES lines — hard constraint from spec., Full pipeline with mocked LLM must produce status='ready' and a brief., Create a gateway mock that returns a fixed JSON or text. (+8 more)

### Community 127 - "PAI Counselor Conversation Tone — Problem Analysis"
Cohesion: 0.12
Nodes (14): 10. Likely fix surface (conceptual only), 11. Success criteria (product), 12. Open questions, 1. Summary, 2. What good counseling sounds like, 3. Two kinds of certainty (often confused), 5. What a real counselor does before “completion”, 7. Missing concept: goal comprehension maturity (+6 more)

### Community 128 - "DigitizationResult"
Cohesion: 0.11
Nodes (24): _docx_text(), extract_text_from_bytes(), pdf_page_texts(), _pdf_text(), Pull plain text from uploaded CV/documents. Empty string means unreadable., DigitizationResult, BaseModel, digitize_bytes() (+16 more)

### Community 129 - "drafts_from_turn"
Cohesion: 0.38
Nodes (11): drafts_from_turn(), _cand(), Memory formation: strengthen on repeat, version on change, don't dump blobs., test_conflict_does_not_share_live_semantic_key(), test_hypothetical_stays_candidate(), test_memory_key_stable_for_catalog_facts(), test_observed_negation_is_not_vault_semantic_key(), test_rank_prefers_query_match_and_skips_unrelated() (+3 more)

### Community 131 - "engine.py"
Cohesion: 0.45
Nodes (8): _as_float(), gpa_on_4(), parse_gpa(), Any, _kind(), Any, relative_delta(), values_equivalent()

### Community 132 - "17. System Behavior Rules"
Cohesion: 0.18
Nodes (11): 17. System Behavior Rules, Rule 10 — Keep intelligence supporting the counselor, Rule 1 — Never reason from the latest message alone, Rule 2 — User preference is evidence, not truth, Rule 3 — Active Goal is not a command, Rule 4 — Vault completion is continuous, Rule 5 — Never turn counseling into a questionnaire, Rule 6 — Prefer one high-value question (+3 more)

### Community 133 - "test_document_cv_extract.py"
Cohesion: 0.50
Nodes (4): _docx_with_text(), CV/document text extraction — PDF and DOCX must yield real text, not a…, test_binary_placeholder_is_gone(), test_extracts_plain_text_and_docx()

### Community 134 - "15. Component Responsibilities"
Cohesion: 0.22
Nodes (9): 15. Component Responsibilities, Goal Intelligence, Goal Resolver, Goal Service, Memory, `PAIOrchestrator`, Profile Discovery / Gap Selection, `StudentConversationAgent` (+1 more)

### Community 135 - "ground.py"
Cohesion: 0.38
Nodes (6): evidence_in_source(), _fold(), ground_candidates(), Drop LLM facts that are not grounded in the source text., test_grounding_drops_empty_evidence(), test_grounding_keeps_verbatim_and_drops_hallucination()

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
Cohesion: 0.21
Nodes (16): StudentTask, is_fact_recording_task(), list_tasks_for_person(), process_task_proposals(), AsyncSession, UUID, Planner intelligence. Proposes actions; Kernel + domains persist them., plan_next_actions() (+8 more)

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
- **135 isolated node(s):** `pai`, `1. Purpose`, `2. Core Philosophy`, `3. Target System Hierarchy`, `4.1 Understand the person` (+130 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **35 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Settings` connect `Settings` to `DigitizationResult`, `api/documents.py`, `auth.py`, `chat`, `get_session_factory`, `test_document_intelligence.py`, `documents/pipeline.py`, `counselor_graph.py`, `PersonBootstrapService`, `LLMGateway`, `ToolContext`, `orchestrator.py`, `app.py`, `LLMMessage`, `AuthError`, `postgres_store.py`, `api/chat.py`, `.redirects_match_cors`, `goals/service.py`, `student/vault/service.py`, `context.py`, `Person`, `test_pai_orchestration.py`, `SupabaseAuthProvider`, `routing.py`, `PAIOrchestrator`, `worker.py`, `jwt.py`, `delete_account`, `goals/pipeline.py`, `test_supabase_provider.py`, `get_db`, `pai/config.py`, `dependencies.py`?**
  _High betweenness centrality (0.158) - this node is a cross-community bridge._
- **Why does `Person` connect `Person` to `api/documents.py`, `auth.py`, `get_session_factory`, `documents/pipeline.py`, `PersonBootstrapService`, `orchestrator.py`, `VaultCandidate`, `api/chat.py`, `typed_apply.py`, `student/vault/service.py`, `context.py`, `Settings`, `person/models.py`, `completion.py`, `PAIOrchestrator`, `worker.py`, `delete_account`, `opening.py`, `apply_completion_to_vault`, `get_db`, `matcher.py`, `dependencies.py`?**
  _High betweenness centrality (0.062) - this node is a cross-community bridge._
- **Why does `LLMGateway` connect `LLMGateway` to `Settings`, `get_session_factory`, `documents/pipeline.py`, `counselor_graph.py`, `PAIOrchestrator`, `worker.py`, `orchestrator.py`, `app.py`, `LLMMessage`, `AuthError`, `api/chat.py`, `goals/pipeline.py`, `test_pai_orchestration.py`, `get_db`, `test_vault_intelligence.py`, `extractor.py`?**
  _High betweenness centrality (0.056) - this node is a cross-community bridge._
- **Are the 90 inferred relationships involving `Settings` (e.g. with `create_app()` and `lifespan()`) actually correct?**
  _`Settings` has 90 INFERRED edges - model-reasoned connections that need verification._
- **Are the 45 inferred relationships involving `LLMGateway` (e.g. with `lifespan()` and `FactExtractionAgent`) actually correct?**
  _`LLMGateway` has 45 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `get_settings()` (e.g. with `_database_url()` and `test_live_deepseek_structured_smoke()`) actually correct?**
  _`get_settings()` has 2 INFERRED edges - model-reasoned connections that need verification._
- **What connects `pai`, `1. Purpose`, `2. Core Philosophy` to the rest of the system?**
  _135 weakly-connected nodes found - possible documentation gaps or missing edges._