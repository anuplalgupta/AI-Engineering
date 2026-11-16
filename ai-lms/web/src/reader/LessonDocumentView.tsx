import "katex/dist/katex.min.css";
import "./reader.css";
import { mediaUrl } from "../api/client";
import type { LessonDocument, Section, SectionSource, SectionType } from "../api/types";
import { Markdown } from "./Markdown";

export const SUPPORTED_SCHEMA_VERSION = 1;

// Heading used when a section has no title of its own. Null means no heading.
const DEFAULT_TITLES: Record<SectionType, string | null> = {
  explanation: null,
  derivation: "Derivation",
  worked_example: "Worked example",
  diagram: null,
  table: null,
  key_points: "Key points",
  common_mistakes: "Common mistakes",
  summary: "Summary",
};

// Small label shown above the title, where it adds information.
const KICKERS: Partial<Record<SectionType, string>> = {
  derivation: "Derivation",
  worked_example: "Worked example",
};

function formatPages(pages: number[]): string {
  if (pages.length === 0) return "";
  const sorted = [...pages].sort((a, b) => a - b);
  const ranges: string[] = [];
  let start = sorted[0] as number;
  let end = start;
  for (const page of sorted.slice(1)) {
    if (page === end || page === end + 1) {
      end = page;
      continue;
    }
    ranges.push(start === end ? `${start}` : `${start}–${end}`);
    start = end = page;
  }
  ranges.push(start === end ? `${start}` : `${start}–${end}`);
  return `${sorted.length === 1 ? "p." : "pp."} ${ranges.join(", ")}`;
}

function Sources({ sources }: { sources: SectionSource[] }) {
  if (sources.length === 0) return null;
  return (
    <p className="section-sources">
      <span className="section-sources-label">{sources.length === 1 ? "Source: " : "Sources: "}</span>
      {sources.map((source, index) => (
        <span key={`${source.source_title}-${index}`}>
          {index > 0 ? "; " : ""}
          <cite>{source.source_title}</cite>
          {source.pages.length > 0 ? `, ${formatPages(source.pages)}` : ""}
        </span>
      ))}
    </p>
  );
}

function SectionView({ section }: { section: Section }) {
  const headingId = `section-${section.id}-title`;
  const known = section.type in DEFAULT_TITLES;
  const title = section.title ?? (known ? DEFAULT_TITLES[section.type] : null);
  const kicker = section.title ? KICKERS[section.type] : undefined;
  const { body_md: body, steps, image, table, items } = section;

  return (
    <section
      id={`section-${section.id}`}
      className={`lesson-section lesson-section--${known ? section.type : "unknown"}`}
      data-section-type={section.type}
      aria-labelledby={title ? headingId : undefined}
    >
      {kicker ? <p className="section-kicker">{kicker}</p> : null}
      {title ? (
        <h2 id={headingId} className="section-title">
          {title}
        </h2>
      ) : null}

      {body ? <Markdown source={body} /> : null}

      {image ? (
        <figure className="diagram">
          <img src={mediaUrl(image.key)} alt={image.alt} loading="lazy" decoding="async" />
          {image.caption ? (
            <figcaption>
              <Markdown source={image.caption} inline />
            </figcaption>
          ) : null}
        </figure>
      ) : null}

      {steps && steps.length > 0 ? (
        <ol className="steps">
          {steps.map((step) => (
            <li key={step.id} id={`step-${section.id}-${step.id}`} className="step">
              <Markdown source={step.body_md} />
            </li>
          ))}
        </ol>
      ) : null}

      {table ? (
        // The table scrolls inside this box; the page itself never scrolls sideways.
        <div
          className="scroll-box table-scroll"
          role="region"
          aria-label={title ? `Table: ${title}` : "Table"}
          tabIndex={0}
        >
          <table>
            <thead>
              <tr>
                {table.headers.map((header, index) => (
                  <th key={index} scope="col">
                    <Markdown source={header} inline />
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {table.rows.map((row, rowIndex) => (
                <tr key={rowIndex}>
                  {row.map((cell, cellIndex) => (
                    <td key={cellIndex}>
                      <Markdown source={cell} inline />
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}

      {items && items.length > 0 ? (
        <ul className="items">
          {items.map((item, index) => (
            <li key={index}>
              <Markdown source={item} inline />
            </li>
          ))}
        </ul>
      ) : null}

      <Sources sources={section.sources ?? []} />
    </section>
  );
}

export function LessonDocumentView({ document }: { document: LessonDocument }) {
  if ((document.schema_version as number) !== SUPPORTED_SCHEMA_VERSION) {
    return (
      <p role="alert" className="notice notice--error">
        This lesson was saved in a newer format than this app can show. Please reload the page to
        get the latest version of the app.
      </p>
    );
  }
  return (
    <div className="lesson-document">
      {document.sections.map((section) => (
        <SectionView key={section.id} section={section} />
      ))}
    </div>
  );
}
