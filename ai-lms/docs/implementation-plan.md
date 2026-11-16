# Implementation plan: AI-LMS pilot

| | |
|---|---|
| **Status** | In progress. On 2026-11-16 the owner approved starting the build on the recommended answers below, and will review the result and ask for changes afterwards. |
| **Date** | 2026-11-16 |
| **Based on** | [PRD](PRD.md) v1.5 and [ADRs](adr/README.md) 0001–0008 (0008 is proposed) |
| **Team assumed** | One or two developers working with an AI coding assistant |

This plan gives the order of the work and what must be true at the end of each step. It gives no dates: order and dependencies matter, not durations. IDs such as `V-12` refer to the PRD's requirement tables.

## How the plan is ordered

1. **Demo first.** The first milestone is a thin slice that starts with one command and shows one tutorial. Every later milestone widens that same running system with something a non-engineer can show.
2. **The guide, the sample course and the demo commands grow in every milestone** and are tested each time by someone who did not write the code. They are never left to the end.
3. **Risky foundations are tried early**, before anything depends on them: the organisation filter, the worker lease and retry rules, the lesson format on a real phone, and the mastery and diagnostic rules with simulated students.
4. **No language model until stage 2.** Stage 1 uses included sample content, hand-written tutorials and uploaded questions and videos.

## Overview

| # | Milestone | What can be shown when it is done |
|---|---|---|
| | **Stage 1 — MVP demo** | |
| M1 | Walking skeleton | One command starts the product; the demo student opens one tutorial on a phone-width screen |
| M2 | Courses, topic tree and question bank | The admin builds or imports a topic tree, approves it and adds questions |
| M3 | Mastery and diagnostic as a tested library | Nothing on screen: a report from simulated students, and the number of sample questions needed |
| M4 | Lesson format, source pages and pipeline core | The admin uploads a textbook and sees its pages; three real tutorials read well on a phone |
| M5 | Tutorial editor and review gate | The admin writes a tutorial; the reviewer approves, rejects or edits it; only then does a student see it |
| M6 | Student lesson, quiz and mastery | The student reads a tutorial, takes the quiz and sees mastery change |
| M7 | Onboarding, diagnostic and gap map | A new student signs up, takes a five-minute diagnostic and gets a gap map |
| M8 | Playlist and study plan | The student gets a dated plan that changes after a quiz and says why |
| M9 | Milestones, reports, dashboard, demo student | The whole student flow in one sitting, with reset and "move the date forward" |
| M10 | Uploaded video lessons | The admin uploads a video; the student sees the tutorial, then the video |
| M11 | MVP demo release | A non-engineer runs it from the guide on a PC and on a cheap public server |
| | **Stage 2 — Generated tutorials** | |
| M12 | PDF extraction with the free local parser | The admin sees extracted text, equations and figures, and the pages that could not be read |
| M13 | Model gateway, checks, proposed tree, past papers | The system proposes a topic tree and turns a past paper into questions |
| M14 | Generated tutorials and questions | The admin presses "generate" and gets a tutorial and questions for review |
| | **Pilot readiness — before real students** | |
| M15 | Privacy, consent and accounts | An under-18 student cannot get an account without parental consent; data can be deleted |
| M16 | India hosting, scale and pilot content | Hosted in India, tested at 500 students at once, pilot course published |
| | **Stage 3 — after the first release** | |
| M17 | Generated video | A narrated video is rendered from a topic's lesson content |

M3 can be built alongside M2. M15 can start after M11 and run alongside stage 2. M10 is the first milestone to move if stage 1 has to be shortened: nothing else in stage 1 depends on it.

## Work that is not code

These start now and run alongside. Each one blocks a milestone if it is late.

| Track | What is needed | Needed by |
|---|---|---|
| Sample slice | Choose which chapters of the openly licensed textbook form the sample course: a small set of linked topics | M2 |
| Subject expert | Someone who can check sample tutorials and questions and later approve the evaluation set | M5, M13 |
| Sample content | Tutorials and questions written a few topics at a time, to the counts set in M3 | M4 to M11 |
| Legal advice: under-18 data | India's data-protection law for minors: how consent is verified, what history may be kept and for how long | M15 |
| Content rights | Rights to the pilot books and past papers, and whether their text may be sent to a model provider outside India | M16 |
| Provider choices | Model provider for paid mode; hosting provider for the pilot | M13, M16 |

