# PRD: AI Learning Management System (working name: "AI-LMS")

| | |
|---|---|
| **Status** | Draft — awaiting approval |
| **Version** | 0.1 |
| **Date** | 2026-11-16 |
| **Next step after approval** | Architecture Decision Records in `docs/adr/` |

---

## 1. Summary

AI-LMS turns the source material a student is already supposed to study (textbooks, syllabus, previous years' question papers) into short, topic-wise videos, then gives each student a personal playlist and study plan based on what they do not yet know. It measures progress through regular assessments and adjusts the plan as the student improves.

Target learners: school students (classes 6–12), undergraduates, and students preparing for Indian competitive exams such as IIT-JEE and NEET.

## 2. Problem

- **One pace for everyone.** Classrooms and recorded coaching lectures move at a single speed. A student who is weak in one prerequisite (say, vectors) falls behind in everything built on it (mechanics, electrostatics) and nobody notices until an exam.
- **Too much content, no map.** Students have plenty of videos and books available. What they lack is knowing which topic to study next and when they have studied it enough.
- **Long lectures.** Typical coaching lectures run 60–90 minutes. Students cannot find the ten minutes they actually need.
- **Weak feedback.** Test scores arrive as a total mark, not as "you are weak in rotational dynamics because you are weak in torque".
- **Cost of content production.** Making good video lessons for every topic of every subject, board and exam by hand is slow and expensive, which is why smaller institutes cannot do it.

## 3. Goals and non-goals

### Goals

1. An admin can upload source PDFs for a course and get a structured topic tree without building it by hand.
2. The system produces a reviewed video of 15 minutes or less for every topic (or sub-topic, where a topic is too large).
3. A new student gets a personal playlist within one session: sign up, pick a course, take a short diagnostic, start watching.
4. Every assessment result is stored and feeds a per-topic picture of what the student has mastered.
5. The study plan contains milestone evaluations that adapt to the student's current level.

### Non-goals (for the first release)

- Live classes, teacher-led sessions, or doubt-solving with human tutors.
- Subjective answer grading (essays, long derivations written by hand). First release grades objective questions only.
- Discussion forums, chat between students, or other social features.
- Payments, subscriptions and institute billing.
- Native mobile apps. First release is a responsive web app that works on a phone browser.
- Building our own video-generation or speech models. We use existing ones.

## 4. Users

| Persona | Who they are | What they need |
|---|---|---|
| **Admin / content manager** | Staff of the institute or platform operator. Knows the subject or works with someone who does. | Upload material, check what the AI produced, fix mistakes, publish. |
| **Student** | Class 6–12, undergraduate, or JEE/NEET aspirant. Often studies on a phone, sometimes on a slow connection. Many are under 18. | Know what to study next, learn it in short sittings, see proof of progress. |
| **Reviewer / subject expert** (may be the same person as admin) | Teacher who approves content before students see it. | A fast way to check a video and its questions against the source and approve or reject. |

Later personas, out of scope now: parent (progress reports), teacher (class-level view).

## 5. How it works (end to end)

```
Admin uploads PDFs ──► AI builds topic tree ──► Admin reviews tree
                                                      │
                          AI writes script + questions per topic
                                                      │
                               AI renders video ──► Reviewer approves ──► Published
                                                                              │
Student signs up ──► picks course ──► diagnostic quiz ──► gap map ──► playlist + study plan
                                                                              │
                         watch video ──► topic quiz ──► mastery updated ──► plan adjusts
                                                                              │
                                                           milestone evaluation ──► report
```

## 6. Requirements

Priority: **P0** = required for first release, **P1** = soon after, **P2** = later.

### 6.1 Admin: content and course setup

| ID | Requirement | Priority |
|---|---|---|
| A-1 | Create a **course** defined by board/exam, class/year and subject (for example "CBSE Class 11 Physics", "JEE Main Physics"). A **programme** groups several courses (for example "NEET" = Physics + Chemistry + Biology). | P0 |
| A-2 | Upload PDFs and tag each as textbook, syllabus, previous years' questions (PYQ), or other reference. Scanned PDFs must work (text recognition). | P0 |
| A-3 | The system extracts text, equations, figures and tables from each PDF and shows the admin the processing status and any pages it could not read. | P0 |
| A-4 | The system proposes a **topic tree** (subject → chapter → topic → sub-topic) with prerequisite links between topics, aligned to the syllabus where one is uploaded. The admin can edit, merge, split, reorder and approve it. | P0 |
| A-5 | PYQs are parsed into individual questions with options, answer, and the topic(s) they belong to. Admin can correct the mapping. | P0 |
| A-6 | Admin can add questions by hand or by bulk upload. | P1 |
| A-7 | When a newer edition of a book is uploaded, the system shows which topics changed and which videos need regenerating. | P2 |
| A-8 | Roles: admin and reviewer, with separate permissions. | P1 |

### 6.2 AI video generation

| ID | Requirement | Priority |
|---|---|---|
| V-1 | For each approved topic, generate a lesson script grounded only in the uploaded source material. Every section of the script records which pages of which source it came from. | P0 |
| V-2 | Render the script into a video of **15 minutes or less**. If a topic needs longer, the system splits it into sub-topic videos and keeps them in order. | P0 |
| V-3 | Video format: narrated explainer with slides, worked examples, diagrams and step-by-step equations. (No requirement for a human-looking presenter.) | P0 |
| V-4 | Each video has captions, a transcript and chapter markers. | P0 |
| V-5 | Each video comes with a set of practice questions on the same topic (generated and from PYQs), each with a worked solution. | P0 |
| V-6 | **Review gate:** nothing is visible to students until a reviewer approves it. Reviewer sees the video, the script and the source pages side by side, and can approve, reject with comments, or edit the script and re-render. | P0 |
| V-7 | Admin can regenerate a single video without touching the others. | P0 |
| V-8 | Languages: English first. Hindi and mixed Hindi-English narration next. | P1 |
| V-9 | Students can report a mistake in a video; reports go to the reviewer queue. | P1 |
| V-10 | Admin sees generation cost and time per video and per course. | P1 |

### 6.3 Student: onboarding and diagnostic

| ID | Requirement | Priority |
|---|---|---|
| S-1 | Sign up and log in with phone number (one-time code) or email. | P0 |
| S-2 | Onboarding collects: name, class/year, board or target exam, subjects, target exam date (if any), and hours available per week. | P0 |
| S-3 | A **diagnostic assessment** per subject finds gaps. It is adaptive: the next question depends on earlier answers, and a wrong answer leads to a check of the prerequisite topic. Target length 15–20 minutes per subject; the student can pause and resume. | P0 |
| S-4 | The result is a **gap map**: every topic marked as not assessed, weak, developing or strong, shown to the student in plain language. | P0 |
| S-5 | Student can skip the diagnostic and start from the beginning of the syllabus; the system then learns their level from topic quizzes. | P1 |
| S-6 | For users under 18, collect verifiable parental consent before creating the account (see section 8). | P0 |

### 6.4 Playlist and study plan

| ID | Requirement | Priority |
|---|---|---|
| P-1 | Generate a **curated playlist** from published videos: weak topics first, prerequisites before the topics that depend on them, strong topics left out or offered as optional revision. | P0 |
| P-2 | Turn the playlist into a dated **study plan** using the student's weekly hours and target exam date. | P0 |
| P-3 | The plan updates when the student's mastery changes, when they fall behind, or when they change their available hours. The student is told what changed and why. | P0 |
| P-4 | For competitive-exam courses, ordering also takes account of how often a topic has appeared in previous years' papers. | P1 |
| P-5 | Student can pin, skip or reorder items; the system warns if a skipped topic is a prerequisite for a later one. | P1 |
| P-6 | Spaced revision: topics already mastered come back for a short check after a gap. | P1 |

### 6.5 Progress tracking and assessment

| ID | Requirement | Priority |
|---|---|---|
| T-1 | Track video progress (started, percentage watched, completed) and resume from where the student stopped. | P0 |
| T-2 | A short **topic quiz** follows each video. The result updates the student's mastery of that topic. | P0 |
| T-3 | Store every attempt permanently: question, answer given, whether correct, time taken, date. | P0 |
| T-4 | **Milestone evaluations** are placed in the study plan (for example at the end of each unit). Each one is built for that student: it covers what they studied since the last milestone, with more questions on topics where they were weak. | P0 |
| T-5 | Student dashboard: progress through the plan, mastery by topic, score trend, time spent, next milestone. | P0 |
| T-6 | After each milestone, the student gets a report: what improved, what is still weak, and what the plan will do about it. | P0 |
| T-7 | Full-length mock tests in the real exam pattern (JEE Main, NEET: timing, marking scheme including negative marks). | P1 |
| T-8 | Admin dashboard: active students, completion rates, topics where most students struggle, videos with high drop-off. | P1 |
| T-9 | Student can export their own results. | P2 |

### 6.6 Requirements that apply across the product

| ID | Requirement | Priority |
|---|---|---|
| X-1 | **Phone first.** Every student screen works on a 360 px wide phone browser. | P0 |
| X-2 | **Slow networks.** Video plays at several quality levels and switches automatically; a 10-minute video is watchable on a 3G connection. | P0 |
| X-3 | **Accuracy.** Generated content must be traceable to source pages (V-1) and approved by a human (V-6). | P0 |
| X-4 | **Privacy.** Student data is stored in India, encrypted, and never used for advertising. | P0 |
| X-5 | **Scale for first release:** 5,000 registered students, 500 using it at the same time. | P0 |
| X-6 | Offline download of videos. | P2 |

## 7. First release scope

Building every board, class and exam at once would spread effort thin and make content quality impossible to check. The recommendation is a **pilot on one programme**:

> **Recommended pilot: JEE Main — Physics, Class 11 syllabus.**
> Reasons: the syllabus is well defined, many years of objective-type past papers exist for diagnostics and quizzes, and physics exercises the hardest parts of video generation (equations, diagrams, worked numerical problems). If it works here, simpler subjects will follow.

Everything marked P0 above is in the first release. The data model must support multiple programmes from day one even though only one is populated.

## 8. Risks and constraints

| Risk | Why it matters | Mitigation |
|---|---|---|
| **Copyright of uploaded material** | Textbooks (including NCERT) and coaching-institute material are copyrighted. Generating and distributing videos derived from them may need a licence, particularly for commercial use. | Admin must confirm rights for each upload (stored with the file). Legal review before launch. Prefer openly licensed or licensed-in sources for the pilot. |
| **Factual errors in generated lessons** | A wrong formula or solution taught to thousands of students damages trust and exam results. | Source grounding (V-1), human review gate (V-6), student error reports (V-9), automatic checking of numerical answers. |
| **Children's data** | Many users are under 18. India's Digital Personal Data Protection Act, 2023 requires verifiable parental consent for minors and restricts tracking and targeted advertising aimed at them. Progress tracking is the core of this product, so this needs legal advice early. | S-6, X-4, legal review of what tracking is permitted and on what basis; collect the minimum data needed. |
| **Video generation cost and time** | A full course is hundreds of videos. Cost per video decides whether the product is viable. | Measure cost per video in the pilot (V-10); generate only for approved topics; regenerate single videos, never whole courses. |
| **Poor PDF extraction** | Scanned pages, equations and diagrams are hard to read correctly; errors here flow into every later step. | Show unreadable pages to the admin (A-3); admin approves the topic tree before any video is generated (A-4). |
| **Diagnostic too long or inaccurate** | Students drop out of long tests; a bad gap map produces a bad playlist. | Adaptive test with a time cap (S-3); mastery keeps updating from topic quizzes after onboarding. |
| **Reviewer becomes the bottleneck** | Every video needs approval. | Side-by-side review screen (V-6); measure review time per video; target under 10 minutes. |

## 9. Success measures

| Area | Measure | Target for pilot |
|---|---|---|
| Content | Topics in the pilot syllabus with a published video | 95% or more |
| Content | Videos approved on first review without edits | 70% or more |
| Content | Confirmed student error reports per 100 published videos | Fewer than 2 |
| Onboarding | Students who finish the diagnostic after starting it | 80% or more |
| Engagement | Students active in week 4 after signing up | 40% or more |
| Engagement | Average video completion | 70% or more |
| Learning | Improvement in score on weak topics between diagnostic and first milestone | 20 percentage points or more |
| Operations | Time from PDF upload to first published video | Under 2 working days |

Targets are starting assumptions to be revised once pilot data exists.

## 10. Open questions

These need a decision from the product owner. The PRD currently assumes the recommended answer.

1. **Pilot segment.** JEE Main Physics Class 11 (recommended), or a different exam, class or subject?
2. **Who operates it?** A single platform we run ourselves (assumed), or software sold to many institutes, each with its own admins, content and students? This changes the data model and is expensive to change later.
3. **Video style.** Narrated slides with animated diagrams and equations (assumed), or a human-like presenter/avatar? The second costs considerably more per video.
4. **Languages at launch.** English only (assumed), or English and Hindi together?
5. **Content rights.** Which books and papers do we have, or can we get, the right to use for the pilot?
6. **Under-18 users.** Allowed in the pilot with parental consent (assumed), or restrict the pilot to 18 and over to defer the consent flow?
7. **Question generation.** May the diagnostic and milestones use AI-generated questions after review (assumed), or only past-paper and admin-written questions?

## 11. Glossary

- **Course** — one subject at one level for one board or exam.
- **Programme** — a set of courses a student prepares for together (for example NEET).
- **Topic tree** — the hierarchy of subject, chapter, topic and sub-topic, with prerequisite links.
- **Gap map** — a student's mastery level for every topic in their courses.
- **Mastery** — the system's estimate of how well a student knows a topic, updated after every assessment.
- **PYQ** — previous years' questions from real exam papers.
- **Milestone evaluation** — a test placed in the study plan and built for the individual student.
