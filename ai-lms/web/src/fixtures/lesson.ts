import type { Lesson } from "../api/types";

// A made-up lesson that uses every section type of lesson document format version 1.
// Used by the component tests and by `npm run dev:mock`. It is not the sample course.
export const fixtureLesson: Lesson = {
  id: "lesson-fixture-1",
  topic_id: "topic-fixture-1",
  title: "Newton's second law of motion",
  format: "tutorial",
  version: 1,
  estimated_minutes: 12,
  attribution:
    "Fixture content written for development. Not taken from any textbook; free to reuse.",
  document: {
    schema_version: 1,
    sections: [
      {
        id: "s-intro",
        type: "explanation",
        title: "Force changes motion",
        body_md:
          "A body keeps its velocity unless a **net force** acts on it. When a net force does act, the body accelerates in the direction of that force.\n\nFor a body of constant mass $m$, the acceleration $\\vec{a}$ is proportional to the net force $\\vec{F}_{\\text{net}}$:\n\n$$\\vec{F}_{\\text{net}} = m\\,\\vec{a}$$\n\nThe unit of force is the newton: $1\\ \\text{N} = 1\\ \\text{kg}\\,\\text{m}\\,\\text{s}^{-2}$.",
        sources: [{ source_title: "Fixture Physics, Volume 1", pages: [112, 113] }],
      },
      {
        id: "s-diagram",
        type: "diagram",
        title: "Forces on a block",
        image: {
          key: "fixtures/forces-on-block.svg",
          alt: "A block on a horizontal surface. An applied force points right, friction points left, weight points down and the normal force points up.",
          caption: "Figure 1. The four forces on a block pulled along a rough horizontal surface.",
        },
        sources: [{ source_title: "Fixture Physics, Volume 1", pages: [114] }],
      },
      {
        id: "s-derivation",
        type: "derivation",
        title: "From momentum to F = ma",
        body_md: "Newton stated the law in terms of momentum $\\vec{p} = m\\vec{v}$.",
        steps: [
          {
            id: "d1",
            body_md:
              "Start from the definition: the net force equals the rate of change of momentum.\n\n$$\\vec{F}_{\\text{net}} = \\frac{d\\vec{p}}{dt}$$",
          },
          {
            id: "d2",
            body_md:
              "Substitute $\\vec{p} = m\\vec{v}$ and use the product rule.\n\n$$\\vec{F}_{\\text{net}} = \\frac{d(m\\vec{v})}{dt} = m\\,\\frac{d\\vec{v}}{dt} + \\vec{v}\\,\\frac{dm}{dt}$$",
          },
          {
            id: "d3",
            body_md:
              "For constant mass, $\\frac{dm}{dt} = 0$, and $\\frac{d\\vec{v}}{dt} = \\vec{a}$, so $\\vec{F}_{\\text{net}} = m\\vec{a}$.",
          },
          {
            id: "d4",
            body_md:
              "Written out in components, with every force on the body listed, the same law is deliberately long so that it has to scroll on a phone:\n\n$$\\sum_{i=1}^{n} F_{i,x} = F_{1,x} + F_{2,x} + F_{3,x} + \\dots + F_{n,x} = m\\,a_x, \\qquad \\sum_{i=1}^{n} F_{i,y} = F_{1,y} + F_{2,y} + F_{3,y} + \\dots + F_{n,y} = m\\,a_y, \\qquad \\sum_{i=1}^{n} F_{i,z} = m\\,a_z$$",
          },
        ],
        sources: [{ source_title: "Fixture Physics, Volume 1", pages: [115] }],
      },
      {
        id: "s-example",
        type: "worked_example",
        title: "A block pulled along a rough floor",
        body_md:
          "A $4.0\\ \\text{kg}$ block is pulled along a floor by a horizontal force of $18\\ \\text{N}$. Friction is $6.0\\ \\text{N}$. Find the acceleration.",
        steps: [
          { id: "e1", body_md: "Net force along the floor: $F_{\\text{net}} = 18 - 6.0 = 12\\ \\text{N}$." },
          { id: "e2", body_md: "Apply the law: $a = \\dfrac{F_{\\text{net}}}{m} = \\dfrac{12}{4.0}$." },
          { id: "e3", body_md: "**Answer:** $a = 3.0\\ \\text{m}\\,\\text{s}^{-2}$ in the direction of the pull." },
        ],
        sources: [{ source_title: "Fixture Physics, Volume 1", pages: [116, 117, 118] }],
      },
      {
        id: "s-table",
        type: "table",
        title: "Quantities and units",
        table: {
          headers: ["Quantity", "Symbol", "SI unit", "Unit in base units", "Vector or scalar", "Typical value in this chapter"],
          rows: [
            ["Force", "$\\vec{F}$", "newton (N)", "$\\text{kg}\\,\\text{m}\\,\\text{s}^{-2}$", "Vector", "1 N to 1000 N"],
            ["Mass", "$m$", "kilogram (kg)", "$\\text{kg}$", "Scalar", "0.1 kg to 100 kg"],
            ["Acceleration", "$\\vec{a}$", "metre per second squared", "$\\text{m}\\,\\text{s}^{-2}$", "Vector", "0 to 20 $\\text{m}\\,\\text{s}^{-2}$"],
            ["Momentum", "$\\vec{p}$", "kilogram metre per second", "$\\text{kg}\\,\\text{m}\\,\\text{s}^{-1}$", "Vector", "0 to 500 $\\text{kg}\\,\\text{m}\\,\\text{s}^{-1}$"],
          ],
        },
        sources: [{ source_title: "Fixture Physics, Volume 1", pages: [119] }],
      },
      {
        id: "s-key",
        type: "key_points",
        items: [
          "Only the **net** force decides the acceleration.",
          "Acceleration is in the direction of the net force.",
          "$F_{\\text{net}} = ma$ holds when the mass is constant.",
        ],
        sources: [{ source_title: "Fixture Physics, Volume 1", pages: [120] }],
      },
      {
        id: "s-mistakes",
        type: "common_mistakes",
        items: [
          "Using one force instead of the net force.",
          "Treating $ma$ as an extra force on the free-body diagram.",
          "Mixing grams and kilograms.",
        ],
        sources: [],
      },
      {
        id: "s-summary",
        type: "summary",
        body_md:
          "A net force gives a body an acceleration in its own direction, with $\\vec{F}_{\\text{net}} = m\\vec{a}$ for constant mass. Draw every force, add them as vectors, then apply the law.",
        sources: [{ source_title: "Fixture Physics, Volume 1", pages: [121] }],
      },
    ],
  },
};
