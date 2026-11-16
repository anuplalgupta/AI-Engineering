# ADR 0005: Language model usage and quality control

| | |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-11-16 |
| **PRD requirements** | V-1, V-5, V-6, V-9, V-10, T-6, X-3, X-4, X-7, X-8, section 8 (factual errors, cost), open question 7 |
| **Amended by** | [ADR 0007](0007-text-tutorials-as-primary-lesson-format.md): the `write_tutorial` task. [ADR 0008](0008-consistency-after-0007-and-demo-mode.md) (proposed): task names (item 1), when the embedding model is loaded (item 2), wording of items 4 and 5 for tutorials |

## Context

In the second stage of the first release (PRD section 7), language models do most of the content work: reading pages, proposing the topic tree, writing scripts and scene specifications, and writing questions and solutions. The largest product risk in the PRD is a confident, wrong lesson reaching students. The second is cost: hundreds of long generations per course.

Three constraints shape this ADR:

- Models and prices change quickly, so the design must not be tied to one model version.
- The MVP demo runs with **no model provider at all** (X-8, ADR 0002): videos and questions are uploaded or come from the sample data. The product must behave sensibly in that state.
- When generation is switched on, a free route must exist before a paid one (X-7).

## Decision

1. **One internal gateway for all model calls.** Application code asks for a *task* (for example `write_script`, `write_questions`, `write_solution`, `check_solution`, `embed`), not a model. The gateway maps each task to a provider and model, and handles limits, usage recording and logging of prompt version, inputs and outputs.
   - **Stored results.** Every call has a key made of task, prompt version, model, a hash of the inputs and an attempt number. The gateway stores the validated output in PostgreSQL under that key; a repeat call with the same key returns the stored output without calling the provider. This makes pipeline steps safe to run twice (ADR 0001) and prevents a second charge. Deliberate regeneration (V-7) raises the attempt number.
   - **Retries.** The gateway itself retries only passing errors (timeouts, rate limits, server errors), a small fixed number of times with increasing delay. Every other failure goes back to the job and counts against the retry limit in ADR 0001.
   - **Page extraction** is owned by the extractor interface in ADR 0003; only the vision-model extractor calls the gateway.
2. **Provider modes, chosen per task by configuration:**

   | Mode | What it is | When |
   |---|---|---|
   | **None** | No provider configured. Generation tasks are refused with a plain message on the admin screen, and the pipeline item keeps its status. Every student, reviewer and admin screen still works with uploaded and sample content. | MVP demo; the default on a fresh install |
   | **Free** | A hosted free tier or a model run locally, reached through one adapter for the widely used OpenAI-style interface. Expected to be slow and less accurate; to be measured. | Trying generation at no cost |
   | **Paid** | Anthropic's Claude models: the most capable model where reasoning quality matters (scripts, solutions, checking), a smaller, cheaper one for high-volume tasks (tagging, extraction). | Real pilot content |

   All adapters share one request and response contract. Each adapter declares what it supports (batch processing, prompt caching, enforced structured output, image input). **Embeddings** are a gateway task served by a small open embedding model run on the processor in the worker container, in every mode.
3. **Structured output everywhere.** Every task returns data in a defined format that is validated on receipt. Invalid, cut-off or refused output never flows onward.
4. **Grounding.**
   - Scripts are written only from supplied source blocks, and each section must cite the blocks it used. Output citing nothing, or citing blocks that were not supplied, is rejected.
   - For questions, grounding means each question and solution cites the source blocks that state the concepts and formulas it uses; the numbers and the scenario may be new.
   - Source blocks are passed to the model as marked data. Instructions that appear inside source text are not followed.
5. **Automatic checks before a person sees anything.** All checks run on the script and questions before rendering; an item reaches `script_ready` (ADR 0001) only after they have run.

   **Group A — always on, no model call:**
   - *Structure*: output matches the defined format.
   - *Citations*: every cited block exists and was supplied.
   - *Numerical answers recomputed by code.* The model supplies each calculation as an arithmetic expression in a restricted form: numbers, named constants from a fixed table, `+ - * /` and powers, brackets, and a fixed list of maths functions. Our own evaluator reads it and rejects anything else. The expression is never passed to a general code-execution function or a shell. Expression length, exponent size and run time are limited. The result is compared with the stated answer within a configured tolerance and, for multiple-choice questions, must match exactly one option. This catches arithmetic errors only.
   - *Format*: length limit, LaTeX compiles, every scene has narration and sources (ADR 0004).

   **Group B — model calls, set per task to off, sampled or full:**
   - *Independent check.* A second call, given the source blocks and the draft but not the first call's reasoning, lists any claim not supported by the source.
   - *Blind solve.* A separate call answers each question, generated or past-paper, without seeing the answer key. Answers are compared by option letter or by the numerical tolerance.
   - Where configuration allows, Group B uses a different model from the one that wrote the content.
   - Default is full in paid mode. When Group B is off or sampled, the review screen says so beside the content.

   **What a failure does:**
   - A Group A failure, or cut-off or refused output, triggers regeneration with the failure message added, up to a configured limit; after that the item is marked failed and shown to the admin.
   - A Group B finding triggers one regeneration. If it persists, the item goes on and the finding is shown to the reviewer as a warning on that script section or question.
   - A flagged question is not used in any assessment until a reviewer approves it.
   - For a past-paper question, a blind-solve disagreement flags the stored answer key for the admin to correct (A-5).
