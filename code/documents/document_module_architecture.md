# Placement AI (PAI) Document Module Architecture & Engineering Guide

## 1. Executive Summary & Core Philosophy

The Document Module in **Placement AI (PAI)** is responsible for ingesting, digitizing, classifying, extracting, verifying, and reconciling student documents (academic transcripts, test scores, diplomas, passports, and resumes).

### The Golden Architecture Rules
1. **AI Never Writes Student Truth Directly**:
   * Semantic extraction proposes interpretations; deterministic gates enforce evidence, ownership, consent, and integrity.
   * AI OCR and LLMs only write to a **staging area** (`document_candidates` table with `review_status = "pending"`).
2. **Canonical Vault as Single Source of Truth**:
   * Only after the human student reviews and accepts candidates via `POST /api/v1/documents/{id}/review` do facts get written to the **Student Vault** (`vault_values` table).
3. **Evidence Backing**:
   * Every fact saved to the vault maintains an explicit evidence link in `vault_evidence` pointing back to the specific document ID, page, text span, and confidence score.
4. **Tenant Isolation**:
   * All database queries, advisory locks, and storage paths enforce strict per-student isolation (`person_id`).

---

## 2. End-to-End Execution Flow

```
[1. Client Upload]
      │  POST /api/v1/documents (file: UploadFile)
      ▼
[2. Ingestion & Storage]  ──>  Supabase Storage (private bucket: documents/{person_id}/{doc_id}/...)
      │                        DB: `documents` (status: uploaded) & `document_jobs` (status: pending)
      │                        Returns 202 Accepted immediately
      ▼
[3. Background Worker]   ──>  Claims job with PostgreSQL advisory lock:
      │                        pg_try_advisory_xact_lock(lock_ns, hashtext(document_id))
      ▼
[4. Digitization / OCR]  ──>  Try NativeDocumentProvider (pypdf/text)
      │                        If scan/photo: fallback to OpenAIVisionProvider (GPT-4o-mini OCR)
      ▼
[5. Classification]      ──>  LLM determines document type & category (e.g. academic_transcript)
      ▼
[6. Fact Extraction]     ──>  LLM extracts structured schema (GPA, degrees, scores, institutions)
      ▼
[7. Identity Match]      ──>  Compares document subject against student account (match/mismatch)
      ▼
[8. Reconciliation]      ──>  Compares extracted facts with existing vault values
      │                        Inserts proposals into `document_candidates` (status: pending)
      ▼
[9. Human-in-the-Loop]   ──>  Student reviews candidates via GET /documents/{id}/candidates
      │                        Student submits POST /documents/{id}/review
      ▼
[10. Vault Commitment]   ──>  Accepted facts written to `vault_values` + `vault_evidence`
```

---

## 3. Comprehensive File & Folder Index

### A. Interfaces & API Layer
* **`src/pai/interfaces/api/documents.py`**
  * **Role:** REST API routes for documents.
  * **Key Handlers:**
    * `upload_document()` (`POST /api/v1/documents`): Ingests uploaded file, checks token/onboarding, returns `202 Accepted`.
    * `upload_chat_document()` (`POST /api/v1/documents/chat-upload`): Uploads attachments from counseling chat.
    * `list_documents_api()` (`GET /api/v1/documents`): Lists all documents belonging to authenticated student.
    * `get_document()` (`GET /api/v1/documents/{id}`): Returns document metadata, decrypted structured extraction, and a temporary signed download URL.
    * `document_status()` (`GET /api/v1/documents/{id}/status`): Polls processing stage (`digitize`, `classify`, `extract`, `reconcile`, `ready`).
    * `document_candidates()` (`GET /api/v1/documents/{id}/candidates`): Lists staging proposals.
    * `review_document()` (`POST /api/v1/documents/{id}/review`): Accepts or rejects candidates into the Vault.
    * `delete_document_api()` (`DELETE /api/v1/documents/{id}`): Soft-deletes document and deletes files from Supabase Storage.
    * `reprocess_document()` (`POST /api/v1/documents/{id}/reprocess`): Re-enqueues processing.
    * `verification_cases_api()` (`GET /api/v1/documents/verification-cases`): Lists open conflict/identity cases.
    * `resolve_verification_case_api()` (`POST /api/v1/documents/verification-cases/{id}/resolve`): Resolves cases.

