# ADR 0001: System architecture and tenancy

| | |
|---|---|
| **Status** | Proposed |
| **Date** | 2026-11-16 |
| **PRD requirements** | A-1, A-8, V-6, V-7, X-5, open question 2 |

## Context

The product has two very different kinds of work:

- **Interactive work**: students watching videos, answering quizzes and viewing dashboards; admins reviewing content. Requests must return in well under a second. Pilot scale is 5,000 students, 500 at once (X-5).
- **Content production**: reading PDFs, building the topic tree, writing scripts, rendering video. Each step takes minutes, can fail, costs money, and some steps wait hours or days for a person to approve (A-4, V-6).

The team is small and the product is unproven. The PRD assumes a single operator, but whether this becomes software sold to many institutes is still open, and adding tenant separation to an existing database later is one of the most expensive changes there is.

## Decision

1. **One application, split into modules.** A single backend codebase and deployment with clear internal modules: `identity`, `catalog` (courses, topic graph, sources), `content` (scripts, videos, questions, review), `assessment`, `learner` (mastery, plans, progress) and `analytics`. Modules call each other through defined interfaces, not each other's tables.
2. **Background workers for content production.** The same codebase runs as a second process type that takes jobs from a queue. Rendering workers run separately from other workers because they need more CPU and memory.
3. **The content pipeline is an explicit state machine stored in the database.** Each source file, topic and video has a status (for example `extracted → tree_proposed → tree_approved → script_ready → rendered → in_review → published`). Workers move items forward; a person moves them through approval steps. Every step can be retried or re-run for a single item (V-7) without affecting others.
4. **Tenant-ready from day one, single tenant in practice.** Every table that holds operator-owned or student-owned data has an `organisation_id` column, and every query filters on it through a shared data-access layer. The pilot has exactly one organisation. No tenant-management screens, billing or per-tenant configuration are built now.

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
- The discipline of module boundaries has to be kept up by review and tests; nothing physically prevents one module reading another's tables.
- Every query carries an organisation filter. Forgetting it would leak data once a second organisation exists, so the filter lives in one shared layer and is covered by tests.

## Revisit if

- **PRD open question 2** changes to "sold to many institutes": add tenant management, per-tenant content libraries and stronger isolation (likely database row-level security). The data model is already prepared.
- Concurrent students grow well beyond X-5, or one module needs to scale very differently from the rest.
- The pipeline gains many conditional paths, at which point a workflow engine earns its keep.
