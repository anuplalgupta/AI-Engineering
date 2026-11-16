# Architecture Decision Records

Each record captures one architectural decision for AI-LMS: the situation, what we chose, what we rejected and what follows from it. Requirements come from the [PRD](../PRD.md); IDs such as `V-6` refer to its requirement tables.

| ADR | Decision | Status |
|---|---|---|
| [0001](0001-system-architecture-and-tenancy.md) | One deployable application plus background workers; every record carries an organisation ID; runs on one machine with Docker Compose | Accepted |
| [0002](0002-technology-stack-and-hosting.md) | Python + FastAPI, React (Vite), PostgreSQL for data and job queue, Docker Compose; hosting in three steps from own computer to managed cloud | Accepted |
| [0003](0003-content-ingestion-and-topic-graph.md) | Page-by-page extraction by a vision model or a free local parser behind one interface; topic tree and prerequisites stored as a graph in PostgreSQL; openly licensed sample content | Accepted |
| [0004](0004-video-generation-pipeline.md) | Lesson videos are either uploaded (built first, used by the MVP demo) or rendered by code from a scene specification with free local narration; no generative video, no avatars | Accepted |
| [0005](0005-llm-usage-and-quality-control.md) | All model calls go through one internal gateway with three provider modes (none, free, paid); outputs are grounded, checked automatically, then reviewed by a person; no student screen depends on a model | Accepted |
| [0006](0006-learner-model-and-study-plan.md) | Mastery, diagnostic and study plan are computed by deterministic algorithms, not by a language model; only published content is used; explanations come from templates by default | Accepted |
| [0007](0007-text-tutorials-as-primary-lesson-format.md) | Text tutorials with diagrams are the primary lesson format for the first release; uploaded video stays; generated video moves after the first release. Amends 0004 and 0006 | Accepted |
| [0008](0008-consistency-after-0007-and-demo-mode.md) | Lists the statements in ADRs 0001 to 0007 that later decisions replace; settles statuses, maths checking, a topic with both a tutorial and a video, new versions and withdrawal, changes to an approved tree, and demo mode | Accepted |

## Conventions

- **Status** is one of Proposed, Accepted, Superseded (with a link to the replacement).
- An accepted ADR is not edited to change its decision. Write a new ADR that supersedes it.
- The PRD is a living document. Every ADR ends with a **Revisit if** section naming the PRD assumptions it rests on. When the PRD changes, check those sections first.
- New ADRs take the next number and follow the same headings: Context, Decision, Alternatives considered, Consequences, Revisit if.
