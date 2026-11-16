import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { LessonDocument, Section, SectionType } from "../api/types";
import { fixtureLesson } from "../fixtures/lesson";
import { LessonDocumentView } from "./LessonDocumentView";
import { Markdown } from "./Markdown";

const ALL_TYPES: SectionType[] = [
  "explanation",
  "derivation",
  "worked_example",
  "diagram",
  "table",
  "key_points",
  "common_mistakes",
  "summary",
];

function renderFixture() {
  return render(<LessonDocumentView document={fixtureLesson.document} />);
}

function sectionOf(container: HTMLElement, type: SectionType): HTMLElement {
  const element = container.querySelector<HTMLElement>(`[data-section-type="${type}"]`);
  if (!element) throw new Error(`No section of type ${type}`);
  return element;
}

describe("LessonDocumentView", () => {
  it("renders every section type in the contract", () => {
    const { container } = renderFixture();
    for (const type of ALL_TYPES) {
      expect(sectionOf(container, type)).toBeInTheDocument();
    }
    expect(container.querySelectorAll(".lesson-section")).toHaveLength(fixtureLesson.document.sections.length);
  });

  it("renders an explanation as Markdown prose", () => {
    const { container } = renderFixture();
    const section = sectionOf(container, "explanation");
    expect(within(section).getByRole("heading", { name: "Force changes motion" })).toBeInTheDocument();
    expect(within(section).getByText("net force").tagName).toBe("STRONG");
  });

  it("typesets inline and display equations with KaTeX", () => {
    const { container } = renderFixture();
    const section = sectionOf(container, "explanation");
    expect(section.querySelectorAll(".katex").length).toBeGreaterThan(1);
    // $$...$$ becomes a display equation, which gets its own scrolling box.
    expect(section.querySelector(".katex-display")).not.toBeNull();
    expect(section.querySelector(".katex-error")).toBeNull();
    // The raw LaTeX is kept for screen readers and copy, not left as loose text.
    const latex = [...section.querySelectorAll("annotation")].map((node) => node.textContent);
    expect(latex).toContain("\\vec{a}");
  });

  it("renders $$...$$ on its own fenced lines as a display equation too", () => {
    const { container } = render(<Markdown source={"Before\n\n$$\nE = mc^2\n$$\n\nAfter"} />);
    expect(container.querySelector(".katex-display")).not.toBeNull();
  });

  it("keeps single-dollar maths inline", () => {
    const { container } = render(<Markdown source={"Energy is $E = mc^2$ here."} />);
    expect(container.querySelector(".katex")).not.toBeNull();
    expect(container.querySelector(".katex-display")).toBeNull();
  });

  it("shows invalid LaTeX as an error mark instead of failing", () => {
    const { container } = render(<Markdown source={"Bad maths: $\\frac{1}{$ end"} />);
    expect(container.querySelector(".katex-error")).not.toBeNull();
    expect(container.textContent).toContain("end");
  });

  it("numbers the steps of a derivation and a worked example", () => {
    const { container } = renderFixture();
    const derivation = sectionOf(container, "derivation");
    const list = within(derivation).getByRole("list");
    expect(list.tagName).toBe("OL");
    expect(within(list).getAllByRole("listitem")).toHaveLength(4);

    const example = sectionOf(container, "worked_example");
    expect(within(example).getByRole("heading", { name: "A block pulled along a rough floor" })).toBeInTheDocument();
    expect(example.querySelectorAll("ol.steps > li")).toHaveLength(3);
  });

  it("loads a diagram from the media endpoint with alt text and caption", () => {
    const { container } = renderFixture();
    const section = sectionOf(container, "diagram");
    const image = within(section).getByRole("img");
    expect(image).toHaveAttribute("src", "/api/media/fixtures/forces-on-block.svg");
    expect(image).toHaveAttribute("alt", expect.stringContaining("A block on a horizontal surface"));
    expect(section.querySelector("figure figcaption")?.textContent).toContain("Figure 1.");
  });

  it("wraps a table in its own scroll container", () => {
    const { container } = renderFixture();
    const section = sectionOf(container, "table");
    const table = within(section).getByRole("table");
    const box = table.parentElement as HTMLElement;
    expect(box).toHaveClass("scroll-box");
    expect(box).toHaveAttribute("role", "region");
    expect(box).toHaveAttribute("tabindex", "0");
    expect(within(table).getAllByRole("columnheader")).toHaveLength(6);
    expect(within(table).getAllByRole("row")).toHaveLength(5);
    // Maths inside a cell is typeset as well.
    expect(table.querySelector("td .katex")).not.toBeNull();
  });

  it("renders key points, common mistakes and summary with default headings", () => {
    const { container } = renderFixture();
    const keyPoints = sectionOf(container, "key_points");
    expect(within(keyPoints).getByRole("heading", { name: "Key points" })).toBeInTheDocument();
    expect(within(keyPoints).getAllByRole("listitem")).toHaveLength(3);

    const mistakes = sectionOf(container, "common_mistakes");
    expect(within(mistakes).getByRole("heading", { name: "Common mistakes" })).toBeInTheDocument();
    expect(within(mistakes).getAllByRole("listitem")).toHaveLength(3);

    const summary = sectionOf(container, "summary");
    expect(within(summary).getByRole("heading", { name: "Summary" })).toBeInTheDocument();
  });

  it("shows the sources of a section with page ranges, and nothing when there are none", () => {
    const { container } = renderFixture();
    expect(sectionOf(container, "explanation").querySelector(".section-sources")?.textContent).toBe(
      "Source: Fixture Physics, Volume 1, pp. 112–113",
    );
    expect(sectionOf(container, "worked_example").querySelector(".section-sources")?.textContent).toContain(
      "pp. 116–118",
    );
    expect(sectionOf(container, "diagram").querySelector(".section-sources")?.textContent).toContain("p. 114");
    expect(sectionOf(container, "common_mistakes").querySelector(".section-sources")).toBeNull();
  });

  it("does not render raw HTML or scripts from Markdown", () => {
    const section: Section = {
      id: "x",
      type: "explanation",
      body_md:
        'Safe text <script>window.hacked = true</script> <img src="x" onerror="window.hacked = true"> [link](javascript:alert(1))',
      sources: [],
    };
    const document: LessonDocument = { schema_version: 1, sections: [section] };
    const { container } = render(<LessonDocumentView document={document} />);
    expect(container.querySelector("script")).toBeNull();
    expect(container.querySelector("img")).toBeNull();
    expect(container.querySelector('a[href^="javascript"]')).toBeNull();
    expect(screen.getByText(/Safe text/)).toBeInTheDocument();
  });

  it("refuses a document in a newer format", () => {
    const document = { schema_version: 2, sections: [] } as unknown as LessonDocument;
    render(<LessonDocumentView document={document} />);
    expect(screen.getByRole("alert")).toHaveTextContent("newer format");
  });
});