* **`src/pai/interfaces/workers/documents.py`**
  * **Role:** CLI worker process entrypoint (`py run.py --service documents`).
  * **Exports:** `document_worker_loop()`, `run_document_worker_once()`.

---

### B. Domain Models & Service Layer
* **`src/pai/domains/documents/models.py`**
  * **Role:** Database entities.
  * **Entities:**
    * `Document`: Core record (`id`, `person_id`, `document_type`, `category`, `status`, `storage_path`, `identity_status`, `verification_status`).
    * `DocumentVersion`: Tracks document revisions, SHA256 hashes, digitized text, and encrypted JSON payloads.
    * `DocumentJob`: Asynchronous worker queue item (`status`, `attempts`, `idempotency_key`, `locked_at`, `current_stage`).
    * `DocumentCandidate`: **Staging table** for extracted facts awaiting review (`field_key`, `value`, `confidence`, `evidence_text`, `review_status`).
    * `DocumentAnalysisRun`: Detailed telemetry and stage completion audit for each pipeline run.
    * `DocumentParty`: Extracted entities (student, issuing institution).
    * `DocumentRelation`: Links documents to chat messages, goals, or applications.
    * `MessageDocument`: Links documents attached to specific chat messages.

* **`src/pai/domains/documents/service.py`**
  * **Role:** Domain business operations.
  * **Functions:**
    * `review_document_candidates()`: Validates candidate ownership, handles rejections, decrypts sensitive values, converts accepted rows to `VaultCandidate` objects, and updates document status to `processed` or `awaiting_review`.
    * `list_document_candidates()`: Returns decrypted staging proposals along with current Vault values for comparison.
    * `list_documents()` / `get_document_owned()`: Tenant-isolated retrieval.
    * `mark_document_deleted()`: Soft-deletes document record.
    * `enqueue_reprocess()`: Resets job to `pending` for re-analysis.

* **`src/pai/domains/documents/text.py`**
  * **Role:** Raw byte text extraction.
  * **Functions:** `pdf_page_texts(data)` (extracts text per page using pypdf), `extract_text_from_bytes(data, mime, filename)`.

---

### C. Intelligence Layer (The Extraction & Processing Engine)
Location: `src/pai/intelligences/documents/`

#### 1. Ingestion & Pipeline Orchestration
* **`ingest.py`**
  * Invoked immediately upon HTTP POST upload.
  * Runs security validations (`validate_upload_bytes`), scan hook (`scan_bytes`), and initial taxonomy classification (`classify_document`).
  * Stores raw file bytes to Supabase Storage at `{person.id}/{doc.id}/{version.id}/original`.
  * Creates `Document`, `DocumentVersion`, and `DocumentJob` with `status="pending"`.
* **`pipeline.py`**
  * **The core orchestrator (`run_document_analysis`).** Executes the sequential stages:
    1. `_digitize()`: Extracts text or triggers vision OCR.
    2. `classify_content()`: Refines document classification via LLM.
    3. `extract_candidates()`: Structured fact extraction using Pydantic schemas.
    4. `match_student()`: Validates document subject against student identity.
    5. `reconcile()`: Reconciles extracted facts against existing Vault beliefs.
    6. Writes proposals into `DocumentCandidate` table and opens verification cases for discrepancies.
* **`config.py`**
  * Loads `data/policy.json` (pipeline versions, stages, confidence thresholds) and `data/taxonomy.json` (document types, allowed MIME types).

#### 2. Digitization & OCR Providers
* **`digitization/service.py` (`digitize_bytes`)**
  * Attempts `NativeDocumentProvider` first. If character count < `min_text_chars` and document is an image or scanned PDF, routes to the configured OCR provider.
