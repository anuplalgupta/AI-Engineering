# AI-LMS backend

Python 3.12, FastAPI, SQLAlchemy 2, Alembic, psycopg 3 and Procrastinate (job queue in PostgreSQL). Everything below runs with Docker only; nothing needs to be installed on the computer. Commands are run from the repository root.

## Layout

| Path | What it holds |
|---|---|
| `src/ailms/platform/` | Shared plumbing: settings, database and the organisation filter, clock, storage, queue, security, mail, audit log, SVG cleaning, trusted proxy |
| `src/ailms/{identity,catalog,content,assessment,learner,analytics}/` | The six modules (ADR 0001). Another module may import only a module's `api.py` |
| `src/ailms/main.py` | The FastAPI app; every route is under `/api` |
| `src/ailms/bootstrap.py` | Start-up: wait for the database, migrate, create the bucket, load the sample data (under a PostgreSQL advisory lock) |
| `src/ailms/seed.py` | Loads `ai-lms/sample-data` into an empty database |
| `migrations/` | Alembic migrations; `0002` applies Procrastinate's own schema |
| `tests/` | Tests, the module-boundary check and the OpenAPI drift check |
| `openapi.json` | The committed API description; the web app's client is generated from it |

## Rules the build enforces

- **Organisation filter** (ADR 0001 item 6). Every table holding an organisation's data uses the `OrganisationOwned` mixin. A database session must be scoped with `scope_to_organisation()` before it touches such a table: reads, updates and deletes are filtered automatically and new rows get the organisation set. With no organisation set, the statement raises `UnscopedQueryError`. `system_scope()` is the one explicit way round it (start-up, and finding a session from its cookie).
- **One clock** (ADR 0006 item 25). Only `platform/clock.py` may read the system time; `tests/test_clock_rule.py` fails otherwise.
- **Module boundaries** (ADR 0001 item 8). `lint-imports` runs inside the tests (`tests/test_checks.py`), using the contracts in `pyproject.toml`.
- **API contract.** `tests/test_checks.py` fails when `openapi.json` differs from what the code generates.

## Common commands

```sh
# Run all tests (in a throwaway database that is created and dropped by the tests)
docker compose -p ailms -f ai-lms/deploy/compose.yaml run --rm backend pytest

# Only the module-boundary check, or only the OpenAPI drift check
docker compose -p ailms -f ai-lms/deploy/compose.yaml run --rm --no-deps backend lint-imports --no-cache
docker compose -p ailms -f ai-lms/deploy/compose.yaml run --rm --no-deps backend python -m ailms.tools.openapi --check

# Regenerate openapi.json after changing a route (rebuild the image first)
docker compose -p ailms -f ai-lms/deploy/compose.yaml build backend
docker compose -p ailms -f ai-lms/deploy/compose.yaml run --rm --no-deps -T backend python -m ailms.tools.openapi > ai-lms/backend/openapi.json

# Create a new migration after changing a model (writes into backend/migrations/versions)
docker compose -p ailms -f ai-lms/deploy/compose.yaml run --rm --no-deps --user root \
  -v "$PWD/ai-lms/backend/migrations:/app/migrations" backend alembic revision --autogenerate -m "what changed"
```

The image contains the source, so rebuild it (`docker compose ... build backend`) after changing code before running the tests.

## Dependencies

`requirements.in` lists the direct dependencies; `requirements.txt` pins every package with hashes. To regenerate it (inside a container, so the host needs nothing):

```sh
docker run --rm -v "$PWD/ai-lms/backend:/work" -w /work python:3.12.16-slim-bookworm sh -c \
  "pip install uv==0.5.11 && uv pip compile --exclude-newer <date two weeks ago>T00:00:00Z \
   --python-version 3.12 --python-platform linux --generate-hashes requirements.in -o requirements.txt"
```

## Building behind a company proxy that inspects HTTPS

If `pip install` fails during the image build with `CERTIFICATE_VERIFY_FAILED`, the network replaces certificates with its own. Export the proxy's root certificate as a PEM file and point `AILMS_EXTRA_CA` at it (in `deploy/.env` or the shell). It is passed to the build as a secret and only added to the trusted list for that step; certificates are still checked, and nothing is stored in the image.