6. **Worked solutions (V-5).** Generated questions are written with their solutions. Past-paper questions (ADR 0003) get a model-written worked solution through the `write_solution` task; its final answer must equal the stored answer key or the item is flagged. Uploaded questions (A-6) may carry their own solution.
7. **Human review is the final gate (V-6).** Automatic check results are shown to the reviewer as warnings beside the content. Nothing is published without approval, whatever the checks say.
8. **A fixed evaluation set.** A set of topics with expert-approved scripts and questions is kept as a benchmark. It starts with 5 to 10 topics from the openly licensed sample course (ADR 0003) and grows to a few dozen before real pilot content is generated. Any change to a prompt or model is run against it before going live, and results are compared with the previous version.
9. **Cost control.**
   - For each call the gateway records input and output size, duration, and cost from a price table kept in configuration, from the first release. The admin screen for this (V-10) stays P1.
   - The gateway enforces a spend limit per day and per course. A paid adapter does not start until a limit is set. When the limit is reached, jobs pause and the admin sees why.
   - Batch processing and prompt caching are used only where the adapter offers them, are off by default, and are never used for a single-video regeneration (V-7). Otherwise calls are sent one at a time from the PostgreSQL queue (ADR 0002) with a configurable rate limit, so free-tier limits are respected.
10. **No student-facing screen depends on a model call succeeding.**
    - No student personal data is sent in content-generation calls (ADR 0002).
    - The milestone report (T-6) and other explanations for students are built from fixed templates filled with the computed results of the learner model (ADR 0006). This is the default and needs no model.
    - As an optional setting, a model may reword the template text. It receives a pseudonymous ID, scores and topic names only. Its output is checked to contain the same topics and numbers as the template; the template text is shown on any failure or when no provider is configured.

## Alternatives considered

| Alternative | Why not |
|---|---|
| Call a model provider directly from each feature | Fastest to write, but scatters prompts, retry logic and cost tracking, and makes changing model a code change in many places. |
| A general-purpose agent or chain framework | Adds a large dependency and hides the prompts, which we need to control and version. Our tasks are fixed steps, not open-ended agents. |
| A paid provider as the only route | Best quality, but nothing can be generated without an account and a bill, against X-7. Kept as the recommended mode for real content. |
| Open models on our own machine as the only route | Free and keeps all data in India, but slow without a graphics processor and weaker on equation-heavy material. Kept as the free mode; the gateway makes the choice a configuration setting. |
| Recorded model responses replayed in the demo | Fragile: recordings stop matching as soon as a prompt or an extractor output changes. Included sample content covers the demo instead (ADR 0002). |
| Rely on human review alone | Reviewers miss errors, especially in long derivations, and review time is the bottleneck (PRD section 8). Automatic checks catch the mechanical errors so people can concentrate on teaching quality. |
| Rely on automatic checks alone | No automatic check is reliable enough for content taught to thousands of students. |
| Skip the blind solve when the recomputed answer already matches | The same call writes both the expression and the stated answer, so recomputation only catches arithmetic slips. The blind solve is the one automatic check on method. |
| Run model-supplied calculations as general code in a sandbox | A sandbox per calculation is heavy on one small machine and a security risk if built loosely. A restricted arithmetic evaluator covers the need. |
| Train or fine-tune our own model | Out of scope in the PRD; no data yet to train on. |

## Consequences

- The product is fully usable with no model provider; generation is an added capability, not a dependency.
- Changing model or provider is a configuration change checked against the benchmark, not a rewrite.
- In paid mode each video costs several model calls (write, check, solve) instead of one. This is the price of catching errors early. Cost per video is not estimated here; it is measured from the recorded usage on the first generated topics and written into this ADR.
- In free mode, Group B checks may be off or sampled to stay within free limits. Human review then carries more of the load, and the review screen says which checks ran.
- Stored results use database space and must be cleared when a prompt version is retired.
- Building and maintaining the benchmark set needs subject-expert time, starting small.
- In paid mode, source material is sent to a model provider outside India. This is content, not student data, but it must be consistent with the content licences (PRD open question 5).
- Reviewer decisions (approved, edited, rejected and why) are stored and become the data for improving prompts.
- Report and explanation data depends on ADR 0006.

## Revisit if

- **PRD open question 7** changes to forbid AI-generated questions: question generation is removed; the blind solve and worked solutions still apply to past-paper and uploaded questions.
- Content licences forbid sending source text to an external provider: move affected tasks to a locally run model through the same gateway.
- First-review approval rate stays well below the PRD target (70%), which would point to prompts, templates or model choice needing work.
- Measured cost per video in paid mode makes a full course unaffordable: reduce Group B to sampled, or move high-volume tasks to a cheaper model.
- The free mode proves too slow or inaccurate to be useful even for trials: drop it and keep "none" and "paid".
- The PRD changes X-7 or X-8.
