# ADR 0006: Learner model, diagnostic and study plan

| | |
|---|---|
| **Status** | Proposed |
| **Date** | 2026-11-16 |
| **PRD requirements** | S-3, S-4, S-5, P-1 to P-6, T-2 to T-6, section 8 (diagnostic length, children's data) |

## Context

The product's promise to the student is: we find what you do not know, tell you what to study next, and show you that you are improving. That requires four things to work together: an estimate of mastery per topic, a short diagnostic that produces a first estimate (S-3), a playlist and dated plan built from it (P-1, P-2), and milestone tests built for the individual (T-4).

There is no student data yet. Whatever method we choose must work from the first student, with questions whose difficulty has not been measured, and must be explainable to a student ("why is this in my plan?", P-3).

## Decision

**Mastery, question selection and planning are computed by deterministic algorithms over the topic graph. Language models are not used to judge what a student knows or to decide what they study.**

### Mastery estimate

1. **A rating per student per topic, and a rating per question**, updated after every answer in the style of the Elo system used in chess: answering a hard question correctly raises the student's topic rating a lot, missing an easy one lowers it a lot. Question ratings move in the opposite direction, so question difficulty calibrates itself as students answer.
2. **Starting values**: questions start from a difficulty estimate (past-paper questions by exam level, generated questions by the level requested); students start at a neutral rating with high uncertainty.
3. **Each rating has an uncertainty** that shrinks with more answers and grows slowly with time since the topic was last practised. This drives revision (P-6).
4. **The gap map (S-4)** translates rating and uncertainty into four labels: not assessed, weak, developing, strong.
5. **Every attempt is stored unchanged** (T-3): question, answer, correctness, time taken, timestamp. Ratings can always be recomputed from this history if the method changes.

### Diagnostic

6. **Adaptive walk over the prerequisite graph.** Start with questions on topics in the middle of the course. A wrong answer moves towards that topic's prerequisites; a right answer moves towards topics that depend on it. Each next question is chosen to reduce uncertainty the most.
7. **Inference between linked topics.** Clear strength in an advanced topic raises the estimate of its prerequisites; clear weakness in a prerequisite lowers the estimate of topics that depend on it. These inferred values keep high uncertainty until tested directly.
8. **Stops** when the time cap is reached (S-3) or uncertainty is low enough across the course. Untested topics are labelled "not assessed", never guessed as strong.

### Playlist and study plan

9. **Playlist = ordered list of topics** produced by sorting the prerequisite graph so prerequisites come first, filtered to topics that are not strong, and ranked by a score combining size of gap, number of later topics that depend on it, and exam weight (ADR 0003, P-4).
10. **Study plan = playlist placed on a calendar** using video length, expected quiz time, the student's weekly hours and target date (P-2). If the plan does not fit, lowest-ranked topics are dropped first and the student is told.
11. **Re-planning** runs after every quiz and nightly. Each change is stored with its reason (P-3).
12. **Milestone evaluations (T-4)** are assembled by rule: cover topics studied since the last milestone, give more questions to topics with lower rating or higher uncertainty, avoid questions the student has seen, and match the exam's format.

### Where a language model is used

13. Only to write explanations in plain language from the computed facts: the gap map summary, "why this changed" notes and milestone reports (T-6). The model receives scores and topic names, not personal details (ADR 0002, 0005).

## Alternatives considered

| Alternative | Why not |
|---|---|
| Let a language model interview the student and choose the playlist | Not repeatable, hard to explain, cannot be tested, and sends student data to a model. Two students with the same answers could get different plans. |
| Item response theory with pre-calibrated questions | The standard for large exams, but needs hundreds of responses per question before it works. We have none. The Elo-style method approximates it and calibrates as data arrives; we can move to it later using the stored history. |
| Bayesian knowledge tracing or neural knowledge tracing | Need training data per topic that does not exist yet. Candidates once thousands of students have used the system. |
| Simple percentage correct per topic | Ignores question difficulty: 3 of 5 on easy questions is not the same as 3 of 5 on past JEE questions. |
| Fixed diagnostic test, the same for everyone | Either too long or too coarse. Adaptive selection gets more information from 15–20 minutes (S-3). |

## Consequences

- Same answers always produce the same plan, and every plan item can be explained from stored numbers. This also makes the logic unit-testable with simulated students before real ones arrive.
- Works from the first student, but early ratings are rough. The gap map must show uncertainty honestly ("not assessed") instead of false precision.
- Quality depends on the prerequisite graph (ADR 0003). A wrong link sends the diagnostic the wrong way, so inferred values stay uncertain until tested directly.
- Needs enough questions per topic at varied difficulty: roughly 10 or more for diagnostics, quizzes and milestones without repeats. This is a content requirement on ADR 0005.
- Storing detailed attempt history for under-18 users is the tracking that PRD section 8 flags for legal advice. The design keeps it to what the learning function needs and allows deletion per student.

## Revisit if

- Legal advice on children's data limits what attempt history may be kept or for how long.
- The PRD brings subjective answers into scope: correctness is no longer yes/no, and grading needs its own decision.
- Pilot data shows the gap map disagrees with later performance; with real data, test the alternatives above against the stored history.
- The PRD adds teacher or parent views, which need the same data presented differently but should not change the model.
