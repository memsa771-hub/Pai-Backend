# Graph Report - Pai-Backend  (2026-08-27)

## Corpus Check
- 250 files · ~82,127 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1957 nodes · 6000 edges · 126 communities (92 shown, 34 thin omitted)
- Extraction: 93% EXTRACTED · 7% INFERRED · 0% AMBIGUOUS · INFERRED: 408 edges (avg confidence: 0.92)
- Token cost: 14,064 input · 2,038 output

## Community Hubs (Navigation)
- Document Relations
- Auth Dependencies
- Goal Job Search
- Conversation Service
- Person Bootstrap
- Document Policy
- Document Models
- Counselor Agents
- App Lifespan
- Vault LLM Extractor
- App Settings
- Goal Creation
- Memory Tools
- LLM Providers
- Document Workers
- Document Classifier
- Memory Drafts
- Goal Resolution
- Domain Errors
- Memory Store
- Counselor Models
- Education Apply
- Goal Service
- Vault Security
- Counselor Context
- Onboarding Service
- Fact Agents
- Geo Countries
- Evidence Grounding
- Auth API Tests
- Vault Catalog
- Degree Extractor
- Onboarding API
- Memory Formation
- Supabase Auth
- Vocab Enums
- Profile Snapshot
- Auth Provider Fake
- Vault Completion
- Student Tasks
- Counselor PAIOrchestrator
- Tests 41
- Auth AuthProvider
- API GoalIntelligence
- Auth
- Onboarding OnboardingSkillItem
- Tests FakeQueue
- Tests 47
- GroundedLifeAim ResolverResult
- Platform DeclarativeBase
- Counselor
- Tests parametrize
- Tests 52
- Tests 53
- Person Vault Person
- Tests 55
- Tests asyncio 56
- Tests asyncio 57
- Kernel CandidateResult
- Counselor CounselorContext
- Tests Environment
- Memory PersonMemoryService
- API field_validator
- Memory ConversationMemory
- src_pai_domains_goals src_pai_domains_st
- Counselor StateGraph
- Generic executable actions
- Student actions tasks
- Documents
- Goal records and
- Persistent truth owned
- Append only person
- Student persistent truth
- Deterministic student data
- Person Vault 86
- Person Vault 87
- Placement PAI backend
- External providers Tavily
- Counselor 90
- Documents 91
- Goal Intelligence assessment
- Reasoning layers Must
- Person Vault 95
- API
- Kernel
- Kernel 98
- Kernel 99
- Kernel 100
- Platform
- Platform 102
- LLM Platform
- Platform 104
- Platform 105
- Cross domain process
- Tests 107
- Goal Intelligence Pipeline
- Person Vault 109
- pai
- src_pai_platform_auth

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
- `test_counselor_profile_surfaces_critical_verification()` --uses--> `CounselorContext`  [INFERRED]
  tests/test_document_intelligence.py → src/pai/intelligences/counselor/context.py
- `test_counselor_json_preamble_does_not_leak_into_reply()` --calls--> `_result_from_text()`  [INFERRED]
  tests/test_pai_orchestration.py → src/pai/intelligences/counselor/counselor_graph.py
- `test_tool_loop_reuses_plain_reply_without_second_llm()` --calls--> `_result_from_text()`  [INFERRED]
  tests/test_pai_orchestration.py → src/pai/intelligences/counselor/counselor_graph.py
- `test_submit_schema_accepts_country_name_alias()` --uses--> `OnboardingSubmit`  [INFERRED]
  tests/test_onboarding.py → src/pai/workflows/onboarding/contracts.py
- `test_submit_schema_high_school_does_not_need_degree()` --uses--> `OnboardingSubmit`  [INFERRED]
  tests/test_onboarding.py → src/pai/workflows/onboarding/contracts.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Student Intelligence Loop** — src_pai_intelligences_vault, src_pai_domains_student, src_pai_intelligences_goals, src_pai_intelligences_counselor [EXTRACTED 0.90]

