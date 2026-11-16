# ADR 0004: Lesson video pipeline (uploaded and generated)

| | |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-11-16 |
| **PRD requirements** | V-1 to V-8, V-10, V-11, X-2, X-7, X-8, section 8 (cost, factual errors), open questions 3 and 4 |
| **Amended by** | [ADR 0007](0007-text-tutorials-as-primary-lesson-format.md): text tutorials become the primary generated format; generated video (section C) moves after the first release. [ADR 0008](0008-consistency-after-0007-and-demo-mode.md) (proposed): build order (item 2), the LaTeX check (item 9), the no-account table and the image size apply as stated there |

## Context

A course needs hundreds of videos. Each must be correct, 15 minutes or less (V-2), editable by a reviewer (V-6), and reproducible one at a time (V-7). The PRD assumes narrated explainers with slides, diagrams and step-by-step equations, with no human-like presenter (V-3).

Two further constraints arrived after the first draft of this ADR:

- The MVP must run on free components on one small machine, and a non-engineer must be able to demonstrate it (X-7, X-8).
- Generating lessons is the largest and riskiest piece of engineering in the product. The MVP demo must not wait for it: an admin can upload finished lesson videos alongside the textbook (V-11).

So a lesson video has **two sources**, and everything after the video exists (review, publishing, playback, quizzes, progress) must not care which one was used.

For generated video, the central question is how a script becomes moving pictures. For teaching maths and science, the picture must be exact: an equation with one wrong symbol is a wrong lesson.

## Decision

### A. One video record, two sources

1. **A lesson video belongs to a topic and has a source: `uploaded` or `generated`.** Both kinds are stored in the same tables, delivered the same way, pass through the same review gate (V-6) and are used identically by playlists, quizzes and progress tracking.
2. **Build order.** The uploaded path (section B) is built first and is what the MVP demo uses. The generated path (section C) is built after it, behind the same video record, and can be added without changing anything a student or reviewer sees.

### B. Uploaded videos (MVP)

3. **Upload.** An admin uploads a video file for an approved topic, confirms the right to use it (stored with the file, as for PDFs in ADR 0003) and may link it to source pages. The original file is kept unchanged.
4. **Processing.** A worker checks the file, measures its length and encodes it to HLS with FFmpeg, using the same settings as generated video (item 14). A video longer than the limit in V-2 is refused with a message asking for it to be split; the limit is configuration.
5. **Captions, transcript and chapters (V-4).** The admin may upload a caption file (WebVTT or SRT) and chapter times. If none is supplied, the video is marked "no captions" on the review screen. Producing captions automatically with an open-source speech-recognition model run locally is an optional later step, off by default.
6. **Review and replacement.** An uploaded video enters the review queue like any other. A reviewer approves or rejects it; "edit and re-render" does not apply. Replacing the file creates a new version that is reviewed again, while students keep seeing the approved one (item 16).

### C. Generated videos

**Videos are rendered by code from a structured scene specification. A language model writes the specification; it never produces the pixels.**

