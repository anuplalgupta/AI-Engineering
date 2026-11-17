# AI-LMS

An AI learning management system for school students, undergraduates and competitive-exam aspirants (IIT-JEE, NEET). It turns textbooks, syllabi and past papers into short topic-wise videos, builds each student a personal playlist from a diagnostic assessment, and tracks progress through adaptive milestone evaluations.

## Documents

| Document | Status |
|---|---|
| [Product Requirements (PRD)](docs/PRD.md) | v1.5, living document |
| [Architecture Decision Records](docs/adr/README.md) | 0001–0008 accepted |
| [Implementation plan](docs/implementation-plan.md) | In progress |
| [Running guide](docs/guide.md) | First version (milestone M1) |

## Running it

Docker is the only thing you need. Full steps, for a non-engineer, are in the [running guide](docs/guide.md). In short, from the repository root:

```sh
sh ai-lms/deploy/setup.sh                                        # once: writes ai-lms/deploy/.env with random secrets
docker compose -p ailms -f ai-lms/deploy/compose.yaml up -d      # start; then open http://localhost:8080
```

| Folder | What it holds |
|---|---|
| `backend/` | Python API and worker ([README](backend/README.md)) |
| `web/` | The web app (React, Vite), served by Caddy |
| `deploy/` | Docker Compose file and setup scripts |
| `sample-data/` | The sample course loaded on first start |