* **`digitization/schemas.py`**
  * `DigitizationResult`: Data model containing extracted text, quality assessment (`good`/`unreadable`), page breakdown, and confidence.
* **`providers/native.py` (`NativeDocumentProvider`)**
  * Fast, free, native digital text parser for PDF, DOCX, and plain text.
* **`providers/openai_vision.py` (`OpenAIVisionProvider`)**
  * Uses `gpt-4o-mini` vision to perform high-accuracy OCR on images, scans, and photos.
* **`providers/factory.py` (`ocr_provider`)**
  * Provider factory selecting OCR implementation based on settings.

#### 3. Classification & Taxonomies
* **`classification/classifier.py`**
  * Uses LLM to classify document into category (`academic`, `identity`, `financial`, `employment`) and document type (`transcript`, `passport`, `diploma`, etc.).
* **`classification/taxonomy.py`**
  * Evaluates whether a document type is evidence-eligible (eligible to write to Vault) or purely informational.

#### 4. Structured Extraction & Schemas
* **`extraction/extractor.py` (`extract_candidates`)**
  * Executes structured LLM generation with schema enforcement. Sensitive values (passport numbers, personal identifiers) are tagged for Fernet encryption.
* **`extraction/schemas/`**
  * `transcript.py`: `TranscriptExtraction` (institution, degree, cumulative GPA, GPA scale, courses, graduation year).
  * `passport.py`: `PassportExtraction` (passport number, nationality, date of birth, expiration date).
  * `degree.py`: `DegreeExtraction` (degree title, field of study, completion date).
  * `test_score.py`: `TestScoreExtraction` (test type: IELTS/TOEFL/GRE/GMAT, total score, sub-band scores).
  * `resume.py`: `ResumeExtraction` (experience, education, skills).
  * `common.py`: Shared base extraction models.

#### 5. Identity Verification & Normalization
* **`identity/matcher.py` (`match_student`)**
  * Compares extracted document name and date of birth with the logged-in student profile.
  * Outputs: `matched`, `mismatch`, or `unconfirmed`.
* **`identity/names.py`**
  * Name normalization, handle aliases, nickname expansion, and cultural name reordering.
* **`identity/parties.py`**
  * Identifies the issuing authority (e.g. Stanford University) and student roles.
* **`normalization/`**
  * `gpa.py`: Converts varied grading systems (e.g. 85/100, 3.8/4.0, First Class) into standardized representations.
  * `dates.py`: Parses arbitrary date formats into standard ISO-8601 strings.
  * `institutions.py`: Normalizes university names against global registries.
  * `countries.py`: Standardizes country names into ISO codes.

#### 6. Reconciliation & Verification
* **`reconciliation/engine.py` (`reconcile`)**
  * Compares extracted candidate facts against current Vault belief:
    * `ACCEPT_NEW`: New fact discovered; proposed for acceptance.
    * `CONFIRM_EXISTING`: Fact matches current belief; reinforces confidence.
    * `PROPOSE_UPDATE`: Fact updates an existing value; opens confirmation.
    * `CRITICAL_CONFLICT`: Fact fundamentally conflicts; opens a verification case.
* **`reconciliation/comparators.py`**
  * Field-specific equality comparators.
* **`verification/service.py`**
  * Opens and manages `verification_cases` when manual resolution is needed.

#### 7. Security, Workers & Telemetry
* **`security/validation.py` (`validate_upload_bytes`)**
  * Validates file size limits (`DOCUMENT_MAX_BYTES`), allowed extensions, and magic byte signatures.
* **`security/scanner.py` (`scan_bytes`)**
  * Antivirus / malware inspection boundary.
* **`workers/analysis_worker.py`**
  * Implements `claim_next_job()` with PostgreSQL row-level advisory lock (`FOR UPDATE SKIP LOCKED`).
  * Enforces job timeout (540s), retry backoff, and lease renewals.
* **`telemetry/tracing.py`**
  * OpenTelemetry tracing spans (`span("document.analysis")`).