## Stage 1 — MVP demo

No language model, free components only (X-7, X-8).

### M1 Walking skeleton

**Shows:** one command starts the product on a PC; the presenter enters as the demo student and opens one tutorial with an equation and a diagram on a phone-width screen.

**Builds:**
- Backend with the six modules and the automatic module-boundary check (ADR 0001 items 1, 8).
- Docker Compose file: web server, backend, worker, PostgreSQL, object store, local mail viewer (ADR 0002). One start command prepares the database and loads the sample data on first start. A setup command writes passwords and secrets to a settings file; there are no default passwords.
- Organisation table and the shared data-access layer with the organisation filter. Tests run with two organisations and check that no query or page leaks from one to the other (ADR 0001 item 6).
- Sign-in by email one-time code; three fixed roles (admin, reviewer, student); demo-mode entry as each demo account (ADR 0008 section G).
- One clock for all time-dependent code (ADR 0006 item 25). The PostgreSQL job queue, running one trivial job.
- Web app shell (React, Vite), API client generated from the backend, maths renderer, read-only tutorial page.
- Lesson record in the real format of ADR 0007 item 3, with a format version and a status. Student pages return only published lessons from the start.
- Sample data: one organisation, three demo accounts, one course, one topic, one tutorial from the open textbook with its licence and attribution.
- Running guide, first version: install Docker, start, enter, stop, where the data is kept.
- Automatic build: tests, module-boundary check, API-contract check, and container images published so that nobody following the guide has to build them.

**Covers:** X-7, X-8, S-1 (email), X-1, V-12 (display), A-1 (data model). **Depends on:** nothing.

**Done when:**
- On a clean Windows PC with WSL 2 and only Docker installed, a person who did not write the code follows the guide and reaches the tutorial.
- The email code appears in the local mail viewer and nothing is sent outside the machine.
- The tutorial shows prose, an equation and a diagram with no sideways scrolling at 360 px, checked on a real Android phone.
- The build fails if a module imports another module's internals or a query leaves out the organisation filter.
- Memory used by the idle system on an 8 GB, 4-core machine is measured and written in the guide.

### M2 Courses, topic tree and question bank

**Shows:** the admin creates a programme and a course, imports or builds a topic tree with prerequisite links, approves it, and adds questions by hand or by bulk upload.

**Builds:**
- Programme and course screens. The data model supports several programmes.
- Topic and prerequisite tables; a link that would create a loop is refused with a message naming the loop (ADR 0003 item 10).
- Tree editor: add, rename, merge, split, reorder, link prerequisites, approve. A tree can also be imported from a file, so a tree can exist with no model.
- The rule for changing a tree after approval (ADR 0008 section F).
- The status-change log (ADR 0001 item 5).
- Question record: text, options, answer, topics, difficulty level, optional worked solution, where it came from, review status. Add and edit form with maths preview. Bulk upload from a documented template, with an error report row by row (A-6).
- Lessons and questions can be attached only to topics in an approved tree.
- Sample course: the full topic tree for the chosen slice, and a first few questions.
- Guide: admin walkthrough, part 1.

**Covers:** A-1, A-4 (edit and approve), A-6. **Depends on:** M1.

**Done when:**
- The admin can create a programme with two courses and see them listed separately.
- Merge, split, reorder and approve each leave an entry in the status-change log.
- A bulk upload with one bad row imports the good rows and reports the bad one with its reason.
- Starting from an empty database recreates the sample tree and questions identically.
- A non-engineer completes the admin walkthrough without help.

### M3 Mastery and diagnostic as a tested library

**Shows:** nothing on screen. The result is a report from simulated students showing that the diagnostic finds known weak topics on the sample tree, and how many questions per topic and difficulty level the sample course needs.

**Builds:**
- A library with no database and no screens: ratings with uncertainty, the allowance for guessing, the rule for questions linked to several topics, the four labels, calibration versions as input (ADR 0006 items 1 to 8).
- The diagnostic: adaptive walk, inference between linked topics, stop rules, state that can be saved and resumed (items 10 to 13).
- Named settings with defaults, and the rule for running out of questions (items 21, 22).
- The simulated-student harness with a fixed random seed (item 26).

**Covers:** the rules behind S-3, S-4 and T-2, which reach the screen in M6 and M7. **Depends on:** M1, and the sample tree file from M2.