```
Topic + source blocks
   │  language model (ADR 0005)
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

7. **Lesson script.** Written from the blocks assigned to the topic (ADR 0003). Each section carries the source pages it used (V-1). The model plans the length; if the estimate exceeds 15 minutes, it splits the topic into ordered sub-topic videos (V-2). All model calls go through the gateway in ADR 0005.
8. **Scene specification.** The script is converted into a list of scenes in a fixed JSON format. Each scene has a type from a library of templates (title, bullet points, equation derivation step by step, worked example, labelled diagram, graph of a function, table, summary), its source pages, and a list of **steps**. Each step has its own on-screen change and its own narration segment. The specification is the editable master copy of the video.
9. **Automatic checks, before anything is rendered:**
   - the specification is valid against the JSON format;
   - every LaTeX string compiles on its own and uses only packages on an allowed list;
   - every content scene cites at least one source page from the topic's assigned blocks (title and summary scenes are exempt);
   - text length is within the template's limits;
   - estimated total length is 15 minutes or less.

   Checks on facts and numerical answers belong to ADR 0005 and run on the script before this step. If a model-written specification fails, it is sent back to the model once with the error; a second failure marks the video failed, with the scene and error shown to the admin (ADR 0001). If a reviewer's edit fails, the error is shown to the reviewer and nothing is rendered.
10. **Visuals: Manim (Community Edition).** An open-source Python animation library built for mathematics. Each scene template is a tested piece of Manim code that takes the scene's content as input.
    - Mathematics is typeset by LaTeX, so equations are exact. All other text (titles, bullets, labels) uses Manim's font-based text, so adding a language needs a font, not new templates.
    - All LaTeX content is untrusted input: it is compiled with shell escape disabled, file access limited to a scratch directory, and a time limit.
    - Every scene is rendered once at 1280×720 with one frame rate and identical encoding settings, set by configuration, so scenes join without re-encoding.
11. **Narration: text-to-speech behind one provider interface, chosen by configuration.**
    - **Default (hosting steps 1 and 2):** an open-source engine run on the processor inside the worker container, with no account and no network. Its voice files are built into the container image, not downloaded on first use. Candidates: Kokoro first, Piper second (Piper is run as a separate command-line program because of its licence).
    - **Excluded:** voices licensed for non-commercial use only.
    - **Later, by configuration:** a hosted voice, if the listening test shows students do not accept the free one.
    - The listening test is run first on the free candidates, on Indian-English physics text including equations, units and names. No free candidate is known to offer an Indian-English accent, so a neutral English voice is accepted for the MVP.
    - The licence of the engine and of each voice is checked and recorded before use.
    - Each narration segment is synthesised to its own audio file, and its measured length sets the length of that step's animation. No word-level timing is needed from the speech engine.
12. **Length is enforced on measured audio.** After narration is synthesised, the total is checked. A video over 15 minutes is not assembled; the topic returns to the split step. The check runs for every language.
13. **Captions, transcript and chapters** (V-4). Caption and transcript text come from the narration segments, their timings from the measured segment lengths, and chapter markers from scene start times. They are stored as WebVTT files beside the HLS playlist.
14. **Assembly and delivery.** FFmpeg joins scenes and audio and encodes H.264 video with AAC audio into HLS. The quality levels are configuration, with a default of three (about 240p, 480p and 720p) (X-2). Slide-style video compresses very well, which helps slow connections.
15. **Editing, re-rendering and caching.** A reviewer edits the script or scene specification, not the video.
    - A scene's audio and video are stored under a key that is a hash of the scene's content, template version, renderer version, voice and speech settings, and render settings. Output is produced once per key and reused, which makes every step safe to run twice (ADR 0001) and means a template fix or voice change cannot reuse stale output.
    - Changing one scene re-renders only that scene (V-6, V-7).
    - **Re-render** reuses the current specification and needs no language model. **Regenerate** asks the model for a new one and warns if the current version contains hand edits.
    - A scene that fails at speech or render time fails only that scene; the video is not assembled, and the admin sees which scene failed and why.
16. **Versions.** A published video points at one approved version. An edit, regeneration or replacement upload creates a new version that goes through review; students keep seeing the previously approved version until the new one is approved.
17. **Pipeline statuses (ADR 0001).** Specification passed its checks = `script_ready`; narration, scene render, assembly and encoding complete = `rendered`; then `in_review` and `published`. An uploaded video enters at `rendered` once encoding completes.
18. **Cost record.** Model usage, speech and rendering time are recorded per video (V-10).

**Custom diagrams** are behind a configuration switch that is **off in the MVP and the demo**. With it off, a scene that fits no template shows the cropped figure from the source page (ADR 0003) with narration; no generated code is run. When it is turned on (hosting step 3), model-written Manim code for a single diagram runs in an isolated process or container with: no network, a non-root user, a read-only file system apart from a size-limited scratch directory, limits on memory, processor, process count and time, and no database or file-store credentials. The worker never has access to the Docker socket. The generated code is stored with the scene and shown to the reviewer. If it fails, the scene falls back to the cropped figure.

### What works with no AI account and no internet

| Action | Needs |
|---|---|
| Play, review and publish sample or uploaded videos | Nothing extra |
| Upload a new video and encode it | Nothing extra (FFmpeg is in the container) |
| Edit narration or on-screen text in a generated sample video and re-render | Nothing extra (local voice, Manim, FFmpeg) |
| Write a new lesson script and scene specification from a PDF | A language model (ADR 0005) |

## Alternatives considered

| Alternative | Why not |
|---|---|
| Generated video only, no upload | Makes the whole MVP depend on the hardest piece of engineering, and leaves institutes that already have good lessons unable to use them. |
| Uploaded video only, drop generation | Removes the product's main promise (PRD goal 2, problem "cost of content production"). Upload is the first step, not the end state. |
| Link to videos hosted elsewhere (for example a video-sharing site) | No control over availability, adverts or tracking on student pages (ADR 0002), and no adaptive quality under our control. |
| Generative video models (text to video) | Cannot be trusted to draw exact equations, labels or graphs; clips are short; cost per minute is high; a reviewer cannot fix one symbol without regenerating. Unsuitable for teaching content today. |
| Human-like avatar presenter | Adds cost per minute and licensing without improving understanding. PRD open question 3 assumes no avatar. Can be layered on later as an overlay without changing the pipeline. |
| Browser-based rendering (HTML slides or Remotion) | Good for general slides and familiar to web developers, but weaker for mathematical animation, and Remotion needs a paid company licence. A possible later addition for non-maths subjects. |
| Slide deck export plus narration | Simplest, but no step-by-step build-up of derivations or diagrams, which is the main teaching value. |
| Model writes free-form Manim code for every scene | Flexible but unreliable: a meaningful share of generated code fails or lays out badly, and running generated code is a security risk. Templates give predictable results; free-form code is limited to sandboxed custom diagrams, off by default. |
| A hosted text-to-speech service as the default | Needs an account and costs per character from the first render, against X-7. Kept as a configuration choice. |

## Consequences

- The MVP demo can show the complete flow with uploaded videos before any generation code exists. The price is that the MVP does not yet prove the product's main promise; that is proved when section C is built.
- Uploaded videos have no script, so a reviewer cannot fix a mistake in one; they can only reject it. Source traceability (V-1) for an uploaded video is only as good as the page links the admin supplies.
- Generated videos are consistent in look and predictable in quality, and every frame is traceable to a specification a person can read and edit.
- The template library is real engineering work up front and limits visual variety. New subject areas (organic chemistry structures, biology diagrams) will need new templates.
- Rendering and encoding are processor-bound and take minutes per video. They run in the render worker (ADR 0001) with a configurable limit on simultaneous jobs: one at hosting steps 1 and 2, raised at step 3 when render workers move to their own machines, with no code change. Render time per video minute on the minimum machine is measured on the first templates and recorded here.
- The worker container image is large (Manim, a minimal LaTeX installation limited to the packages the templates use, FFmpeg, the speech engine and voice). It is published pre-built, and its download size is stated in the running guide.
- Adding a language (V-8) means translating narration and on-screen text in the specification, adding a font and voice, and re-rendering. Visual logic is reused. Devanagari rendering is tested with one sample scene before Hindi work starts.
- Synthetic voices may sound flat on long lessons, and the free voice is not Indian-accented; the listening test is an early task because it affects student acceptance.

## Revisit if

- **PRD open question 3** changes to require an avatar or a different visual style.
- **PRD open question 4** changes to launch with Hindi: the speech provider test and on-screen Devanagari typesetting move to the start of the work.
- The free local voice fails the listening test with pilot students: switch to a hosted voice by configuration.
- More than about 10% of scenes in the pilot course fall back to a cropped source figure: add templates or turn on custom diagrams.
- Fewer than the PRD target of 70% of generated videos are approved on first review because of visual or narration problems.
- Render time on the chosen hosting step puts the PRD target of under 2 working days from upload to first published video out of reach.
- Uploaded videos turn out to be the main source of content in the pilot: captions by speech recognition and a way to correct them become necessary.
- The pilot expands to subjects where diagrams matter more than equations (biology), which may justify a second renderer.
- Generative video becomes reliably exact and cheap enough to reconsider.
- The PRD changes X-7, X-8 or V-11.