---

### D. Workflow & Storage Providers
* **`src/pai/workflows/document_ingestion/runner.py`**
  * Invoked by worker; binds `run_document_analysis` with domain `VaultReader` and `VaultWriter`.
* **`src/pai/platform/storage/supabase.py` (`SupabaseStorageProvider`)**
  * Client for Supabase Storage. Handles `upload_private`, `download_bytes`, `create_signed_download_url`, and `delete_object`.
* **`src/pai/kernel/evidence/vault_apply.py` (`process_candidates`, `apply_vault_candidate`)**
  * **The Gatekeeper to the Vault.** When the student approves candidates:
    1. Writes to `vault_values` table (`status="active"`, `verification_level="verified"`).
    2. Writes evidence to `vault_evidence` table linking `document_id`, snippet, and confidence.
    3. Writes audit trail to `vault_history` table.
    4. Recomputes profile completion.

---

## 4. Complete Database Tables Overview

| Table Name | Description | Key Columns |
| :--- | :--- | :--- |
| **`documents`** | Root document metadata record | `id`, `person_id`, `title`, `document_type`, `status`, `storage_path`, `identity_status` |
| **`document_versions`** | Revision history for each document file | `id`, `document_id`, `version_number`, `sha256`, `content_text`, `structured_extraction` |
| **`document_jobs`** | Background worker queue | `id`, `document_id`, `status`, `attempts`, `locked_at`, `current_stage`, `last_error` |
| **`document_candidates`** | **Staging Area** (AI extraction proposals) | `id`, `document_id`, `field_key`, `value`, `confidence`, `evidence_text`, `review_status` |
| **`document_analysis_runs`**| Audit record of pipeline execution | `id`, `document_id`, `current_stage`, `completed_stages`, `ocr_provider`, `ocr_model` |
| **`document_parties`** | Extracted people & entities | `id`, `document_id`, `role`, `name_raw`, `organization_name` |
| **`verification_cases`** | Open conflict/identity cases | `id`, `person_id`, `document_id`, `field_key`, `case_type`, `severity`, `status` |
| **`vault_values`** | **The Canonical Student Vault** (Active Truth) | `id`, `vault_id`, `field_key`, `value`, `status`, `verification_level`, `confidence` |
| **`vault_evidence`** | Audit link between vault fact & document | `id`, `vault_value_id`, `source_type`, `source_reference`, `evidence_text`, `confidence` |
| **`vault_history`** | Immutable changelog of vault edits | `id`, `vault_id`, `field_key`, `action`, `old_value`, `new_value`, `actor_id` |

---

## 5. Swagger REST API Reference

| Endpoint | Method | Purpose | Response |
| :--- | :---: | :--- | :---: |
| `/api/v1/documents` | `POST` | Upload new document file | `202 Accepted` |
| `/api/v1/documents/chat-upload` | `POST` | Upload document from counseling chat | `202 Accepted` |
| `/api/v1/documents` | `GET` | List all documents for student | `200 OK` |
| `/api/v1/documents/taxonomy` | `GET` | Get categories, types, allowed mimes | `200 OK` |
| `/api/v1/documents/{id}` | `GET` | Get details, extraction & signed URL | `200 OK` |
| `/api/v1/documents/{id}/status` | `GET` | Poll worker processing status | `200 OK` |
| `/api/v1/documents/{id}/candidates` | `GET` | **View AI proposals in staging area** | `200 OK` |
| `/api/v1/documents/{id}/review` | `POST` | **Accept/Reject proposals into Vault** | `200 OK` |
| `/api/v1/documents/{id}/reprocess` | `POST` | Re-queue document for re-analysis | `200 OK` |
| `/api/v1/documents/{id}` | `DELETE` | Delete document and stored files | `200 OK` |
| `/api/v1/documents/verification-cases` | `GET` | List open verification conflicts | `200 OK` |
| `/api/v1/documents/verification-cases/{id}/resolve` | `POST` | Manually resolve conflict | `200 OK` |