## Communities (126 total, 34 thin omitted)

### Community 0 - "Document Relations"
Cohesion: 0.06
Nodes (90): DocumentRelation, MessageDocument, Chat references a Document Vault item. The file is not stored on the message., Polymorphic links: chat, goal, application, verification, lineage., add_relation(), AsyncSession, UUID, attach_documents_to_message() (+82 more)

### Community 1 - "Auth Dependencies"
Cohesion: 0.06
Nodes (72): alias, _bearer, Header, HTTPAuthorizationCredentials, get_settings(), get_person_by_auth(), Mark person deleted and purge vault values before auth deletion., soft_delete_person_data() (+64 more)

### Community 2 - "Goal Job Search"
Cohesion: 0.05
Nodes (69): Generic search action., Any, Generic search action. Provider-specific work lives in integrations., search(), GoalJob, Durable goal intelligence job. Same poll-loop pattern as PersonJob., Any, Tavily web search adapter. Callers go through capabilities.search. (+61 more)

### Community 3 - "Conversation Service"
Cohesion: 0.07
Nodes (58): Conversation, begin_chat_turn(), ConversationNotFoundError, count_person_messages(), create_conversation(), get_conversation_owned(), get_latest_active_conversation(), get_or_create_person_conversation() (+50 more)

### Community 4 - "Person Bootstrap"
Cohesion: 0.08
Nodes (40): normalize_email(), PersonBootstrapService, Any, AsyncSession, UUID, Create the Person Vault on first verified auth; skip heavy work on later logins., process_candidates(), AsyncSession (+32 more)

### Community 5 - "Document Policy"
Cohesion: 0.09
Nodes (40): evidence_eligible(), policy(), Any, Load Document Intelligence taxonomy and policy from package data (not code)., _read(), field_criticality(), field_sensitivity(), rank() (+32 more)

### Community 6 - "Document Models"
Cohesion: 0.09
Nodes (43): Document, DocumentAnalysisRun, DocumentCandidate, DocumentFact, DocumentParty, DocumentVersion, Immutable processing attempt. Never overwrite a completed run., Normalized evidence. Not Person Vault truth. (+35 more)

### Community 7 - "Counselor Agents"
Cohesion: 0.09
Nodes (37): counselor_seed_messages(), _dict_to_llm_message(), _first_json_object(), iter_counselor_tokens(), _normalize_tool_call(), _parse_conversation_json(), public_reply(), Any (+29 more)

### Community 8 - "App Lifespan"
Cohesion: 0.07
Nodes (38): BaseCheckpointSaver, create_app(), create_app_from_env(), lifespan(), FastAPI, close_graph_checkpointer(), get_graph_checkpointer(), init_graph_checkpointer() (+30 more)

### Community 9 - "Vault LLM Extractor"
Cohesion: 0.14
Nodes (24): OmnibusLLMExtractor, Single strong multi-domain LLM pass (AgentSpan-style specialist, one call)., _schema_source(), _task_for(), normalize_candidates(), Vault Intelligence — multi-source, multi-domain Person understanding.…, PAI's strong profile-learning brain. Does not write Vault itself., VaultIntelligenceService (+16 more)

### Community 10 - "App Settings"
Cohesion: 0.10
Nodes (24): BaseSettings, field_validator, model_validator, Self, Settings, DigitizationResult, BaseModel, digitize_bytes() (+16 more)

### Community 11 - "Goal Creation"
Cohesion: 0.09
Nodes (40): _anchor_match_score(), _assert_no_vault_keys(), create_goal(), goal_fact_lines(), _has_hard_conflict(), _norm(), True only when a stable anchor is present on both sides and disagrees. Missing…, Create a brand-new goal record. Caller commits. (+32 more)

