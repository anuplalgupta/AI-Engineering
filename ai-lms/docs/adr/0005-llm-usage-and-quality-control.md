# ADR 0005: Language model usage and quality control

| | |
|---|---|
| **Status** | Proposed |
| **Date** | 2026-11-16 |
| **PRD requirements** | V-1, V-5, V-6, V-9, V-10, X-3, X-4, section 8 (factual errors, cost), open question 7 |

## Context

Language models do most of the content work: reading pages, proposing the topic tree, writing scripts and scene specifications, and writing questions and solutions. The largest product risk in the PRD is a confident, wrong lesson reaching students. The second is cost: hundreds of long generations per course.

Models and prices change quickly, so the design should not be tied to one model version.

## Decision

1. **One internal gateway for all model calls.** Application code asks for a *task* (for example `extract_page`, `write_script`, `write_questions`, `check_solution`), not a model. The gateway maps each task to a provider and model, and handles retries, limits, usage recording and logging of prompt version, inputs and outputs.
2. **Default provider: Anthropic's Claude models**, with the most capable model for tasks where reasoning quality matters (scripts, solutions, checking) and a smaller, cheaper model for high-volume tasks (page extraction, tagging). The mapping is configuration, so it can change without code changes.
3. **Structured output everywhere.** Every task returns data in a defined format that is validated on receipt. Invalid output is retried, then flagged; it never flows onward.
4. **Grounding.** Scripts and questions are written only from supplied source blocks, and each section must cite the blocks it used. Output citing nothing, or citing blocks that were not supplied, is rejected.
5. **Automatic checks before a person sees anything:**
   - **Independent check pass.** A second model call, given the source blocks and the draft but not the first call's reasoning, lists any claim not supported by the source.
   - **Numerical answers are recomputed by code.** For worked examples and numerical questions, the model supplies the calculation as an executable expression, which is evaluated (in a sandbox) and compared with the stated answer.
   - **Questions are solved blind.** A separate call answers each generated question without seeing the answer key. Disagreement flags the question.
   - **Format checks**: length limit, LaTeX compiles, every scene has narration and sources.
6. **Human review is the final gate (V-6).** Automatic check results are shown to the reviewer as warnings beside the content. Nothing is published without approval, whatever the checks say.
7. **A fixed evaluation set.** A few dozen topics with expert-approved scripts and questions are kept as a benchmark. Any change to a prompt or model is run against it before going live, and results are compared with the previous version.
8. **Cost control.** Non-urgent generation uses providers' batch processing, and repeated context (the same chapter used for script, questions and checks) uses prompt caching. Usage is recorded per task and per video (V-10).
9. **No student personal data in content-generation calls** (ADR 0002). Where a model writes text for a student, such as a milestone report (T-6), it receives scores and topic names only.

## Alternatives considered

| Alternative | Why not |
|---|---|
| Call a model provider directly from each feature | Fastest to write, but scatters prompts, retry logic and cost tracking, and makes changing model a code change in many places. |
| A general-purpose agent or chain framework | Adds a large dependency and hides the prompts, which we need to control and version. Our tasks are fixed steps, not open-ended agents. |
| Rely on human review alone | Reviewers miss errors, especially in long derivations, and review time is the bottleneck (PRD section 8). Automatic checks catch the mechanical errors so people can concentrate on teaching quality. |
| Rely on automatic checks alone | No automatic check is reliable enough for content taught to thousands of students. |
| Train or fine-tune our own model | Out of scope in the PRD; no data yet to train on. |
| Run open models on our own servers | Keeps all data in India and may cut cost at scale, but needs GPU operations skills and currently gives weaker results on equation-heavy pages. The gateway makes this a later configuration choice. |

## Consequences

- Changing model or provider is a configuration change checked against the benchmark, not a rewrite.
- Each video costs several model calls (write, check, solve) instead of one. This is the price of catching errors early; the cost record (V-10) will show whether it is acceptable.
- Building and maintaining the benchmark set needs subject-expert time before the first course is generated.
- Source material is sent to a model provider outside India. This is content, not student data, but it must be consistent with the content licences (PRD open question 5).
- Reviewer decisions (approved, edited, rejected and why) are stored and become the data for improving prompts.

## Revisit if

- **PRD open question 7** changes to forbid AI-generated questions: question generation is removed and the blind-solve check applies only to past-paper answer keys.
- Content licences forbid sending source text to an external provider: move affected tasks to self-hosted models through the same gateway.
- First-review approval rate stays well below the PRD target (70%), which would point to prompts, templates or model choice needing work.
