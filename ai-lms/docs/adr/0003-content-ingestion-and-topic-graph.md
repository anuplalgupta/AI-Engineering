# ADR 0003: Content ingestion and the topic graph

| | |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-11-16 |
| **PRD requirements** | A-2, A-3, A-4, A-5, A-7, V-1, P-1, P-4, X-7, X-8, section 8 (copyright, poor extraction) |
| **Amended by** | [ADR 0008](0008-consistency-after-0007-and-demo-mode.md) (proposed): "scripts" and "videos" read as lesson content and lessons; changes to an approved tree |

## Context

Everything downstream depends on reading the uploaded PDFs correctly: scripts are written from them, questions are drawn from them, and every claim in a video must point back to a page (V-1). The material is hard to read by machine. Physics and chemistry pages are full of equations, diagrams, tables and multi-column layouts, and many Indian textbooks and past papers circulate as scans.

The topic tree with prerequisite links (A-4) is the backbone of the product. Videos, questions, mastery and playlists all hang off it.

## Decision

### Reading the PDFs

1. **Process page by page.** Each page is turned into an image and also has its embedded text extracted where present.
2. **Each page is converted into structured text**: Markdown for prose, LaTeX for equations, described figures (with the figure cropped and stored as an image), and tables. The embedded text, where available, is used as a cross-check.
3. **Two interchangeable extractors sit behind one interface, chosen by configuration** (X-7):
   - a **vision-capable language model**, which costs model usage per page;
   - a **free, open-source document parser run locally**, which costs nothing but computer time.

   Both produce the same block format. A test on real pilot pages compares them on equations, reading order, figures and scanned pages, and decides which is the default. Either can be used for a whole book or only for pages the other handled badly.
4. **Every extracted block keeps its origin**: source file, page number and position on the page. This origin travels with the block through every later step and is what V-1 cites.
5. **Blocks that continue across pages are joined.** After extraction, a joining step merges a derivation, worked example, table or paragraph that runs onto the next page into one block. The joined block keeps every page reference it came from.
6. **Each page gets a confidence flag.** Pages where the extractor reports uncertainty, or where its output disagrees substantially with the embedded text, are listed for the admin (A-3).
7. **Original files are kept unchanged**, along with the admin's rights confirmation for each upload (PRD section 8).
8. **Sample and test content comes from openly licensed sources** until content rights are settled (PRD open question 5). The sample course included with the demo (X-8) is built from an openly licensed textbook (for example an OpenStax physics title), with its licence and attribution recorded. Sample questions are newly written or generated and reviewed; past exam papers are not included in the sample data.

### Building the topic graph

9. **The topic tree is proposed by a model, approved by a person.** The model reads the syllabus (if uploaded) and the textbook's chapter structure and proposes subject → chapter → topic → sub-topic, plus prerequisite links. Nothing downstream runs until the admin approves the tree (A-4).
10. **Stored as a graph in PostgreSQL**: a `topic` table (with parent link for the hierarchy) and a `topic_prerequisite` table (edges). The prerequisite graph must have no cycles; this is enforced on save.
11. **Content is attached to topics**, not found by search alone. Each extracted block is assigned to one or more topics. Writing a script for a topic starts from the blocks assigned to it; embedding search is used only to pull in supporting material from elsewhere.
12. **Past-paper questions become structured records**: question text, options, correct answer, year, exam, and topic links, each with a confidence value. Low-confidence mappings go to the admin (A-5). The count of past questions per topic is stored as the topic's exam weight (P-4).

## Alternatives considered

| Alternative | Why not |
|---|---|
| Traditional text extraction and character recognition only | Cheap, but loses equations, reading order in multi-column pages, and figure meaning. Errors here would spread into every video. |
| A paid specialist document-parsing service | Viable, and can be added as a third extractor behind the same interface. Not needed while a free local parser and a vision model are both available. |
| Vision model only, no free route | Simplest, but every page costs money and nothing can be extracted without a provider account, against X-7. |
| Strict page-by-page blocks with no joining | Simpler, but splits derivations and tables in two, which damages scripts and questions written from them. |
| Skip the topic tree; search the whole book when writing each video | Simple, but gives no structure for prerequisites, playlists, mastery or exam weighting, all of which the PRD requires. |
| Admin builds the topic tree by hand | Accurate but slow; PRD goal 1 is to avoid this. The admin edits a proposal instead. |
| Graph database | The graph is small. See ADR 0002. |

## Consequences

- With the vision model, extraction costs model usage per page: a 400-page book is hundreds of calls. With the local parser it costs nothing but is slow on a small machine. Either way it is done once per book and cached; changed pages only are re-read when a new edition arrives (A-7).
- Two extractors mean two sets of quirks to test, and the shared block format must be strict enough that later steps cannot tell which one produced a block.
- Sample content from an openly licensed textbook will not match the JEE syllabus exactly. It proves the pipeline; the real pilot content still depends on the rights question.
- Page-level origin makes the reviewer's side-by-side screen (V-6) and source citations (V-1) straightforward.
- Admin approval of the tree is a deliberate stop in the pipeline. It adds waiting time but prevents a bad tree producing hundreds of bad videos.
- Prerequisite links proposed by a model will contain mistakes. The admin screen must make them easy to see and fix, and ADR 0006 must tolerate an imperfect graph.

## Revisit if

- The extraction test on real pilot pages shows more than about 5% of pages need manual correction with the better of the two extractors: combine them page by page, or add a paid specialist parsing service.
- The PRD adds source types other than PDF (slides, web pages, existing video).
- Content rights (PRD open question 5) restrict storing or reproducing source text or figures, which would change what blocks we keep and show.