**Done when:**
- Replaying the same answers always gives identical ratings and labels.
- Simulated students of known ability on the sample tree reach all four labels, and no untested topic is ever labelled strong.
- On a fixed test graph, a wrong answer is followed by a question on a prerequisite when one exists.
- The harness states how many questions per topic and level the sample course needs for a five-minute diagnostic, the topic quizzes and one milestone. Sample questions are written to that number.

### M4 Lesson format, source pages and pipeline core

**Shows:** the admin uploads a textbook PDF and sees its pages; three real tutorials (one heavy on derivations, one on diagrams, one a worked numerical problem) read well on a phone.

**Builds:**
- The lesson format completed: every section type, with source pages per section (ADR 0007 item 3).
- The maths check on the server, using the same renderer as the web app (ADR 0008 section C). The reading-time estimate and the 15-minute limit, with a split into ordered sub-topic lessons (V-2).
- The first three diagram templates drawn by code (graph of a function, vectors and forces on a body, labelled diagram) and the cleaner for SVG images (ADR 0007 item 5).
- Source file upload with its type and rights confirmation; the original is kept; a worker job turns each page into an image (A-2). No content is extracted yet.
- The general pipeline core: statuses for each kind of item (ADR 0008 section B), leases that expire, a retry limit, a failed state shown to the admin, steps that are safe to run twice (ADR 0001 items 3, 4). The page-image job is its first user.
- Sample course: the three trial tutorials, each section citing pages of the open textbook.

**Covers:** A-2 (upload, tagging, page images), V-12, V-2, V-1 (sources per section), X-1. **Depends on:** M2.

**Done when:**
- Between them the three trial tutorials use every section type, and equations and diagram labels are legible on a real Android phone at 360 px.
- A maths string the renderer cannot typeset is rejected and the section is named.
- A tutorial over the time limit cannot be saved as one lesson.
- If the worker is stopped part-way, the remaining pages are picked up after the lease expires; running the job twice creates no duplicates; a job that keeps failing stops at the retry limit and is shown as failed.
- An uploaded image containing a script is stored without it.
- The time to prepare page images for the sample textbook slice on the minimum machine is measured and recorded.

### M5 Tutorial editor and review gate

**Shows:** the admin writes or pastes a tutorial with a live preview; the reviewer sees it beside the source pages and approves it, rejects it with a comment, or edits it; only then does a student see it.

**Builds:**
- Tutorial editor with live preview: Markdown and LaTeX; a diagram from template data, an uploaded image or a region cropped from a source page; source pages chosen per section (V-13).
- Lesson versions: an edit creates a new version, and students keep the approved one until the new one is approved (ADR 0004 item 16, ADR 0008 section E).
- Review queue and side-by-side screen: approve, reject with comment, edit text, replace a diagram or edit its data (V-6, ADR 0007 item 9). A section with no source page is marked.
- Question review: approve or reject; a question with no worked solution is marked.
- The publish rule in one place in the content module: other modules can only ask it for published lessons and approved questions (ADR 0001 items 1, 8).
- Withdrawing a published lesson or an approved question (ADR 0008 section E).
- Sample course: tutorials for most topics; a few topics left with questions only; a few items left waiting for review and one rejected with a comment, so the reviewer flow can be shown straight away.
- Guide: admin walkthrough, part 2; reviewer walkthrough.

**Covers:** V-13, V-6, V-5 (question review), V-7 (one lesson at a time), X-3. **Depends on:** M4.

**Done when:**
- A hand-written tutorial is invisible to the student account until the reviewer approves it; an automatic test covers this.
- Editing a published tutorial leaves the old version visible to students until the new one is approved.
- Rejecting with a comment records the comment and the person in the status-change log.
- The review screen shows each section beside the pages it cites, and every sample tutorial section cites at least one page.
- A non-engineer completes the reviewer walkthrough.

### M6 Student lesson, quiz and mastery

**Shows:** the student reads a published tutorial, comes back to where they stopped, takes the quiz that follows, sees worked solutions, and sees their mastery of the topic change.

**Builds:**
- Tutorial reader with progress by section; it reopens at the last section reached (T-1, ADR 0007 item 10).
- Topic quiz from approved questions, with answered, skipped and timed-out outcomes; the worked solution is shown after answering where one exists.
- The attempt record (T-3). Ratings update in the same database transaction, using the M3 library (ADR 0006 item 4).
- A topic list showing the label for each topic: the first form of the gap map.
- Sample course: the question bank written up to the counts from M3.

