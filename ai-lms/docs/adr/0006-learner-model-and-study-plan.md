# ADR 0006: Learner model, diagnostic and study plan

| | |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-11-16 |
| **PRD requirements** | S-3, S-4, S-5, P-1 to P-6, T-2 to T-6, X-7, X-8, section 8 (diagnostic length, children's data) |
| **Amended by** | [ADR 0007](0007-text-tutorials-as-primary-lesson-format.md): "published video" in items 14 and 16 reads "published lesson" of any format. [ADR 0008](0008-consistency-after-0007-and-demo-mode.md) (proposed): wording of items 14 and 16, a topic with both a tutorial and a video, what "reset demo data" restores (item 28) |

## Context

The product's promise to the student is: we find what you do not know, tell you what to study next, and show you that you are improving. That requires four things to work together: an estimate of mastery per topic, a short diagnostic that produces a first estimate (S-3), a playlist and dated plan built from it (P-1, P-2), and milestone tests built for the individual (T-4).

There is no student data yet. Whatever method we choose must work from the first student, with questions whose difficulty has not been measured, and must be explainable to a student ("why is this in my plan?", P-3).

This is also the part of the product the MVP demo shows most (X-8). It must work on a small sample course where only a few topics have videos, with no language model, and it must be possible to show the whole student flow in one sitting.

## Decision

**Mastery, question selection and planning are computed by deterministic algorithms over the topic graph. Language models are not used to judge what a student knows or to decide what they study.**

### Mastery estimate

1. **A rating per student per topic, and a rating per question**, in the style of the Elo system used in chess: answering a hard question correctly raises the student's topic rating a lot, missing an easy one lowers it a lot.
2. **Each student rating carries an uncertainty value**, in the style of the Glicko system. It shrinks with each answer and grows with the days since the topic was last practised. The growth is calculated when the rating is read, from the last-practised time; no scheduled job writes it. This drives revision (P-6).
3. **Guessing is allowed for.** The expected chance of a correct answer has a floor of 1 divided by the number of options, so a lucky guess on a multiple-choice question moves the rating less.
4. **Student ratings update immediately**, in the same database transaction that stores the attempt.
5. **Question ratings update in versions, not live.** They are recalculated from the stored attempts, in time order, by a periodic job on the PostgreSQL queue, and published as a numbered calibration version. A question keeps its starting estimate until it has a configured minimum number of answers. Each plan records the calibration version it used. The sample course ships with a fixed version that demo use does not change.
6. **Starting values**: questions start from a difficulty estimate (past-paper questions by exam level, generated or uploaded questions by the level given; a missing level means neutral); students start at a neutral rating with high uncertainty.
7. **Questions linked to several topics** update each linked topic. The diagnostic uses single-topic questions only.
8. **The gap map (S-4)** translates rating and uncertainty into four labels: not assessed, weak, developing, strong.
9. **Every attempt is stored unchanged** (T-3): question, answer, correctness, time taken, timestamp. A skipped or timed-out question is stored as an attempt with its own outcome. Ratings can always be recomputed from this history if the method changes.

### Diagnostic

10. **Adaptive walk over the prerequisite graph.** Start with questions on topics in the middle of the course. A wrong answer moves towards that topic's prerequisites; a right answer moves towards topics that depend on it. Each next question is chosen to reduce uncertainty the most.
11. **Inference between linked topics.** Clear strength in an advanced topic raises the estimate of its prerequisites; clear weakness in a prerequisite lowers the estimate of topics that depend on it. Inferred values are recomputed from direct evidence each time, are never stored as attempts, keep high uncertainty until tested directly, and cannot by themselves produce the label "strong".
12. **Stops** when the time cap is reached (S-3), when uncertainty is low enough across the course, or when no unseen question remains that would reduce uncertainty. Untested topics are labelled "not assessed", never guessed as strong.
13. **Pause and resume.** Diagnostic state (questions asked, answers, active time) is saved after every answer. Resuming continues from it; the time cap counts active time only; an abandoned diagnostic still produces a gap map from what was answered.

### Playlist and study plan

14. **Only published videos and reviewer-approved questions are used** (V-6, P-1). For each topic that is not strong:

    | The topic has | It appears as |
    |---|---|
    | A published video | A video item followed by its topic quiz |
    | Approved questions but no published video | A practice-only item (topic quiz and source page reference), marked "video coming" |
    | Neither | "Not yet available", left off the calendar |

    The diagnostic and gap map cover every topic that has approved questions, whether or not it has a video.
15. **Playlist = ordered list of topics** produced by sorting the prerequisite graph so prerequisites come first, filtered to topics that are not strong, and ranked by a score combining size of gap, number of later topics that depend on it, and exam weight (ADR 0003, P-4; a missing exam weight counts as zero). A "not assessed" topic is treated as "developing" and kept in syllabus order.
16. **Study plan = playlist placed on a calendar** using video length, expected quiz time, the student's weekly hours and target date (P-2). Practice-only items use expected quiz time only. If the plan does not fit, lowest-ranked topics are dropped first and the student is told.
17. **Re-planning is a job on the PostgreSQL queue** (ADR 0002), run by the existing worker. It is queued when:
    - a quiz or milestone is completed;
    - the student changes weekly hours or target date (P-3);
    - a planned item passes its date unfinished.

    A periodic task of the same queue runs it daily for students with an overdue item; no separate scheduler service is used. If the daily run was missed, for example because the machine was off, the plan is recomputed when the student next opens it. At most one re-plan runs per student at a time, and running it twice gives the same plan (ADR 0001).
18. **Student choices survive a re-plan.** Pins, skips and reorders (P-5) are stored separately from the computed plan and kept. If a skipped topic is a prerequisite of a later item, a warning is shown.
19. **Every plan change is stored with a structured reason code** (P-3), for example "moved earlier: quiz showed weakness in a prerequisite".
20. **Milestone evaluations (T-4)** are assembled by rule: cover topics studied since the last milestone, give more questions to topics with lower rating or higher uncertainty, avoid questions the student has seen, and match the exam's format. A milestone becomes available when its covered topics are complete, not only on its calendar date; the student may start it early.

### Small courses and settings

21. **Named settings per course, with defaults:** diagnostic time cap and maximum number of questions, rating step size, label thresholds, minimum answers before a question's rating is trusted, and milestone length. Their values are set by tests with simulated students, not fixed here.
22. **Running out of questions never stops an assessment.** When unseen questions run out, a quiz or milestone is shortened first, then reuses the questions answered longest ago, with the attempt marked as a repeat. A topic with no approved questions is "not assessed" and is placed by its position in the graph alone.
23. **The sample course** has a short diagnostic (about five minutes) and enough reviewed questions per topic, at several difficulty levels, for one sitting to show a diagnostic, a gap map, a plan and a milestone. The exact counts are set by a simulated-student test on the sample course that checks all four labels and a non-empty milestone can be reached.

### Explanations for the student

24. **Explanations are built from templates by default.** The gap map summary, "why this changed" notes and milestone reports (T-6) are produced behind one interface with two implementations chosen by configuration:
    - **Default:** templated text filled from the computed facts (topic names, labels, rating change, stored reason code). It needs no model, no account and no network, and is what the demo uses.
    - **Optional:** a language model rewords the same facts through the gateway (ADR 0005), receiving a pseudonymous ID, scores and topic names only (ADR 0002). If no provider is configured, or a call fails or is slow, the templated text is shown.

### Demonstration and testing

25. **One clock.** All time-dependent logic reads the current time from a single clock interface, so tests and simulated students can move time forward.
26. **A simulated-student harness** generates answer histories from students of known ability with a fixed random seed. It is used to test the algorithms, to choose the settings in item 21, and to create demo history.
27. **The demo student account** (ADR 0002) is created with history from the harness: part-way through a plan, with one recorded plan change and one completed milestone with its report. A "retake diagnostic" action lets the live diagnostic be shown on the same account.
28. **A documented "reset demo data" command** restores the seeded ratings, history and calibration version.

## Alternatives considered

| Alternative | Why not |
|---|---|
| Let a language model interview the student and choose the playlist | Not repeatable, hard to explain, cannot be tested, and sends student data to a model. Two students with the same answers could get different plans. |
| Item response theory with pre-calibrated questions | The standard for large exams, but needs hundreds of responses per question before it works. We have none. The method here approximates it and calibrates as data arrives; we can move to it later using the stored history. |
| Bayesian knowledge tracing or neural knowledge tracing | Need training data per topic that does not exist yet. Candidates once thousands of students have used the system. |
| Simple percentage correct per topic | Ignores question difficulty: 3 of 5 on easy questions is not the same as 3 of 5 on past JEE questions. |
| Fixed diagnostic test, the same for everyone | Either too long or too coarse. Adaptive selection gets more information from 15–20 minutes (S-3). |
| Update question ratings live after every answer | Simplest, but a student's plan would then depend on what other students answered and in what order, results could not be reproduced, and every demo run would change the sample questions' difficulty. |
| Re-plan only in a nightly job | Changes would not appear on a machine that is off at night, which is the normal case for a demo. |
| Extra demo student accounts at different stages | ADR 0002 fixes one demo account per persona. Seeded history plus a "retake diagnostic" action shows the same things with one account. |
| Language model writes all explanations | Makes the student flow depend on a provider account, against X-8, and puts unreviewed model text in front of students. |

## Consequences

- The same answers against the same calibration version always produce the same plan, and every plan item can be explained from stored numbers. This makes the logic testable with simulated students before real ones arrive.
- The student flow has no dependency on a model provider. Templated text is repetitive but free and always matches the stored numbers.
- The complete student flow, including a milestone report and a plan change, can be shown in one sitting, and the sample course can show a full gap map and an ordered plan with only a few videos.
- Works from the first student, but early ratings are rough. The gap map must show uncertainty honestly ("not assessed") instead of false precision.
- Question difficulty lags behind the answers until the next calibration version is published.
- Quality depends on the prerequisite graph (ADR 0003). A wrong link sends the diagnostic the wrong way, so inferred values stay uncertain until tested directly.
- Needs enough questions per topic at varied difficulty for diagnostics, quizzes and milestones without repeats. In the MVP these come from upload (A-6) and the sample data; later also from generation (ADR 0005).
- The simulated-student harness is extra work up front, but it replaces guesswork for every setting and supplies the demo history.
- Storing detailed attempt history for under-18 users is the tracking that PRD section 8 flags for legal advice. The design keeps it to what the learning function needs and allows deletion per student.

## Revisit if

- Legal advice on children's data limits what attempt history may be kept or for how long.
- The PRD brings subjective answers into scope: correctness is no longer yes/no, and grading needs its own decision.
- Pilot data shows the gap map disagrees with later performance; with real data, test the alternatives above against the stored history.
- The topic graph is restructured (topics merged or split) after students have ratings: ratings are rebuilt from stored attempts, and the rule for mapping old topics to new ones needs its own decision.
- The PRD adds teacher or parent views, which need the same data presented differently but should not change the model.
- The PRD changes X-7 or X-8.
