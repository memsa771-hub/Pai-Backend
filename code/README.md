# PAI Module Documentation

The `code/` directory contains detailed, implementation-oriented documentation grouped by feature.
Runtime source remains under `src/pai/`; executable tests remain under `tests/`.

## Modules

| Module | Canonical source document | Generated exports |
| --- | --- | --- |
| Authentication | [`authentication/authentication_module_architecture.md`](authentication/authentication_module_architecture.md) | HTML and PDF in the same folder |
| Documents | [`documents/document_module_architecture.md`](documents/document_module_architecture.md) | HTML and PDF in the same folder |
| Counselor | [`counselor/counselor_architecture.md`](counselor/counselor_architecture.md) | Markdown |
| Student Vault | [`vault/longitudinal_student_vault_architecture.md`](vault/longitudinal_student_vault_architecture.md) | Markdown |
| Vault testing | [`vault/vault_structure_and_testing_guide.md`](vault/vault_structure_and_testing_guide.md) | Markdown |

Markdown is the canonical editable format. HTML and PDF files are presentation exports and may lag
behind Markdown until explicitly regenerated.

## Repository layout

```text
code/                 Engineering documentation by module
docs/                 Cross-cutting design notes and operational guides
src/pai/              Application source code
tests/                Automated regression and security tests
alembic/versions/     Ordered database migrations
scripts/              Diagnostics, maintenance, and validation utilities
```

Do not place credentials, local environment files, caches, virtual environments, test output, or
runtime captures in `code/`.