**Covers:** T-1, T-2, T-3, V-5. **Depends on:** M3, M5.

**Done when:**
- Closing the browser part-way through a tutorial and reopening returns to the last section reached.
- Each answer produces exactly one stored attempt with every field in T-3; a skipped question is stored with its own outcome.
- Replaying the stored attempts in time order reproduces the stored ratings exactly, and matches the M3 library.
- When unseen questions run out, the quiz is shortened, then reuses the oldest-answered questions marked as repeats, and never fails.
- Every screen in this flow works at 360 px.

### M7 Onboarding, diagnostic and gap map

**Shows:** a new student signs up, completes onboarding, takes a five-minute adaptive diagnostic on the sample course (pausing once), and gets a gap map in plain language.

**Builds:**
- Sign-up by email code and the onboarding form (S-2). Sign-ups are closed on a public demo (ADR 0008 section G).
- Diagnostic screens on top of the M3 library: state saved after every answer, resume, and a "retake diagnostic" action.
- Gap map screen with the four labels and a templated summary (ADR 0006 items 8, 24).
- Guide: student walkthrough, part 1.

**Covers:** S-1, S-2, S-3, S-4. **Depends on:** M6.

**Done when:**
- Pausing, closing the browser and resuming continues from the same state and does not count the idle time.
- The same answers against the same calibration version give the same gap map as the M3 library.
- The sample-course diagnostic finishes within its time cap.
- A non-engineer goes from sign-up to gap map on a phone-width browser using the guide.

### M8 Playlist and study plan

**Shows:** from the gap map the student gets an ordered playlist and a dated plan; after a quiz, or a change of weekly hours, the plan changes and the student is told what changed and why.

**Builds:**
- Playlist builder: prerequisites first, topics that are not strong, ranked by gap, dependants and exam weight; "not assessed" treated as developing and kept in syllabus order; three kinds of item: lesson with quiz, practice only marked "lesson coming", and "not yet available" (ADR 0006 items 14, 15, as amended).
- Calendar placement from reading time, quiz time, weekly hours and target date; when the plan does not fit, the lowest-ranked topics are dropped and the student is told (item 16). One course per plan.
- The re-plan job on the queue: its triggers, the daily run, recomputing when the student opens the plan, one at a time per student, the same result if run twice (item 17).
- Reason codes and templated "what changed and why" notes (items 19, 24). Storage for the student's pins and skips, kept apart from the computed plan (item 18; the screens for them are P1).
- Each plan records the calibration version it used; the sample course has a fixed version (item 5).
- Harness scenarios: falling behind, a change in mastery, a change in hours.
- Guide: student walkthrough, part 2.

**Covers:** P-1, P-2, P-3. **Depends on:** M7.

**Done when:**
- No playlist item ever comes before one of its prerequisites (tested over many random graphs).
- Only published lessons and approved questions appear; a topic with questions but no lesson appears as practice only.
- Changing weekly hours produces a new plan and a visible note with the reason.
- Moving the clock past an unfinished item's date and opening the plan shows it re-planned, even if no daily run happened.
- Running the re-plan twice gives an identical plan, and a stored skip survives it.
- A plan that cannot fit before the target date names the topics that were dropped.

### M9 Milestones, reports, dashboard and the demo student

**Shows:** the demo student account opens part-way through a plan with a completed milestone and its report. The presenter takes a new milestone built for that student, sees the report and the plan react, moves the date forward to show falling behind, and resets everything.

**Builds:**
- Milestone placement and assembly by rule; a milestone opens when its topics are complete; exam format settings per course (T-4, ADR 0006 item 20).
- Milestone report from templates; a re-plan when a milestone is completed (T-6).
- Student dashboard: progress through the plan, mastery by topic, score trend, time spent, next milestone (T-5).
- The question calibration job, producing numbered versions (ADR 0006 item 5).
- Demo student history made by the harness (item 27). Demo-mode controls: "reset demo data", which restores content, review queue, accounts, history and files, and "move the date forward" (ADR 0008 section G).
- A simulated-student test on the finished sample course: all four labels and a milestone with questions can be reached (item 23).
- Guide: the complete student script for one sitting.

**Covers:** T-4, T-5, T-6, X-8. **Depends on:** M8.