### Community 12 - "Memory Tools"
Cohesion: 0.12
Nodes (23): Any, Stores non-vault insights. Does NOT mutate Person Vault., RecallSemanticMemoryTool, RememberInsightTool, build_default_registry(), build_turn_registry(), Any, Deterministic per-turn tool set — avoid handing every tool to every request. (+15 more)

### Community 13 - "LLM Providers"
Cohesion: 0.08
Nodes (16): BaseModel, LLMProvider, BaseModel, Protocol, DeepSeekProvider, LLMProviderError, BaseModel, LLMRequest (+8 more)

### Community 14 - "Document Workers"
Cohesion: 0.11
Nodes (32): DocumentJob, run_intelligence_followup(), claim_next_job(), document_worker_loop(), process_document_job(), AsyncSession, Event, Document intelligence worker: claim jobs, run analysis, persist via the domain. (+24 more)

### Community 15 - "Document Classifier"
Cohesion: 0.12
Nodes (29): classify_document(), _best_type(), _best_type_on_filename(), classify_from_name(), default_type(), _filename_tokens(), _generated_types(), known_types() (+21 more)

### Community 16 - "Memory Drafts"
Cohesion: 0.12
Nodes (28): _belongs_to(), _content_for(), _draft_from_candidate(), importance_of(), memory_key_for(), _observed_status(), _slug(), _cand() (+20 more)

### Community 17 - "Goal Resolution"
Cohesion: 0.10
Nodes (31): _extract_anchors_from_intent(), _has_hard_conflict_on_goal(), Any, Normalize anchors from intent. Countries via student geo, not a handwritten…, Decide what to do with the goal signal from this turn. Called synchronously…, resolve(), GoalExtract, Living brief in the student's words — language-agnostic, not an enum. (+23 more)

### Community 18 - "Domain Errors"
Cohesion: 0.13
Nodes (12): Exception, AuthError, CsrfError, EmailAlreadyInUseError, EmailNotVerifiedError, ForbiddenError, IncorrectPasswordError, InvalidCredentialsError (+4 more)

### Community 19 - "Memory Store"
Cohesion: 0.11
Nodes (16): MemoryEntry, MemoryStore, format_for_recall(), record_from_row(), Persisted memory scoped to a person. Unstructured notes (AgentSpan remember())…, SemanticMemoryRow, AsyncPostgresMemoryStore, InProcessMemoryStore (+8 more)

### Community 20 - "Counselor Models"
Cohesion: 0.16
Nodes (19): One counselor transcript per person., Message, OrchestrationRun, save_assistant_message(), handle_user_message(), _payload_from_state(), AsyncSession, UUID (+11 more)

### Community 21 - "Education Apply"
Cohesion: 0.20
Nodes (27): Education, _apply_education_fields(), _apply_education_one(), apply_typed_candidate(), _as_items(), _education_payload(), _education_snapshot(), _find_education_match() (+19 more)

### Community 22 - "Goal Service"
Cohesion: 0.17
Nodes (27): Goal, Canonical goal identity record — one row per distinct pursuit., activate_goal(), enqueue_goal_intelligence_job(), find_matching_goal(), get_active_goal(), get_conversation_active_goal(), get_goal_by_id() (+19 more)

### Community 23 - "Vault Security"
Cohesion: 0.15
Nodes (9): mask_value(), Any, Fernet-based encoding for sensitive vault payloads (no custom crypto)., SensitiveValueCodec, Any, AsyncSession, UUID, Active vault_value map only — no completion scan or typed counts. (+1 more)

### Community 24 - "Counselor Context"
Cohesion: 0.16
Nodes (27): _advice_gaps(), build_chat_starters(), build_counselor_context(), build_known_facts(), build_person_context_pack(), build_student_context_pack(), chat_stay_payload(), _dedupe_goal_lines() (+19 more)

