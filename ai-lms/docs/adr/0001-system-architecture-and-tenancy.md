# ADR 0001: System architecture and tenancy

| | |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-11-16 |
| **PRD requirements** | A-1, A-8, V-6, V-7, X-5, X-7, X-8, open question 2 |
| **Amended by** | [ADR 0008](0008-consistency-after-0007-and-demo-mode.md) (proposed): contents of the `content` module (item 1), workers in the first release (item 2), statuses per kind of item (item 3) |

## Context

The product has two very different kinds of work:

- **Interactive work**: students watching videos, answering quizzes and viewing dashboards; admins reviewing content. Requests must return in well under a second. Pilot scale is 5,000 students, 500 at once (X-5).
- **Content production**: reading PDFs, building the topic tree, writing scripts, rendering video. Each step takes minutes, can fail, costs money, and some steps wait hours or days for a person to approve (A-4, V-6).

The team is small and the product is unproven. The PRD assumes a single operator, but whether this becomes software sold to many institutes is still open, and adding tenant separation to an existing database later is one of the most expensive changes there is.

## Decision

1. **One application, split into modules.** A single backend codebase and deployment with clear internal modules: `identity`, `catalog` (courses, topic graph, sources), `content` (scripts, videos, questions, review), `assessment`, `learner` (mastery, plans, progress) and `analytics`. Modules call each other through defined interfaces, not each other's tables.
2. **Background workers for content production.** The same codebase runs as a second process type that takes jobs from a queue. Rendering workers run separately from other workers because they need more CPU and memory.
3. **The content pipeline is an explicit state machine stored in the database.** Each source file, topic and video has a status (for example `extracted → tree_proposed → tree_approved → script_ready → rendered → in_review → published`). Workers move items forward; a person moves them through approval steps. Every step can be retried or re-run for a single item (V-7) without affecting others.
4. **Pipeline steps survive worker failure.** Every step is safe to run twice (same input gives the same result, with no duplicate records or files). An item being worked on holds a lease with an expiry time; if the worker dies, the lease runs out and the item returns to the queue. After a fixed number of failed tries the item is marked failed and shown to the admin, not retried forever.
5. **Every status change is recorded.** A transition log table stores, for each change: the item, old and new status, who or what made the change (person or worker), when, and any comment. The status column gives the current state; the log gives the history the review gate needs (V-6).
6. **Tenant-ready from day one, single tenant in practice.** Every table that holds operator-owned or student-owned data has an `organisation_id` column, and every query filters on it through a shared data-access layer. The pilot has exactly one organisation. No tenant-management screens, billing or per-tenant configuration are built now.
7. **The whole product runs on one machine.** Web app, backend, workers, database and file storage all start together with Docker Compose on a laptop or a single small server (X-7, X-8). Larger deployments run the same containers spread over more machines; the code does not change. Component choices are in ADR 0002.
8. **Module boundaries are checked automatically.** An import-rule check in the build fails if one module imports another's internals.

## Alternatives considered

| Alternative | Why not |
|---|---|
| Separate services per module from the start | Adds deployment, networking and data-consistency work that a small team does not need at 500 concurrent users. Module boundaries inside one codebase let us split later if a real need appears. |
| A workflow engine (such as Temporal) for the pipeline | A good fit for long-running steps with human approval, but another system to run and learn. A status column and a job queue cover the pilot. Reconsider if the pipeline grows many branching paths. |
| No tenant column until multi-institute is confirmed | Cheapest today, but a retrofit touches every table, query and test. One column and one filter now costs very little. |
| A separate database per institute | Strongest isolation, but heavy to operate and unnecessary until an institute asks for it. |

## Consequences

- One thing to deploy, monitor and debug. A new developer can run the whole product locally.
- Slow, expensive work never blocks student requests, and render capacity can grow independently.
- The pipeline's state is visible in ordinary tables, which makes the admin status screens (A-3, V-10) simple to build.
- Module boundaries are enforced for code imports by the build check. Nothing physically prevents one module's queries reading another's tables; that is kept up by review.
- On one small machine, rendering and student requests share CPU, so a demo deployment renders slowly and may feel slow while rendering. Accepted for the MVP (X-7); moving render workers to their own machine fixes it without code changes.
- **Open point, not decided here:** whether a student's phone number or email is unique across all organisations or only within one. It does not matter with a single organisation and must be decided before a second one exists.
- Every query carries an organisation filter. Forgetting it would leak data once a second organisation exists, so the filter lives in one shared layer and is covered by tests.

## Revisit if

- **PRD open question 2** changes to "sold to many institutes": add tenant management, per-tenant content libraries and stronger isolation (likely database row-level security). The data model is already prepared.
- Concurrent students grow well beyond X-5, or one module needs to scale very differently from the rest.
- The pipeline gains many conditional paths, at which point a workflow engine earns its keep.