**Done when:**
- Two simulated students with different weak topics get different milestones over the same studied topics, each weighted towards their own weak ones.
- The milestone report names the same topics and numbers as the stored results.
- The dashboard shows all five items in T-5 for the demo student.
- After any amount of demo use, reset restores the starting state exactly, including the review queue and stored files.
- A non-engineer shows the whole student flow in one sitting, with no network, using the guide.

### M10 Uploaded video lessons

**Shows:** the admin uploads a finished video for a topic; it passes the same review gate; the student sees the tutorial first and the video after it, with the quality adjusting to the connection.

**Builds:**
- Video upload for an approved topic, with rights confirmation and optional source pages; the original is kept (V-11, ADR 0004 section B).
- A worker job on the M4 pipeline core: check the file, measure its length, refuse it above the limit with a message asking for a split, encode to HLS at configurable quality levels, one job at a time.
- Optional caption file and chapter times; a "no captions" mark on the review screen. The reviewer can approve or reject; a replacement file is a new version.
- Player with automatic quality, captions and resume; progress by position watched.
- The rule for a topic that has both a tutorial and a video (ADR 0008 section D).
- One short sample video with clear rights.
- Guide: upload-a-video walkthrough.

**Covers:** V-11, V-2, X-2, T-1 (video). **Depends on:** M8.

**Done when:**
- A video over the limit is refused, and an uploaded video is not visible to students until approved.
- On a simulated 3G connection a 10-minute video starts and plays through at the lowest quality.
- Leaving and returning resumes at the stored position.
- Running the encoding job again for the same file creates no duplicates; a failing job stops at the retry limit and is shown as failed.
- Encoding time per minute of video, and how the app responds while encoding, are measured on the minimum machine and recorded.

### M11 MVP demo release

**Shows:** stage 1 is complete. A non-engineer starts the product on their own computer and on a cheap public server from the written guide, and shows the admin, reviewer and student flows with the included sample data.

**Builds:**
- Packaging: images for Intel/AMD and ARM processors; their sizes and the minimum computer stated in the guide; the sample course's files loaded into the object store on first start with no internet.
- Public demo (hosting step 2 in ADR 0002): the same Compose file on one small server with a domain name and automatic HTTPS; demo mode with an access code, sign-ups closed, a "sample data only" banner, and the mail viewer not reachable from the internet. The minimum server size and its monthly cost are stated after testing. A scheduled copy of the database, with restore steps in the guide.
- Installable web app; opened tutorials stay available offline (ADR 0007 item 13); the app is split and cached to speed up the first load.
- With no model provider, every "generate" action is refused with a plain message (ADR 0005 item 2).
- The guide completed: two routes (own computer, public server); setup, start, stop, update, reset, restore and common problems; three persona scripts in which every stage 1 requirement has a line that shows it.
- Automatic end-to-end tests of the three persona scripts against the running system.
- Licence and attribution page for the sample content; the sample course is frozen.

**Covers:** X-8, X-7, X-1, X-2. **Depends on:** M9, M10.

**Done when:**
- Someone outside the team, using only the guide, starts the product on an 8 GB, 4-core Windows PC with WSL 2 and completes all three persona scripts. This is repeated until a run needs no help.
- The same person brings up the public demo, and a second person enters it from a phone on mobile data.
- Every running component is free or open source and no model provider is configured.
- The public demo refuses new sign-ups and cannot be entered without the access code.
- A tutorial opened once reopens in the installed app with the network off.
- A restore from the scheduled database copy has been carried out once by following the guide.

## Stage 2 — Generated tutorials

### M12 PDF extraction with the free local parser

**Shows:** the admin uploads a textbook PDF, including a scanned one, and sees the status of each page, the extracted text, equations, figures and tables, and a list of pages the system could not read.

**Builds:**
- The extractor interface and the shared block format, with the origin of every block (ADR 0003 items 2 to 4).
- The free open-source parser run locally, with text recognition for scans and the cross-check against embedded text.
- Joining of blocks that continue across pages (item 5); a confidence flag per page; the admin status screen; re-running a single page (item 6).
- Extraction runs as its own optional worker, so the default demo neither downloads nor loads it. The sample course is included already extracted.
- Assigning blocks to topics by chapter or page range, without a model. The review screen shows blocks as well as pages.
- Guide: uploading a PDF, and how long it takes on the minimum computer.

