# ADR 0007: Text tutorials with diagrams as the primary lesson format

| | |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-11-16 |
| **PRD requirements** | V-1, V-5, V-6, V-7, V-12, V-13, P-1, T-1, X-2, X-3, X-7, X-8, section 7 |
| **Amends** | [ADR 0004](0004-video-generation-pipeline.md) (build order, lesson record), [ADR 0006](0006-learner-model-and-study-plan.md) (item 14, 16) |
| **Amended by** | [ADR 0008](0008-consistency-after-0007-and-demo-mode.md) (proposed): how maths is checked (item 4), a topic with both a tutorial and a video (items 10, 11), statuses (item 12) |

## Context

ADR 0004 gives a lesson two sources, uploaded video and generated video. Generated video is the most expensive part of the product to build and to run: a template library, a speech engine, minutes of rendering per lesson on a small machine, and a large container image. Uploaded video removes that from the MVP demo but leaves the product with nothing it generates itself.

A generated **text tutorial with diagrams** sits between the two. It needs one model call chain and no rendering, loads quickly on a slow phone (X-2), is easy for a reviewer to correct, and still shows the product's main promise: a lesson made from the textbook for each topic.

It also fits what is already decided. ADR 0004's generated video starts from a lesson script and a structured scene specification. A tutorial is the same structured content shown as a page instead of rendered as frames.

## Decision

1. **A lesson is the unit the student studies, and it has a format.** Every topic can have a lesson in one of three formats:

   | Format | Source | Stage (PRD section 7) |
   |---|---|---|
   | **Text tutorial with diagrams** | Generated from the source blocks, or written by hand | 1 (sample and hand-written), 2 (generated) |
   | **Uploaded video** | Uploaded by the admin (ADR 0004 section B) | 1 |
   | **Generated video** | Rendered from a scene specification (ADR 0004 section C) | 3, after the first release |

   A topic may have a tutorial and a video; the student sees both, tutorial first. Review, publishing, the playlist, the study plan, quizzes and progress treat all formats the same.
2. **The text tutorial is the primary generated format** for the first release. Generated video is kept as designed in ADR 0004 and moves after the first release.
3. **A tutorial is a structured lesson document**, stored as data, not as a page. It is an ordered list of sections; each section has a type, its content and its source pages (V-1). Section types: explanation (prose), equation derivation step by step, worked example, diagram with caption, table, key points, common mistakes, summary. These are the same content types as the scene templates in ADR 0004, so a tutorial can later be the starting point of a generated video for the same topic.
4. **Text and equations.** Prose is Markdown; mathematics is LaTeX, typeset in the browser by an open-source maths renderer bundled with the web app (no external service). The automatic check that every LaTeX string is valid (ADR 0004 item 9) applies.
5. **Diagrams come from three sources, in this order of preference:**
   - **The figure from the source page**, cropped during extraction (ADR 0003), shown with its page reference.
   - **A diagram drawn by code from a specification**: a small library of tested diagram templates (graph of a function, vectors and forces on a body, labelled diagram, concept map of linked ideas, number line or axis, simple circuit). The model supplies the template name and its data; code draws an SVG image. Labels and values are exact because code places them.
   - **An SVG image written by the model**, for a diagram no template covers. SVG is a picture description, not a program: it is cleaned before storage (no scripts, no links to outside files, size limit) and always marked on the review screen as "drawn by the model, check carefully". This source is behind a configuration switch.

   Every diagram is produced once at generation time and stored as an image file, so what the reviewer approves is exactly what the student sees.
6. **Length.** A tutorial has a target reading time of 15 minutes or less, estimated from word count plus a fixed allowance per equation, diagram and worked example. A topic that needs more is split into ordered sub-topic tutorials, as for video (V-2).
7. **Generation** uses the gateway and checks in ADR 0005 unchanged: written only from the topic's source blocks, citations per section, numerical answers recomputed, independent check, then human review. The task is `write_tutorial`.
8. **Three ways a tutorial comes to exist:**
   - **Included sample data**: finished tutorials for the sample course, so the demo needs no model (X-8).
   - **Written or pasted by hand** in an editor on the admin screen (V-13), with a live preview. Works with no model provider.
   - **Generated** from the source blocks when a provider is configured in free or paid mode (ADR 0005).
9. **Review and editing.** The reviewer sees the tutorial beside its source pages and can edit any section's text, equations or diagram data directly, replace a diagram, or regenerate one section or the whole tutorial (V-6, V-7). An edit creates a new version that must be approved; students keep seeing the approved version (ADR 0004 item 16).
10. **Progress (T-1).** The student's position is tracked by section: started, sections reached, completed when the last section is reached and the student marks it done. The tutorial reopens at the last section reached. The topic quiz follows the lesson as before (T-2).
11. **Study plan.** Wherever ADR 0006 says "published video", read "published lesson". The plan schedules a tutorial by its estimated reading time and a video by its length. A topic with approved questions but no published lesson of any format stays a practice-only item marked "lesson coming".
12. **Pipeline statuses (ADR 0001).** A tutorial that has passed its checks and had its diagrams drawn is `rendered`, then `in_review` and `published`. There is no separate rendering worker step.
13. **The installed web app keeps opened tutorials available offline.** Text and images are small enough to store on the phone, which gives part of X-6 for this format at little cost.

## Alternatives considered

| Alternative | Why not |
|---|---|
| Keep generated video as the only generated format | Highest build and running cost of any part of the product, and the MVP would generate nothing until it is finished. |
| Drop video entirely | Institutes with good recorded lessons could not use them, and the upload path is already designed and cheap. Generated video stays available as a later stage. |
| Tutorial stored as one Markdown or HTML page | Simple, but a reviewer could not regenerate one section, sources could not be tracked per section, and nothing could be reused for video. |
| Diagrams as images made by an image-generation model | Labels, values and geometry cannot be trusted to be exact, and a reviewer cannot correct one label. Same objection as generative video in ADR 0004. |
| Diagrams only from source-page figures | Free and exact, but depends entirely on content rights (PRD open question 5) and gives nothing for a worked example that needs its own figure. |
| Model writes drawing code that is run to make each diagram | Flexible, but running generated code is the security risk ADR 0004 already switched off. Templates and cleaned SVG avoid running any generated code. |
| Slides or an auto-narrated slideshow as a middle format | Closer to video, but needs the speech engine and most of the rendering work for little gain over a well-structured page. |

## Consequences

- The MVP demo shows a generated-style lesson for each sample topic with no model, no rendering and almost no processing load. The worker container no longer needs Manim, LaTeX or a speech engine until stage 3, so it is much smaller and faster to download.
- Generating a course is far cheaper and faster than with video: model calls only, no rendering time.
- Reviewers can fix a mistake in place, which should raise the first-review approval rate and shorten review time.
- Reading suits some students less than watching, and a page shows a derivation less vividly than an animation. Engagement measures in the pilot will show whether this matters; uploaded and later generated video remain available per topic.
- The diagram template library is real work and limits what can be drawn exactly. Model-written SVG widens coverage but leans on the reviewer.
- Text is easier to copy than video, which matters if the source material's licence restricts reproduction (PRD open question 5).
- The PRD success measure "average video completion" becomes "average lesson completion".

## Revisit if

- Pilot engagement or learning results are clearly worse for tutorial-only topics than for topics with video: bring generated video (stage 3) forward.
- More than about 10% of diagrams need model-written SVG, or reviewers reject many of them: add templates.
- Content rights restrict reproducing source text or figures closely: tighten how much source wording a tutorial may reuse, and rely on drawn diagrams.
- The PRD changes V-12, V-13, X-7 or X-8.
