# ADR 0002: Technology stack and hosting

| | |
|---|---|
| **Status** | Proposed |
| **Date** | 2026-11-16 |
| **PRD requirements** | S-1, X-1, X-2, X-4, X-5, section 8 (children's data) |

## Context

The stack must suit three things: heavy use of AI and document-processing libraries, a phone-first web app that works on slow connections (X-1, X-2), and student data stored in India (X-4). The team is small, so fewer technologies and more managed services are better.

## Decision

| Layer | Choice | Reason |
|---|---|---|
| Backend and workers | **Python, FastAPI** | The PDF, maths-animation and AI tooling we need (ADR 0003, 0004) is in Python. One language for API and workers. |
| Web app | **TypeScript, Next.js (React)**, responsive, installable as a home-screen app | One web codebase for student and admin screens. Server-rendered pages load quickly on slow phones. |
| Main database | **PostgreSQL** | Relational data (courses, attempts, plans), the topic graph (ADR 0003) and text search with embeddings (`pgvector` extension) all in one database. |
| Job queue | **Redis-backed queue** (Celery) | Mature, well understood, enough for the pilot. Pipeline state itself lives in PostgreSQL (ADR 0001). |
| Files and video | **Object storage** with a **content delivery network** in front | PDFs, rendered video segments, captions. Video is served as HLS at several quality levels so playback adapts to the connection (X-2). |
| Hosting | **AWS, Mumbai region (ap-south-1)**: containers on ECS Fargate, RDS for PostgreSQL, ElastiCache, S3, CloudFront | Keeps student data in India (X-4). Managed services reduce operations work. |
| Sign-in | Phone one-time code and email, through a managed identity service; sessions issued by our backend | Phone number is the normal sign-in for Indian students (S-1). We do not build password or code-delivery handling ourselves. The specific provider is chosen during implementation; requirement: India data residency. |
| Infrastructure definition | Terraform | Environments are reproducible and reviewed like code. |

**Data handling rules that follow from X-4 and the children's-data risk:**

- Student personal data and assessment history stay in the Mumbai region.
- Text sent to AI model providers for content generation comes from source material, not from students. Where a model call does concern a student (for example writing a milestone report), it receives a pseudonymous ID and scores only: no name, phone number or email.
- No advertising or third-party tracking scripts on student pages.
- Encryption in transit and at rest; access to student data is logged.

## Alternatives considered

| Alternative | Why not |
|---|---|
| TypeScript for the backend too | One language overall, but the document and animation libraries we depend on are Python. We would end up running Python workers anyway. |
| Native Android app first | Most students are on Android, but a native app doubles front-end work and slows release cycles. The PRD puts native apps out of scope; a web app installable to the home screen covers the pilot. |
| A separate vector database | Another system to run. `pgvector` handles the pilot's volume (tens of thousands of text chunks). |
| A separate graph database for the topic tree | The graph is small (thousands of nodes). PostgreSQL tables and recursive queries are sufficient. |
| A video platform service (hosted player and encoding) | Faster to start, but per-minute pricing grows with every student view, and data location is harder to control. Our videos are simple to encode ourselves. |
| Google Cloud or Azure in India | Both workable. AWS is chosen for breadth of managed services in Mumbai; nothing in the design depends on AWS-only features beyond standard building blocks. |

## Consequences

- Two languages (Python, TypeScript) to maintain, with an API contract between them. The contract is generated from the backend's OpenAPI description so the two cannot drift silently.
- PostgreSQL carries a lot: transactional data, the graph and embeddings. This is simple now and may need splitting at much larger scale.
- Offline video download (X-6, P2) is harder in a web app than a native one. Accepted for now.
- Hosting cost is dominated by video rendering and delivery, not by the application servers.

## Revisit if

- The PRD brings native apps or offline download into scope.
- Legal advice on children's data (PRD section 8) requires stricter controls than listed here.
- An institute customer requires a different cloud or on-premises hosting (linked to PRD open question 2).