**Covers:** A-2 (scanned PDFs), A-3, V-1. **Depends on:** M11.

**Done when:**
- A PDF with embedded text and a scanned PDF both complete, with a status on every page.
- Deliberately poor pages are listed for the admin as unreadable or low confidence.
- A derivation that crosses a page break becomes one block citing both pages.
- Running extraction again on the same file creates no duplicate blocks; stopping the worker part-way leaves the remaining pages to be picked up.
- Extraction runs with no model provider and no internet, and the default demo's download size and memory use are unchanged.

### M13 Model gateway, checks, proposed tree and past papers

**Shows:** with a free or paid provider configured, the system proposes a topic tree with prerequisites for the admin to edit and approve, and turns a past-paper PDF into individual questions linked to topics for the admin to correct.

**Builds:**
- The gateway: tasks, adapters for "none", free and paid modes, stored results by key, retries only for passing errors, validated structured output, a log of prompt version, inputs and outputs (ADR 0005 items 1 to 3).
- Cost recording per call; spend limits per day and per course; the paid adapter refuses to start without a limit; a rate limit for free tiers (item 9).
- The checks that need no model, including the restricted arithmetic evaluator, tested with hostile input (item 5, Group A).
- The evaluation set, started with 5 to 10 sample topics approved by the subject expert, and a runner that compares a change of prompt or model with the previous result (item 8).
- The embedding task with a small local model, loaded only in this configuration (ADR 0008 section A).
- The vision-model extractor behind the M12 interface; choice of extractor per page; the comparison of the two extractors on sample pages, with the result written into ADR 0003.
- Topic tree proposal, arriving in the M2 editor as a proposal; automatic assignment of blocks to topics (ADR 0003 items 9, 11).
- Past-paper parsing into question records with a confidence value, a correction queue, and exam weight per topic (item 12). It is tested on a past paper with clear rights, or on a mock paper written for the purpose.
- Guide: how to configure free and paid mode, and what each costs.

**Covers:** A-4 (the system proposes), A-5, X-3, X-7. **Depends on:** M12.

**Done when:**
- With no provider, every "generate" action is refused with a plain message and nothing changes status.
- A repeated call with the same key returns the stored result and records no new usage.
- Invalid or cut-off model output never reaches a pipeline item (tested with a faulty stand-in adapter).
- Reaching the spend limit pauses the jobs and shows the reason on the admin screen.
- The evaluator rejects every expression outside its restricted form.
- A proposed tree for the sample book can be edited and approved in the existing editor, and nothing further runs before approval.
- A test past paper yields questions linked to topics; the uncertain ones appear in the correction queue and corrections are saved.

### M14 Generated tutorials and questions

**Shows:** for an approved topic the admin presses "generate" and gets a tutorial with diagrams and practice questions with worked solutions. Every section cites its source pages, and the check results are shown to the reviewer. One lesson, or one section, can be regenerated alone.

**Builds:**
- The `write_tutorial` task, producing the M4 lesson format from the topic's blocks, with the grounding rules (ADR 0005 item 4, ADR 0007 item 7). Length planning and the split into sub-topic tutorials.
- Diagrams in order of preference: the source figure; the remaining three templates (concept map, number line or axis, simple circuit); an image written by the model, behind a switch, cleaned and marked for the reviewer (ADR 0007 item 5).
- The `write_questions` and `write_solution` tasks. Past-paper questions and uploaded questions with no solution get one; a solution that disagrees with a stored answer key is flagged (ADR 0005 item 6).
- The model-based checks, set to off, sampled or full: the independent check, and the blind solve on every question including uploaded ones. A disagreement on a past-paper question flags its answer key. The failure rules (item 5, Group B).
- Review screen: warnings beside sections and questions, which checks ran, regenerate one section or the whole lesson, a warning before regenerating over hand edits. Reviewer decisions are stored.
- Stored model results are cleared when a prompt version is retired.
- Measurements written into ADRs 0005 and 0007: first-review approval rate against 70%, share of diagrams drawn by the model against 10%, review time and cost per lesson.
- Sample course: a few topics generated in free mode and kept as examples. Guide: the generate, review, publish flow.

**Covers:** V-1, V-5, V-7, V-2, V-6, V-12, X-3. **Depends on:** M13.

