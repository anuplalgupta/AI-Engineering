import type { Root } from "mdast";
import { Fragment, type ReactNode } from "react";
import ReactMarkdown, { type Components, type Options as MarkdownOptions } from "react-markdown";
import rehypeKatex from "rehype-katex";
import rehypeSanitize, { defaultSchema, type Options as SanitizeSchema } from "rehype-sanitize";
import remarkMath from "remark-math";
import { visit } from "unist-util-visit";
import type { VFile } from "vfile";

// Raw HTML in Markdown is never rendered (react-markdown drops it), and the tree is
// sanitised before KaTeX runs, so only KaTeX's own markup is added after the clean-up.
const codeAttributes = (defaultSchema.attributes?.code ?? []).filter(
  (attribute) => !(Array.isArray(attribute) && attribute[0] === "className"),
);
const sanitizeSchema: SanitizeSchema = {
  ...defaultSchema,
  attributes: {
    ...defaultSchema.attributes,
    code: [...codeAttributes, ["className", /^language-./, "math-inline", "math-display"]],
  },
};

// The lesson format says $$...$$ is display maths. remark-math treats $$...$$ written
// inside a line of text as inline maths, so mark those for display typesetting.
function remarkDoubleDollarDisplay() {
  return (tree: Root, file: VFile) => {
    const source = String(file);
    visit(tree, "inlineMath", (node) => {
      const start = node.position?.start.offset;
      if (start === undefined || !source.startsWith("$$", start)) return;
      node.data = {
        ...node.data,
        hProperties: { className: ["language-math", "math-display"] },
      };
    });
  };
}

const remarkPlugins: MarkdownOptions["remarkPlugins"] = [remarkMath, remarkDoubleDollarDisplay];
const rehypePlugins: MarkdownOptions["rehypePlugins"] = [
  [rehypeSanitize, sanitizeSchema],
  [rehypeKatex, { throwOnError: false, strict: "ignore", errorColor: "#b42318" }],
];

function ExternalLink({ href, children }: { href?: string; children?: ReactNode }) {
  return (
    <a href={href} target="_blank" rel="noopener noreferrer">
      {children}
    </a>
  );
}

const blockComponents: Components = { a: ExternalLink };
// For text that sits inside a table cell or list item: no wrapping paragraph.
const inlineComponents: Components = { a: ExternalLink, p: ({ children }) => <Fragment>{children}</Fragment> };

interface MarkdownProps {
  source: string;
  inline?: boolean;
}

export function Markdown({ source, inline = false }: MarkdownProps) {
  const content = (
    <ReactMarkdown
      remarkPlugins={remarkPlugins}
      rehypePlugins={rehypePlugins}
      components={inline ? inlineComponents : blockComponents}
    >
      {source}
    </ReactMarkdown>
  );
  return inline ? <span className="md md-inline">{content}</span> : <div className="md">{content}</div>;
}
