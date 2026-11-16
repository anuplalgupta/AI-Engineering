# ADR 0003: Content ingestion and the topic graph

| | |
|---|---|
| **Status** | Proposed |
| **Date** | 2026-11-16 |
| **PRD requirements** | A-2, A-3, A-4, A-5, A-7, V-1, P-1, P-4, section 8 (copyright, poor extraction) |

## Context

Everything downstream depends on reading the uploaded PDFs correctly: scripts are written from them, questions are drawn from them, and every claim in a video must point back to a page (V-1). The material is hard to read by machine. Physics and chemistry pages are full of equations, diagrams, tables and multi-column layouts, and many Indian textbooks and past papers circulate as scans.

The topic tree with prerequisite links (A-4) is the backbone of the product. Videos, questions, mastery and playlists all hang off it.

## Decision

### Reading the PDFs

1. **Process page by page.** Each page is turned into an image and also has its embedded text extracted where present.
2. **A vision-capable language model converts each page into structured text**: Markdown for prose, LaTeX for equations, described figures (with the figure cropped and stored as an image), and tables. The embedded text, where available, is given to the model as a cross-check.
3. **Every extracted block keeps its origin**: source file, page number and position on the page. This origin travels with the block through every later step and is what V-1 cites.
4. **Each page gets a confidence flag.** Pages where the model reports uncertainty, or where its output disagrees substantially with the embedded text, are listed for the admin (A-3).
5. **Original files are kept unchanged**, along with the admin's rights confirmation for each upload (PRD section 8).

### Building the topic graph

6. **The topic tree is proposed by a model, approved by a person.** The model reads the syllabus (if uploaded) and the textbook's chapter structure and proposes subject → chapter → topic → sub-topic, plus prerequisite links. Nothing downstream runs until the admin approves the tree (A-4).
7. **Stored as a graph in PostgreSQL**: a `topic` table (with parent link for the hierarchy) and a `topic_prerequisite` table (edges). The prerequisite graph must have no cycles; this is enforced on save.
8. **Content is attached to topics**, not found by search alone. Each extracted block is assigned to one or more topics. Writing a script for a topic starts from the blocks assigned to it; embedding search is used only to pull in supporting material from elsewhere.
9. **Past-paper questions become structured records**: question text, options, correct answer, year, exam, and topic links, each with a confidence value. Low-confidence mappings go to the admin (A-5). The count of past questions per topic is stored as the topic's exam weight (P-4).

## Alternatives considered

| Alternative | Why not |
|---|---|
| Traditional text extraction and character recognition only | Cheap, but loses equations, reading order in multi-column pages, and figure meaning. Errors here would spread into every video. |
| A specialist document-parsing service | Viable and may be cheaper per page. Kept as a fallback behind the same interface; the vision-model route is chosen first because it handles equations, diagrams and Hindi text in one step. To be confirmed by a test on real pilot pages. |
| Skip the topic tree; search the whole book when writing each video | Simple, but gives no structure for prerequisites, playlists, mastery or exam weighting, all of which the PRD requires. |
| Admin builds the topic tree by hand | Accurate but slow; PRD goal 1 is to avoid this. The admin edits a proposal instead. |
| Graph database | The graph is small. See ADR 0002. |

## Consequences

- Extraction costs model usage per page. A 400-page book is hundreds of calls, done once per book and cached; changed pages only are re-read when a new edition arrives (A-7).
- Page-level origin makes the reviewer's side-by-side screen (V-6) and source citations (V-1) straightforward.
- Admin approval of the tree is a deliberate stop in the pipeline. It adds waiting time but prevents a bad tree producing hundreds of bad videos.
- Prerequisite links proposed by a model will contain mistakes. The admin screen must make them easy to see and fix, and ADR 0006 must tolerate an imperfect graph.

## Revisit if

- The extraction test on real pilot pages shows more than about 5% of pages need manual correction: try a specialist parsing service or a combined approach.
- The PRD adds source types other than PDF (slides, web pages, existing video).
- Content rights (PRD open question 5) restrict storing or reproducing source text or figures, which would change what blocks we keep and show.