**Done when:**
- Every section of a generated tutorial cites at least one block that was supplied, and the review screen opens those pages beside it.
- Regenerating one lesson changes no other lesson's content, version or status.
- A question whose stated answer differs from the recomputed one is regenerated or marked failed, never shown as clean.
- A model-written image containing a script or an outside link is stored without it and is marked on the review screen.
- A generated tutorial is invisible to students until approved, and flagged questions are not used in any quiz, diagnostic or milestone.
- Every published lesson in the sample course has practice questions, each with a worked solution.

## Pilot readiness — before real students

### M15 Privacy, consent and accounts

**Shows:** an under-18 student cannot get an account without recorded parental consent; a student's data can be deleted; staff are invited with a role; a student can report a mistake in a lesson.

**Builds:**
- The legal advice applied: age asked at sign-up; the parental consent flow in the form the advice requires, or the pilot limited to 18 and over (PRD open question 6); the consent record (S-6).
- Deletion of one student's data; how long history is kept; privacy notice; a log of staff reading student data; a check that student pages carry no third-party tracking (X-4).
- Sign-ups by real students are opened only once the above is in place.
- Inviting a staff member as admin or reviewer.
- "Report a mistake" on a lesson, going to the reviewer queue (V-9, if it is raised to this stage).
- Phone one-time code, if it is decided that the pilot needs it (S-1). The decision on whether an email or phone number is unique across organisations (ADR 0001 open point).

**Covers:** S-6, X-4 (controls), S-1 (phone, if decided). **Depends on:** M11, and the legal advice being in hand. It can run alongside stage 2.

**Done when:**
- Written legal advice is on file, and each point in it is matched by a control in the product or a recorded decision.
- An under-18 sign-up cannot create an account without recorded consent.
- One student's data can be deleted on request, and the deletion is checked.
- A log entry exists for every staff read of student data.

### M16 India hosting, scale and pilot content

**Shows:** the product runs in an Indian region on managed services, has been tested with 500 students at once, and has reviewed pilot content published.

**Builds:**
- Hosting step 3 defined with Terraform, AWS Mumbai by default: managed containers, managed PostgreSQL, object storage with a content delivery network, encryption in transit and at rest, backups (ADR 0002). Moving from step 2 changes configuration only.
- A response-time target set before the load test; a load test at 5,000 registered students and 500 at once (X-5).
- Monitoring, error reporting and notes for whoever operates it.
- The extractor comparison run again on real pilot pages once rights are settled (ADR 0003 item 3). The evaluation set grown to a few dozen topics (ADR 0005 item 8).
- The harness run on the pilot-sized topic graph, to set the diagnostic's time cap (target 15 to 20 minutes, S-3) and the number of questions needed per topic.
- The pilot course generated, reviewed and published. Paid mode is used only if the rights allow source text to leave India; otherwise a locally run model.
- The measures in PRD section 9 can be read from the system.

**Covers:** X-4, X-5, S-3 (pilot settings), and the content targets in PRD section 9. **Depends on:** M14, M15, and content rights being settled.

**Done when:**
- Every store of student data, and every backup, is in an Indian region and encrypted.
- The load test report shows the response-time target met with 500 students at once.
- A restore from backup has been carried out in this environment.
- At least 95% of pilot topics have a published lesson, or the gap is listed and accepted by the owner.
- A rights confirmation is stored for every pilot source file.

## Stage 3 — after the first release

### M17 Generated video

**Shows:** a narrated video with captions, transcript and chapters is rendered from a topic's lesson content and passes the same review gate.

**Builds:** everything in ADR 0004 section C: the scene specification made from the tutorial, the checks before rendering, the Manim templates, the free local voice after the listening test, scene caching and re-rendering of one scene, assembly and encoding in a separate render worker, and the cost record. Hindi narration (V-8) is not planned here.

**Covers:** V-3, V-4, V-10 (recording). **Depends on:** M16. Whether and how far to build it is decided from the pilot's results for tutorial-only topics against topics with video.

**Done when:** a sample topic with a published tutorial gets a generated video that passes review; editing one scene re-renders only that scene; no video is longer than 15 minutes.

## Decisions needed