### Community 25 - "Onboarding Service"
Cohesion: 0.20
Nodes (9): OnboardingSubmit, Starting profile. Categorical fields are closed enums; GET /onboarding returns…, OnboardingService, _present(), Any, AsyncSession, Map the starting profile into the Vault and mark onboarding complete.…, Extract CV facts into the vault and mark onboarding complete. (+1 more)

### Community 26 - "Fact Agents"
Cohesion: 0.13
Nodes (19): FactExtractionAgent, Compatibility facade over VaultIntelligenceService (chat + document)., Only user-facing agent (PAI Student Counselor) with LangGraph tool loop., StudentConversationAgent, FactExtractionResult, Any, SchemaRoutingMockProvider, test_agents_do_not_call_each_other() (+11 more)

### Community 27 - "Geo Countries"
Cohesion: 0.12
Nodes (18): coerce_country(), country_codes_from_value(), _country_names(), extract_countries_from_text(), ISO 3166-1 countries via pycountry — not a handwritten country table., High-recall ISO alpha-2 codes mentioned in free text (names, not 2-letter…, Normalize to ISO 3166-1 alpha-2 (code, alpha-3, English name, or common exonym)., Pull ISO alpha-2 codes from a string, list, or already-normalized code. (+10 more)

### Community 28 - "Evidence Grounding"
Cohesion: 0.11
Nodes (22): _normalize_stream(), Return (candidates, hit labels). High precision only., run_deterministic_boosters(), evidence_in_source(), _fold(), ground_candidates(), Drop LLM facts that are not grounded in the source text., merge_candidates() (+14 more)

### Community 29 - "Auth API Tests"
Cohesion: 0.11
Nodes (10): _signup_body(), test_resend_verification(), test_session_from_verification_tokens(), test_session_rejects_unverified_tokens(), test_signup_does_not_require_phone(), test_signup_duplicate_email(), test_signup_flow(), test_signup_invalid_email() (+2 more)

### Community 30 - "Vault Catalog"
Cohesion: 0.22
Nodes (16): VaultEvidence, VaultHistory, VaultValue, get_catalog_field(), Person Vault field registry (C / I / E priorities)., _history_value(), Write many vault_value fields in one select + one flush, then evidence rows., ConsentRequiredError (+8 more)

### Community 31 - "Degree Extractor"
Cohesion: 0.11
Nodes (17): extract_candidates(), _try_typed(), DegreeExtraction, BaseModel, to_field_map(), PassportExtraction, BaseModel, to_field_map() (+9 more)

### Community 32 - "Onboarding API"
Cohesion: 0.15
Nodes (14): get_onboarding(), AsyncSession, Depends, get, JSONResponse, post, Request, UploadFile (+6 more)

### Community 33 - "Memory Formation"
Cohesion: 0.20
Nodes (22): Action, apply_draft(), apply_memory_drafts(), _formation_blob(), _jaccard(), _link_turn(), MemoryDraft, MemoryRecord (+14 more)

### Community 34 - "Supabase Auth"
Cohesion: 0.20
Nodes (3): Any, AsyncClient, SupabaseAuthProvider

### Community 35 - "Vocab Enums"
Cohesion: 0.27
Nodes (19): country_options(), BudgetBand, CurrentStatus, EducationLevel, EmploymentType, FieldOfStudy, Gender, IntakeSeason (+11 more)

### Community 36 - "Profile Snapshot"
Cohesion: 0.21
Nodes (18): Certification, PersonConsent, Project, Skill, WorkExperience, _cert_dict(), _edu_dict(), _goal_dict() (+10 more)

### Community 37 - "Auth Provider Fake"
Cohesion: 0.16
Nodes (4): InvalidTokenError, UserNotFoundError, ProviderSession, FakeAuthProvider

### Community 38 - "Vault Completion"
Cohesion: 0.22
Nodes (20): Priority, PersonVault, CatalogField, _fields(), build_vault_status(), compute_completion(), compute_completion_from_snapshot(), field_is_present_in_snapshot() (+12 more)

### Community 39 - "Student Tasks"
Cohesion: 0.20
Nodes (16): StudentTask, is_fact_recording_task(), list_tasks_for_person(), process_task_proposals(), AsyncSession, UUID, Planner intelligence. Proposes actions; Kernel + domains persist them., plan_next_actions() (+8 more)

### Community 40 - "Counselor PAIOrchestrator"
Cohesion: 0.22
Nodes (7): _counselor_web_note(), PAIOrchestrator, Counselor reply only. Extraction/Vault run after the user has the text., Vault/memory/tasks after the student already has the reply., Counselor coordinator. Does not own Vault/Goals/Documents writes., PAIState, TypedDict

### Community 41 - "Tests 41"
Cohesion: 0.10
Nodes (10): test_enum_catalog_exposes_dropdown_ids(), test_submit_schema_accepts_country_name_alias(), test_submit_schema_high_school_does_not_need_degree(), test_submit_schema_minimal_criticals_are_enough(), test_submit_schema_normalizes_phone_to_e164(), test_submit_schema_optional_fields_can_be_omitted(), test_submit_schema_rejects_unknown_country(), test_submit_schema_rejects_vague_primary_goal() (+2 more)

### Community 42 - "Auth AuthProvider"
Cohesion: 0.17
Nodes (5): Auth domain: signup/login, JWT, Supabase provider., AuthProvider, GenericActionResult, Protocol, SignupResult

### Community 43 - "API GoalIntelligence"
Cohesion: 0.28
Nodes (16): GoalIntelligence, Background-computed intelligence summary for one goal. One row per goal., get_goal_intelligence(), activate_goal_endpoint(), get_active_goal_endpoint(), get_goal_detail(), list_student_goals(), Any (+8 more)

### Community 44 - "Auth"
Cohesion: 0.21
Nodes (15): _fetch_jwks(), _jwks_url(), _key_for_token(), Any, Response, Access-token verification for Supabase (HS256 legacy + ES256/RS256 JWKS)., Network verification fallback for asymmetric JWTs., Verify Supabase user JWT (HS256 secret or ES256/RS256 via JWKS). (+7 more)

### Community 45 - "Onboarding OnboardingSkillItem"
Cohesion: 0.16
Nodes (9): _blank_to_none(), _linkedin_url(), OnboardingSkillItem, OnboardingTestScoreItem, OnboardingWorkItem, BaseModel, date, field_validator (+1 more)

### Community 46 - "Tests FakeQueue"
Cohesion: 0.14
Nodes (13): fake_queue(), FakeQueue, _make_fake_goal(), asyncio, fixture, Tests that chat reply path is never blocked by the goal intelligence pipeline.…, CounselorContext.profile_block() must work when active_goal_brief is None., Records enqueue calls but never executes jobs. (+5 more)

### Community 48 - "GroundedLifeAim ResolverResult"
Cohesion: 0.17
Nodes (14): _fold(), _goal_name_tokens(), GroundedLifeAim, _maybe_enqueue(), AsyncSession, UUID, Goal resolver — cheap, synchronous, no extra LLM call on the chat path.…, Tokens that identify this goal for containment matching. (+6 more)

### Community 49 - "Platform DeclarativeBase"
Cohesion: 0.29
Nodes (7): _database_url(), run_migrations_offline(), run_migrations_online(), DeclarativeBase, Goal, GoalIntelligence, and GoalJob. Tables unchanged (goals,…, PersonDecision, Base

### Community 50 - "Counselor"
Cohesion: 0.14
Nodes (11): AsyncSession, UUID, classify_turn(), _has_profile_signal(), Cheap turn kind. Not a second LLM call., Extract statements. Skip greetings, acknowledgements, and advice-only questions., should_extract_facts(), test_classify_turn_kinds() (+3 more)

### Community 51 - "Tests parametrize"
Cohesion: 0.21
Nodes (11): parametrize, GoalType, GoalWriteAction, StrEnum, Canonical goal vocabulary. Intelligence classifies; this module validates., _classify_goal_type(), Prefer LLM GoalExtract.goal_type; tiny keyword fallback only., Verify that goal_type matches expected for 'create' cases. (+3 more)

### Community 52 - "Tests 52"
Cohesion: 0.23
Nodes (11): _docx_text(), extract_text_from_bytes(), pdf_page_texts(), _pdf_text(), Pull plain text from uploaded CV/documents. Empty string means unreadable., _docx_with_text(), CV/document text extraction — PDF and DOCX must yield real text, not a…, test_binary_placeholder_is_gone() (+3 more)

### Community 53 - "Tests 53"
Cohesion: 0.33
Nodes (12): drafts_from_turn(), _kind_for(), _cand(), Memory formation: strengthen on repeat, version on change, don't dump blobs., test_conflict_does_not_share_live_semantic_key(), test_hypothetical_stays_candidate(), test_memory_key_stable_for_catalog_facts(), test_observed_negation_is_not_vault_semantic_key() (+4 more)

### Community 54 - "Person Vault Person"
Cohesion: 0.45
Nodes (11): Person, update_person_profile(), create_resource(), delete_resource(), list_resources(), Any, AsyncSession, UUID (+3 more)

### Community 55 - "Tests 55"
Cohesion: 0.38
Nodes (11): grounded_life_aim(), LLM classified life_aim only if evidence is a span of the student text., _extract(), test_english_life_aim_is_stored(), test_exploring_and_pivot_come_from_the_classifier(), test_mixed_aim_and_attach_keeps_only_the_aim(), test_model_cannot_invent_a_goal_not_in_the_message(), test_questions_and_greetings_are_not_goals() (+3 more)

### Community 56 - "Tests asyncio 56"
Cohesion: 0.23
Nodes (11): _mock_goal(), asyncio, Selective Vault→Goals refresh tests. Verifies that when a Vault field changes:…, Spot-check that key Vault fields are in the map., Updating application.test_scores must stale + enqueue admission goals., Updating a field not in VAULT_FIELDS_THAT_AFFECT_GOALS must not touch any goal., Create two goals (admission + job). Update IELTS (test_scores). Only admission…, test_test_score_update_marks_admission_stale() (+3 more)

### Community 57 - "Tests asyncio 57"
Cohesion: 0.26
Nodes (11): asyncio, fixture, _settings_kwargs(), supabase_settings(), test_redirect_origin_must_be_in_cors(), test_redirect_url_cannot_be_site_root(), test_supabase_login_incorrect_password(), test_supabase_login_unknown_email() (+3 more)

### Community 58 - "Kernel CandidateResult"
Cohesion: 0.42
Nodes (10): CandidateResult, evaluate_candidate(), evaluate_candidate_with_context(), evaluate_candidates_batch(), load_candidate_validation_context(), _normalize(), Any, AsyncSession (+2 more)

### Community 59 - "Counselor CounselorContext"
Cohesion: 0.20
Nodes (7): context_pack_to_json(), CounselorContext, BaseModel, Compact counselor prompt + stay payload. Not the full Person dump., StudentContextPack, When active_goal_brief is present, it replaces the legacy goal line., test_counselor_context_injects_brief_when_ready()

### Community 60 - "Tests Environment"
Cohesion: 0.29
Nodes (8): Environment, extraction_catalog_hint(), Compact writable field list for the fact-extraction LLM (exact keys only)., _render(), test_omnibus_cv_prompt_asks_for_full_resume(), test_prompt_render_student_conversation(), test_extraction_catalog_lists_admissions_keys(), test_omnibus_prompt_is_recall_first_not_summarize()

### Community 61 - "Memory PersonMemoryService"
Cohesion: 0.25
Nodes (3): Long-term semantic + session conversation memory (AgentSpan-backed)., PersonMemoryService, Facade: conversation window + formed long-term memory per student. Agents may…

### Community 62 - "API field_validator"
Cohesion: 0.25
Nodes (5): normalize_phone(), Phone numbers via Google libphonenumber; stored as E.164., field_validator, model_validator, test_normalize_phone_e164()

### Community 63 - "Memory ConversationMemory"
Cohesion: 0.29
Nodes (5): ConversationMemory, SemanticMemory, async_sessionmaker, AsyncSession, UUID

### Community 64 - "src_pai_domains_goals src_pai_domains_st"
Cohesion: 0.29
Nodes (7): Goals Domain, Student Domain, Counselor Intelligence, Goal Intelligence, Vault Intelligence, Kernel Write Gates, Onboarding Workflow

### Community 65 - "Counselor StateGraph"
Cohesion: 0.50
Nodes (3): build_pai_graph(), StateGraph, test_chat_graph_replies_without_waiting_on_extract_chain()

## Knowledge Gaps
- **3 isolated node(s):** `pai`, `Person Vault`, `Goal Intelligence Pipeline`
  These have ≤1 connection - possible missing edges or undocumented components.
- **34 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Settings` connect `App Settings` to `Document Relations`, `Auth Dependencies`, `Goal Job Search`, `Conversation Service`, `Person Bootstrap`, `Document Models`, `Counselor Agents`, `App Lifespan`, `Vault LLM Extractor`, `Memory Tools`, `LLM Providers`, `Document Workers`, `Document Classifier`, `Domain Errors`, `Counselor Models`, `Vault Security`, `Counselor Context`, `Onboarding Service`, `Fact Agents`, `Vault Catalog`, `Onboarding API`, `Supabase Auth`, `Profile Snapshot`, `Counselor PAIOrchestrator`, `API GoalIntelligence`, `Auth`, `Tests asyncio 57`, `Memory PersonMemoryService`, `Memory ConversationMemory`?**
  _High betweenness centrality (0.189) - this node is a cross-community bridge._
- **Why does `Person` connect `Person Vault Person` to `Document Relations`, `Auth Dependencies`, `Goal Job Search`, `Conversation Service`, `Person Bootstrap`, `Document Policy`, `Document Models`, `Document Classifier`, `Counselor Models`, `Education Apply`, `Vault Security`, `Counselor Context`, `Onboarding Service`, `Vault Catalog`, `Onboarding API`, `Profile Snapshot`, `Vault Completion`, `Student Tasks`, `Platform DeclarativeBase`, `Counselor`, `Kernel CandidateResult`?**
  _High betweenness centrality (0.075) - this node is a cross-community bridge._
- **Why does `LLMGateway` connect `Vault LLM Extractor` to `Onboarding API`, `Goal Job Search`, `Document Models`, `Counselor Agents`, `App Lifespan`, `Counselor PAIOrchestrator`, `App Settings`, `Memory Tools`, `LLM Providers`, `Document Workers`, `Domain Errors`, `Counselor Models`, `Fact Agents`, `Degree Extractor`?**
  _High betweenness centrality (0.069) - this node is a cross-community bridge._
- **Are the 90 inferred relationships involving `Settings` (e.g. with `create_app()` and `lifespan()`) actually correct?**
  _`Settings` has 90 INFERRED edges - model-reasoned connections that need verification._
- **Are the 45 inferred relationships involving `LLMGateway` (e.g. with `lifespan()` and `FactExtractionAgent`) actually correct?**
  _`LLMGateway` has 45 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `get_settings()` (e.g. with `_database_url()` and `test_live_deepseek_structured_smoke()`) actually correct?**
  _`get_settings()` has 2 INFERRED edges - model-reasoned connections that need verification._
- **What connects `pai`, `Person Vault`, `Goal Intelligence Pipeline` to the rest of the system?**
  _3 weakly-connected nodes found - possible documentation gaps or missing edges._