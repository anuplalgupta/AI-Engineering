# Architecture Decision Records

Each record captures one architectural decision for AI-LMS: the situation, what we chose, what we rejected and what follows from it. Requirements come from the [PRD](../PRD.md); IDs such as `V-6` refer to its requirement tables.

| ADR | Decision | Status |
|---|---|---|
| [0001](0001-system-architecture-and-tenancy.md) | One deployable application plus background workers; every record carries an organisation ID | Proposed |
| [0002](0002-technology-stack-and-hosting.md) | Python + FastAPI, Next.js, PostgreSQL, hosted in AWS Mumbai | Proposed |
| [0003](0003-content-ingestion-and-topic-graph.md) | Page-by-page extraction with a vision model; topic tree and prerequisites stored as a graph in PostgreSQL | Proposed |
| [0004](0004-video-generation-pipeline.md) | Videos rendered by code from a scene specification, with synthetic narration; no generative video, no avatars | Proposed |
| [0005](0005-llm-usage-and-quality-control.md) | All model calls go through one internal gateway; outputs are grounded, checked automatically, then reviewed by a person | Proposed |
| [0006](0006-learner-model-and-study-plan.md) | Mastery, diagnostic and study plan are computed by deterministic algorithms, not by a language model | Proposed |

## Conventions

- **Status** is one of Proposed, Accepted, Superseded (with a link to the replacement).
- An accepted ADR is not edited to change its decision. Write a new ADR that supersedes it.
- The PRD is a living document. Every ADR ends with a **Revisit if** section naming the PRD assumptions it rests on. When the PRD changes, check those sections first.
- New ADRs take the next number and follow the same headings: Context, Decision, Alternatives considered, Consequences, Revisit if.