The build is proceeding on the recommended answer to each (owner's go-ahead, 2026-11-16). They remain open to change; a different answer changes the milestone named.

| # | Question | Recommended answer | Affects |
|---|---|---|---|
| 1 | Accept [ADR 0008](adr/0008-consistency-after-0007-and-demo-mode.md)? It settles statuses, how maths is checked, a topic with both a tutorial and a video, new versions and withdrawal, changing an approved tree, and demo mode. | Accept | M1, M4, M5, M9, M10, M11 |
| 2 | Is an email code enough for sign-in in the first release (PRD S-1 says phone or email)? | Yes. Add the phone code before the pilot only if it proves necessary. | M1, M15 |
| 3 | Should the PRD name pilot readiness (consent, India hosting, scale) as a gate after stage 2? Today it says stage 2 completes the first release. | Yes | M15, M16 |
| 4 | May a question with no worked solution be published in stage 1 (PRD V-5 says every question has one; A-6 makes it optional)? | Yes, marked for the reviewer. Required for every published question from stage 2. | M5, M14 |
| 5 | Separate admin and reviewer roles are P1 (A-8), but the review gate needs them. | Three fixed roles from M1. Inviting staff is built in M15. | M1, M15 |
| 6 | PRD X-8 lists three ways to run it: laptop, Docker, cheap hosting. ADR 0002 makes the laptop route Docker. | Two routes in the guide: own computer with Docker, and a public server. No route without Docker. | M1, M11 |
| 7 | Should the MVP demo show PDF extraction? The free parser needs no model. | No: keep it as M12. Move it before M11 only if the admin demo must show it. | M11, M12 |
| 8 | "Error reports per 100 lessons" is a pilot measure, but reporting a mistake (V-9) is P1. | Build V-9 in M15. | M15 |
| 9 | Can a student's plan cover one course in the first release? The data model supports several. | Yes | M8 |
| 10 | Which chapters of the open textbook form the sample course? | Needs the owner or the subject expert. | M2 |

## Left out of this plan

| Requirement | Priority | Note |
|---|---|---|
| S-5 skip the diagnostic | P1 | |
| P-4 ordering by exam weight | P1 | The weight is stored from M13 and the ranking already accepts it. |
| P-5 pin, skip, reorder | P1 | Storage exists from M8; no screens. |
| P-6 spaced revision | P1 | Uncertainty grows with time from M3; no revision checks are scheduled. |
| T-7 mock tests, T-8 admin dashboard | P1 | |
| V-8 Hindi | P1 | |
| V-10 cost screen | P1 | Cost is recorded from M13. |
| A-7 new editions, T-9 export | P2 | |
| X-6 offline video | P2 | Opened tutorials are available offline from M11. |

## Main risks

| Risk | Where it is handled |
|---|---|
| The guide fails for a real non-engineer (Windows, WSL 2, Docker, an 8 GB machine) | Tested by an outsider in every stage 1 milestone; measured on the minimum machine in M1, M4, M10 and M11 |
| The sample course has too few questions for one sitting | M3 sets the counts before the questions are written; M9 tests the finished course |
| Writing the sample tutorials and questions takes longer than the code | Content is written a few topics at a time from M4; a topic with no lesson is a designed state |
| The review gate or the organisation filter is bypassed by a later feature | Automatic tests from M1 and M5, run on every change |
| A worker stops part-way and leaves items stuck or duplicated | Lease, retry and run-twice tests in M4, before encoding (M10) and extraction (M12) rely on them |
| The public demo server is too small, or collects real people's data | Size and cost are measured in M11; demo mode closes sign-ups and needs an access code |
| The free local parser is slow or wrong on equations and scans | Measured in M12; compared with the vision model in M13; repeated on real pages in M16 |
| Free-mode models write poor tutorials, or free limits block generation | Stored results and rate limits in M13; checks, the evaluation set and the review screen in M14; paid mode by configuration |
| Legal advice restricts the history the learner model depends on | Requested now; attempts are stored so ratings can be rebuilt; deletion in M15 |
| Content rights for the pilot books are not obtained | Stages 1 and 2 use the openly licensed sample textbook; rights gate M16 |
| Students engage less with reading than with video | Uploaded video from M10; lesson completion measured in M16; generated video in M17 |

## Not yet known

- **Sizes and speeds.** No memory, disk, encoding-time or extraction-time figure has been measured. The smallest server that can run the public demo is unknown until M11; a free-tier server may be too small for video encoding.
- **Free parser quality** on equation-heavy and scanned pages is untested until M12.
- **Free-mode model quality** for tutorials and questions is untested until M13 and M14.
- **Cost per generated lesson** in paid mode is measured in M14, not estimated here.
