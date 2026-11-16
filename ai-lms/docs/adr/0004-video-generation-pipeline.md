# ADR 0004: Video generation pipeline

| | |
|---|---|
| **Status** | Proposed |
| **Date** | 2026-11-16 |
| **PRD requirements** | V-1 to V-8, V-10, X-2, section 8 (cost, factual errors), open questions 3 and 4 |

## Context

A course needs hundreds of videos. Each must be correct, 15 minutes or less (V-2), editable by a reviewer (V-6), and reproducible one at a time (V-7). The PRD assumes narrated explainers with slides, diagrams and step-by-step equations, with no human-like presenter (V-3).

The central question is how a script becomes moving pictures. For teaching maths and science, the picture must be exact: an equation with one wrong symbol is a wrong lesson.

## Decision

**Videos are rendered by code from a structured scene specification. A language model writes the specification; it never produces the pixels.**

```
Topic + source blocks
   │  language model
   ▼
Lesson script  ──►  Scene specification (JSON)  ──►  Automatic checks
                                                         │
                     ┌───────────────────────────────────┤
                     ▼                                   ▼
          Narration audio (text-to-speech)      Visuals (Manim renderer)
                     └──────────────┬────────────────────┘
                                    ▼
                    Assemble (FFmpeg) → captions, chapters
                                    ▼
                    Encode to HLS at several qualities → review queue
```

1. **Lesson script.** Written from the blocks assigned to the topic (ADR 0003). Each section carries the source pages it used (V-1). The model plans the length; if the estimate exceeds 15 minutes, it splits the topic into ordered sub-topic videos (V-2).
2. **Scene specification.** The script is converted into a list of scenes in a fixed JSON format. Each scene has a type from a library of templates (title, bullet points, equation derivation step by step, worked example, labelled diagram, graph of a function, table, summary), its content (text and LaTeX), its narration text, and its source pages. The specification is the editable master copy of the video.
3. **Visuals: Manim (Community Edition).** An open-source Python animation library built for mathematics. Each scene template is a tested piece of Manim code that takes the scene's content as input. Equations are typeset by LaTeX, so they are exact.
4. **Narration: text-to-speech behind a provider interface.** One voice per language per course. Narration timing drives scene timing. The provider is chosen by a listening test on Indian-English and Hindi samples, including how it reads equations and technical terms.
5. **Captions, transcript and chapters** come directly from the scene specification (V-4), so they always match what is said.
6. **Assembly and delivery.** FFmpeg joins scenes and audio and encodes HLS at several quality levels (roughly 240p to 720p). Slide-style video compresses very well, which helps slow connections (X-2).
7. **Editing and re-rendering.** A reviewer edits the script or scene specification, not the video. Scenes are rendered and cached individually, so changing one scene re-renders only that scene (V-6, V-7).
8. **Cost record.** Model usage, speech and rendering time are recorded per video (V-10).

**Custom diagrams.** Where no template fits, the model may write Manim code for a single diagram. That code runs only in a sandbox with no network or file access and a time limit; if it fails, the scene falls back to the cropped figure from the source page. This is second priority; templates come first.

## Alternatives considered

| Alternative | Why not |
|---|---|
| Generative video models (text to video) | Cannot be trusted to draw exact equations, labels or graphs; clips are short; cost per minute is high; a reviewer cannot fix one symbol without regenerating. Unsuitable for teaching content today. |
| Human-like avatar presenter | Adds cost per minute and licensing without improving understanding. PRD open question 3 assumes no avatar. Can be layered on later as an overlay without changing the pipeline. |
| Browser-based rendering (HTML slides or Remotion) | Good for general slides and familiar to web developers, but weaker for mathematical animation, and Remotion needs a paid company licence. A possible later addition for non-maths subjects. |
| Slide deck export plus narration | Simplest, but no step-by-step build-up of derivations or diagrams, which is the main teaching value. |
| Model writes free-form Manim code for every scene | Flexible but unreliable: a meaningful share of generated code fails or lays out badly, and running generated code is a security risk. Templates give predictable results; free-form code is limited to sandboxed custom diagrams. |

## Consequences

- Videos are consistent in look and predictable in quality, and every frame is traceable to a specification a person can read and edit.
- The template library is real engineering work up front and limits visual variety. New subject areas (organic chemistry structures, biology diagrams) will need new templates.
- Rendering is CPU-bound and takes minutes per video; it runs on dedicated workers (ADR 0001) and can run many videos in parallel.
- Adding a language (V-8) means translating narration and on-screen text in the specification and re-rendering. Visual logic is reused.
- Synthetic voices may sound flat on long lessons; the listening test is an early task because it affects student acceptance.

## Revisit if

- **PRD open question 3** changes to require an avatar or a different visual style.
- **PRD open question 4** changes to launch with Hindi: the speech provider test and on-screen Devanagari typesetting move to the start of the work.
- The pilot expands to subjects where diagrams matter more than equations (biology), which may justify a second renderer.
- Generative video becomes reliably exact and cheap enough to reconsider.
