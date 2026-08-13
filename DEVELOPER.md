# Placement AI (PAI) — Developer Handoff

Short guide for engineers joining the project.

## What this repo is

A **standalone FastAPI backend** for Placement AI:

- Auth (Supabase behind `AuthProvider`)
- Person Vault + typed profile
- Chat counselor (persistent per Person)
- Vault Intelligence (chat/document extraction)
- Documents, tasks, semantic memory

```
┌─────────────┐     HTTPS      ┌──────────────────┐     HTTPS      ┌─────────────┐
│   Frontend  │ ────────────► │  PAI Backend     │ ────────────► │ Supabase    │
│  (any app)  │  /api/v1/*    │  (this repo)     │  Auth + DB    │ + DeepSeek  │
└─────────────┘               └──────────────────┘               └─────────────┘
```

## Repository layout

```text
src/pai/
  app.py                 # FastAPI app, lifespan, health
  config.py              # Settings from .env
  api/                   # HTTP routes (auth, onboarding, chat, vault, person, documents)
  orchestration/         # LangGraph turn control + counselor agent
  intelligence/          # Vault Intelligence (multi-source extraction)
  onboarding/            # Three-step post-login Person Vault setup
  vault/                 # Catalog, completion, vault service
  person/                # Person bootstrap + typed resources
  ingestion/             # Deterministic vault/typed applies
  conversations/         # Threads + messages
  memory/                # Semantic + conversation memory (AgentSpan)
  documents/             # Upload + worker
  tasks/                 # Student task proposals
  tools/                 # web_search, memory tools
  llm/                   # LLM gateway + DeepSeek
  security/              # JWT verification
  core/                  # Auth errors + AuthService
  providers/             # Supabase auth provider
  storage/               # Supabase storage
tests/
```

## Run locally

```powershell
.\.venv\Scripts\Activate.ps1
python -m alembic upgrade head
python -m uvicorn pai.app:create_app_from_env --factory --reload --host 127.0.0.1 --port 8000
```

Swagger: `http://127.0.0.1:8000/docs`

Authorize with **accessToken only** (no `Bearer` prefix in the Swagger box).

## Chat model (important)

- After first verified login, complete **3-step onboarding** before chat
- Onboarding writes into the same Person Vault (not a separate profile)
- PAI is **one counselor per Person**
- A conversation is only a **topic thread**
- `newConversation: true` = new topic, not amnesia
- Omit `conversationId` → continues latest active thread

## Key modules

| Concern | Path |
|---------|------|
| Chat entry | `pai/api/chat.py` |
| Turn graph | `pai/orchestration/graph.py` + `orchestrator.py` |
| Vault learn | `pai/intelligence/vault_intel/` |
| Counselor | `pai/orchestration/agents.py` + prompts |
| Vault writes | `pai/ingestion/vault_apply.py`, `typed_apply.py` |
| Catalog | `pai/vault/catalog.py` |

## Docker

```bash
docker build -t pai-backend .
docker run --env-file .env -p 8000:8000 pai-backend
```

## Tests

```bash
python -m pytest tests/ -q
```
