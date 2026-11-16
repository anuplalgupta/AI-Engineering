# ADR 0002: Technology stack and hosting

| | |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-11-16 |
| **PRD requirements** | S-1, X-1, X-2, X-4, X-5, X-7, X-8, section 8 (children's data) |
| **Amended by** | [ADR 0008](0008-consistency-after-0007-and-demo-mode.md) (proposed): what the demo needs, and how demo accounts sign in on a public demo |

## Context

The stack must suit four things:

- heavy use of AI and document-processing libraries;
- a phone-first web app that works on slow connections (X-1, X-2);
- student data stored in India (X-4);
- an MVP that costs as little as possible, ideally nothing, and that a non-engineer can start on their own computer to demonstrate (X-7, X-8).

Slow performance is acceptable for the MVP. What is not acceptable is a design that has to be rebuilt to go faster. So the rule for this ADR is: **the fewest components that can run on one machine, each one replaceable by a larger or managed version through configuration alone.**

## Decision

### Components

| Layer | Choice | Reason |
|---|---|---|
| Backend and workers | **Python, FastAPI** | The PDF, maths-animation and AI tooling we need (ADR 0003, 0004) is in Python. One language for API and workers. |
| Web app | **TypeScript, React, built with Vite** into static files; responsive; installable as a home-screen app | One web codebase for student and admin screens. Static files need no server process of their own. |
| Main database | **PostgreSQL** with the `pgvector` extension | Relational data, the topic graph (ADR 0003), embeddings for text search, and the job queue, all in one database. |
| Job queue | **Inside PostgreSQL** (a Python library such as Procrastinate, which uses row locking) | No separate queue service to run. Matches the lease and retry design in ADR 0001. |
| Files and video | **Any S3-compatible object store**, reached through one storage interface | MinIO in a container locally; a hosted bucket later. Video is served as HLS at several quality levels (X-2). |
| Web server | **Caddy** | Serves the static web app, passes API requests to the backend, and obtains HTTPS certificates automatically when given a domain name. |
| Sign-in | **Email one-time code** for the MVP, behind a sign-in interface; sessions issued by our backend. Demo accounts for each persona are created with the sample data. | Free to run. Phone one-time code (S-1) is added later behind the same interface; SMS in India costs per message and needs sender registration. |
| Packaging | **Docker Compose** | One file starts everything. The same containers are used at every hosting step. |

### Hosting steps

The same containers run at each step. Moving up a step changes configuration and where things run, not code.

| Step | For | What runs where | Cost |
|---|---|---|---|
| **1. Own computer** | Building and demonstrating | Docker Compose on a Windows PC (through WSL 2), Mac or Linux. No cloud account. Email codes are shown in a local mail viewer instead of being sent. | None |
| **2. One small server** | A few users over the public internet | The same Compose file on a single free-tier or low-cost virtual server, with a domain name and automatic HTTPS. | Free to about US$5–10 a month |
| **3. Managed cloud** | The real pilot (X-5) | Backend and workers as managed containers, managed PostgreSQL, hosted object storage with a content delivery network, render workers on their own machines. Infrastructure defined with Terraform. | Grows with use |

**Rules for choosing a provider at steps 2 and 3:**

- If any real student uses the deployment, the server and database are in an Indian region (X-4). A demonstration with sample accounts only may run anywhere.
- Free-tier offers change. The provider is confirmed when the deployment is set up, not fixed here. The running guide (X-8) names one tested option.
- At step 3 the default is AWS Mumbai (ECS Fargate, RDS, S3, CloudFront); nothing in the design depends on AWS-only features.

### What the demo needs

- **Minimum computer:** 8 GB memory, 4 processor cores, 10 GB free disk, Docker installed. All other software, including LaTeX and the animation tools, is inside the containers.
- **Sample data is included** (X-8): one small course with its topic tree, a few finished videos, questions and three demo accounts. The complete flow for each persona can be shown with no AI provider account and no internet connection.
- Generating new content from a newly uploaded PDF needs whatever ADRs 0004 and 0005 decide for narration and model calls.

### Data handling rules that follow from X-4 and the children's-data risk

- Student personal data and assessment history stay in India once real students use the product.
- Text sent to AI model providers for content generation comes from source material, not from students. Where a model call does concern a student (for example writing a milestone report), it receives a pseudonymous ID and scores only: no name, phone number or email.
- No advertising or third-party tracking scripts on student pages.
- Encryption in transit and at rest; access to student data is logged.

## Alternatives considered

| Alternative | Why not |
|---|---|
| Next.js for the web app | Server rendering mainly helps public pages; almost every screen here is behind sign-in. It adds a Node server process to run on a small machine and invites backend logic to drift out of the FastAPI modules (ADR 0001). Reconsider if public, searchable pages come into scope; the React components carry over. |
| TypeScript for the backend too | One language overall, but the document and animation libraries we depend on are Python. We would end up running Python workers anyway. |
| Redis-backed queue (Celery) | Mature, but a second service to run and pay for. A PostgreSQL queue is enough at pilot volume. Reconsider if queue throughput becomes a limit. |
| Managed cloud services from the start | Monthly cost from the first day and nothing a non-engineer can run locally. Kept as step 3. |
| Free hosted services for each part (separate hosted database, hosted front end, hosted functions) | Free, but each has its own limits and sleep behaviour, and the deployment no longer matches what runs locally. One server running the same Compose file is simpler to explain and debug. |
| SQLite as the database | Even simpler to run, but no `pgvector`, weaker concurrent writes, and a migration needed before the pilot. |
| Native Android app first | Doubles front-end work. The PRD puts native apps out of scope; an installable web app covers the pilot. |
| A separate vector or graph database | More systems to run. PostgreSQL handles the pilot's volume for both. |
| A video platform service | Per-minute pricing grows with every view, and data location is harder to control. |
| A managed identity service | Adds an external dependency and usually a cost for phone codes. Email codes from our own backend are enough for the MVP; the sign-in interface leaves this open. |

## Consequences

- Two languages (Python, TypeScript) to maintain, with an API contract between them. The contract is generated from the backend's OpenAPI description so the two cannot drift silently.
- Three running services at step 1 and 2 (backend with workers, PostgreSQL, object store) plus the web server. This is what keeps the running guide short.
- PostgreSQL carries a lot: transactional data, the graph, embeddings and the queue. Simple now; the queue and embeddings are the first candidates to move out at larger scale.
- The first page load is slower than a server-rendered page, because the app downloads before anything shows. Reduced by splitting the app into small parts and caching it after the first visit.
- At steps 1 and 2, rendering shares the machine with student requests, so rendering is slow and the app may feel slow while it runs (ADR 0001).
- At step 2 there are no automatic backups or failover unless we add them. A scheduled database dump to the object store is the minimum before any real user data is held.
- Sending email codes to real users at step 2 needs an email-sending service; free tiers cover a few users.
- Offline video download (X-6, P2) is harder in a web app than a native one. Accepted for now.

## Revisit if

- The PRD brings native apps, offline download or public searchable pages into scope.
- Legal advice on children's data (PRD section 8) requires stricter controls than listed here.
- An institute customer requires a different cloud or on-premises hosting (linked to PRD open question 2).
- Phone sign-in is needed before step 3: choose an SMS provider and complete sender registration.
- Budget is available and speed matters: move to step 3, starting with separate render workers.
