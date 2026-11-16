# ADR 0008: Consistency after ADR 0007, demo mode and small open points

| | |
|---|---|
| **Status** | Accepted (2026-11-16, under the owner's go-ahead to build on the recommended answers; open to review) |
| **Date** | 2026-11-16 |
| **PRD requirements** | A-4, S-1, V-2, V-6, V-11, V-12, V-13, P-1, P-2, T-1, X-4, X-7, X-8 |
| **Amends** | ADR 0001 (items 1 to 3), 0002 (what the demo needs; sign-in on a public demo), 0003 (wording), 0004 (items 2 and 9, the no-account table, image size), 0005 (items 1, 2, 4, 5), 0006 (items 14, 16, 28), 0007 (items 4, 10, 11, 12) |

## Context

ADR 0007 made text tutorials the primary lesson format after ADRs 0001 to 0006 had been accepted. A review of the [implementation plan](../implementation-plan.md) against all the documents found two kinds of problem:

- **Leftovers.** Statements in the earlier ADRs that still describe the product as it was before ADR 0007: a worker image full of animation tools, a demo built on finished videos, statuses named after video scripts.
- **Gaps.** Points that no ADR decides and that two developers would build differently: how maths is checked when the containers hold no LaTeX, what happens when a topic has both a tutorial and a video, what happens to a student when a lesson changes, whether an approved topic tree can still be restructured, and how the demo accounts sign in on a public server.

Accepted ADRs are not rewritten (see the conventions in the [index](README.md)). This ADR therefore lists which earlier statements are replaced, and decides the gaps.

## Decision

### A. How to read the earlier ADRs

1. **Where an earlier ADR and a later ADR that amends it differ, the later one applies.** The earlier ADR carries an "Amended by" line in its header.
2. **Statements replaced:**

   | ADR | Earlier statement | Now reads |
   |---|---|---|
   | 0001 item 1 | The `content` module holds scripts, videos, questions and review | It holds lessons (tutorials and videos), questions and review |
   | 0001 item 2 | Rendering workers run separately from other workers | In the first release there is one worker by default. Video encoding of uploads runs in it, one job at a time. PDF extraction runs as an optional second worker. Separate render workers arrive with generated video (stage 3) |
   | 0001 item 3 | One example chain of statuses ending in `script_ready → rendered → in_review → published` | Statuses per kind of item, in section B |
   | 0002 "What the demo needs" | LaTeX and the animation tools are inside the containers; the sample data has a few finished videos; generating new content depends on narration choices | In the first release the containers hold no LaTeX, animation tools or speech engine. The sample data is one small course with its topic tree, finished tutorials with diagrams, questions with worked solutions, one short video, and three demo accounts. Generating new content depends only on ADR 0005 |
   | 0003 context, item 11, consequences | "Scripts" and "videos" | Lesson content and lessons |
   | 0004 item 2 | The uploaded path is built first and is what the MVP demo uses | Tutorials are built first (ADR 0007), uploaded video second, generated video after the first release |
   | 0004 no-account table and consequences | A generated sample video can be edited and re-rendered offline; the worker image is large | Both apply only from stage 3 |
   | 0005 item 1 | Tasks include `write_script` | Tasks include `write_tutorial`; `write_script` belongs to stage 3 |
   | 0005 item 2 | Embeddings are served in the worker in every mode | The embedding model is loaded only when a provider mode other than "none" is configured. The default demo worker does not include it |
   | 0005 items 4, 5 | Scripts are grounded; checks run before rendering; an item reaches `script_ready`; every scene has narration and sources | Lesson content is grounded; checks run before a tutorial reaches `rendered`; every section has sources |
   | 0005 consequences | Cost per video | Cost per lesson |
   | 0006 items 14, 16 | "Video item", "video coming", video length | "Lesson item", "lesson coming", reading time for a tutorial and length for a video |

### B. Statuses for each kind of item

3. **Each kind of item has its own short chain** (replaces the single example in ADR 0001 item 3):

   | Item | Statuses, in order | Notes |
   |---|---|---|
   | Source file | `uploaded` → `pages_ready` → `extracted` | `extracted` only where extraction is run (ADR 0003) |
   | Topic tree | `draft` or `tree_proposed` → `tree_approved` | A tree built by hand or imported starts as `draft`; one proposed by a model as `tree_proposed` |
   | Text tutorial | `draft` → `rendered` → `in_review` → `published` | `rendered` means the automatic checks passed and the diagrams are stored. A hand-written tutorial is a `draft` until its author submits it |
   | Uploaded video | `uploaded` → `rendered` → `in_review` → `published` | `rendered` means encoded |
   | Generated video (stage 3) | `script_ready` → `rendered` → `in_review` → `published` | As ADR 0004 item 17 |
   | Question | `draft` → `in_review` → `approved` | A flagged question (ADR 0005) stays `in_review` |

   Any item can also be `failed` (a worker step gave up, ADR 0001 item 4). A reviewed item can be `rejected`, which returns it to its author with the comment. A published lesson or approved question can be `withdrawn` (section E).

### C. Checking maths without LaTeX in the containers

4. **One open-source maths renderer is used in two places**: in the browser to display maths, and on the server to check every maths string when a lesson or question is saved or generated. Maths is stored as LaTeX source. A string is valid if that renderer accepts it.
5. **First candidate: KaTeX**, confirmed on the three trial tutorials in the implementation plan (M4) before the editor is built.
6. **The server check runs as a command-line step in the worker.** This adds a small JavaScript runtime to the worker image and nothing else.
7. **The "compiles with LaTeX" check and the list of allowed packages** in ADR 0004 item 9 and ADR 0005 item 5 apply only to generated video (stage 3).
8. **Notation the renderer cannot typeset is not used in tutorials.** The author, or the generation step, is told which section failed.

### D. A topic with both a tutorial and a video

9. **The tutorial is the lesson the study plan schedules**, by its reading time. The video is offered after it as optional and adds no planned time.
10. **A topic with only a video** is scheduled by the video's length.
11. **Completion.** The lesson is complete when the student marks the tutorial done (ADR 0007 item 10). Where there is only a video, it is complete when the watched position passes a configured share of its length (default 90%). Progress on both is stored (T-1).

### E. New versions and withdrawal

12. **Sections keep the same identity across versions of a tutorial.** When a new version is approved, a student who had completed the lesson stays completed. A student part-way through continues at the same section if it still exists, otherwise from the start, with a note that the lesson was updated.
13. **An admin can withdraw a published lesson or an approved question.** It is no longer shown or used. The plan then treats the topic as ADR 0006 item 14 describes (practice only, or not yet available). Attempts and ratings are kept, and the withdrawal is recorded in the status-change log.

### F. Changing an approved topic tree

14. **Always allowed:** renaming a topic, reordering, and adding or removing a prerequisite link (with the loop check). Students affected by a changed link are re-planned.
15. **Merging, splitting or deleting a topic** is allowed only while no student attempt is linked to it. After that it is refused with an explanation, until the rule for mapping old topics to new ones (ADR 0006 "Revisit if") is decided. PRD A-4's "edit, merge, split" is met in full before students start, and "reset demo data" clears attempts so the editor can be shown in full in a demo.

### G. Demo mode

16. **Every deployment has a demo mode setting.** It is on for the own-computer route and for a public demo server. It is off for a deployment with real students.
17. **With demo mode on:**
    - The sign-in page offers entry as each of the three demo accounts (ADR 0002) without an email code.
    - On a public server, that entry needs one access code which the operator chooses during setup; new sign-ups are closed; the local mail viewer cannot be reached from the internet; a banner says the site holds sample data only.
    - On the operator's own computer, sign-up by email code stays open, with the code shown in the local mail viewer, so that sign-up (S-1) can be shown.
    - Presenter controls are available: "reset demo data", "retake diagnostic" (ADR 0006 item 27) and "move the date forward", which uses the clock (ADR 0006 item 25).
18. **"Reset demo data" restores the whole sample data set** (extends ADR 0006 item 28): courses, topic tree, lessons with their review states, questions, accounts, student history, calibration version and stored files.
19. **A public demo needs no email-sending service** (amends ADR 0002 consequences).
20. **With demo mode off:** there is no demo entry and there are no presenter controls. Sign-in is by email code through an email-sending service. Sign-ups by new students stay closed until the consent flow exists (PRD S-6). The deployment must be in an Indian region with encryption at rest (ADR 0002).

## Alternatives considered

| Alternative | Why not |
|---|---|
| Rewrite the accepted ADRs in place | Removes the contradictions at their source, but breaks the rule that an accepted decision is not edited, and loses the record of what was decided when. |
| Keep a LaTeX installation in the worker to check maths | Checks against a different system from the one that displays the maths, and brings back most of the image size that ADR 0007 removed. |
| Check maths only in the browser editor | Generated tutorials never pass through the editor, so the server must be able to check. |
| Schedule both the tutorial and the video | Doubles the planned time for one topic, so more topics are dropped from a plan that has to fit a target date. |
| Real email addresses for the demo accounts on a public demo | Needs an email-sending account and three real mailboxes: more setup for a non-engineer, and a running cost. |
| Open sign-up on a public demo | Collects real people's personal data on a server that may be outside India and has no consent flow (X-4, S-6). |
| Demo entry with no access code | Anyone who finds the address could act as admin and upload files to the operator's server. |
| Allow merge and split at any time and rebuild the ratings | Needs the mapping rule that ADR 0006 leaves open, and is not needed for the pilot. |

## Consequences

- The earlier ADRs must be read together with their "Amended by" lines. The table in section A is the single list of what changed.
- The worker image gains a small JavaScript runtime for the maths check.
- Some notation that a full LaTeX installation accepts cannot be used in tutorials.
- A student who prefers the video is still given planned time based on reading.
- An admin cannot merge or split a topic once students have attempts on it.
- Demo mode is code that must never be active in a real deployment. The setting is read at start, shown on the admin screen, and covered by a test that demo entry and presenter controls are absent when it is off.
- A public demo is protected by one shared access code, which is enough for sample data and not for anything else.

## Revisit if

- The trial tutorials show the renderer cannot typeset notation the pilot syllabus needs: choose a different renderer, or check with LaTeX on the server.
- The pilot shows that students mostly choose the video where both exist: schedule by the format the student uses.
- An admin needs to merge or split topics after students have started: decide the mapping rule.
- Visitors to a public demo need to try sign-up themselves: add a sign-up that collects no real personal data.
- The PRD changes S-1, S-6, X-4, X-7 or X-8.
