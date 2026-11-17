import { render, screen, within } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { api } from "../api/client";
import type { Course, Topic } from "../api/types";
import { CoursePage } from "./CoursePage";

const course: Course = {
  id: "c1",
  title: "Mechanics",
  subject: "Physics",
  level: "Class 11",
  programme: { id: "p1", title: "Test programme" },
};

const topics: Topic[] = [
  { id: "t-third", parent_id: "t-root", title: "Third law", position: 2, lesson: null },
  { id: "t-root", parent_id: null, title: "Laws of motion", position: 1, lesson: null },
  {
    id: "t-second",
    parent_id: "t-root",
    title: "Second law",
    position: 1,
    lesson: { id: "l1", format: "tutorial", title: "Second law", estimated_minutes: 12 },
  },
];

function renderPage() {
  return render(
    <MemoryRouter initialEntries={["/courses/c1"]} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <Routes>
        <Route path="/courses/:courseId" element={<CoursePage />} />
      </Routes>
    </MemoryRouter>,
  );
}

afterEach(() => vi.restoreAllMocks());

describe("CoursePage topic tree", () => {
  it("nests topics in order and shows which have a lesson", async () => {
    vi.spyOn(api, "courses").mockResolvedValue([course]);
    vi.spyOn(api, "courseTopics").mockResolvedValue(topics);
    renderPage();

    const nav = await screen.findByRole("navigation", { name: "Topics" });
    expect(screen.getByRole("heading", { level: 1, name: "Mechanics" })).toBeInTheDocument();
    expect(api.courseTopics).toHaveBeenCalledWith("c1");

    const root = within(nav).getByText("Laws of motion").closest("li") as HTMLElement;
    const children = within(root).getAllByRole("listitem");
    expect(children.map((item) => item.querySelector(".topic-title")?.textContent)).toEqual([
      "Second law",
      "Third law",
    ]);

    const link = within(nav).getByRole("link", { name: /Second law/ });
    expect(link).toHaveAttribute("href", "/lesson/l1");
    expect(link).toHaveTextContent("Lesson ready · 12 min read");

    const third = children[1] as HTMLElement;
    expect(within(third).queryByRole("link")).toBeNull();
    expect(third).toHaveTextContent("Lesson coming");
    // A group heading with children is not marked as waiting for a lesson.
    expect(root.querySelector(":scope > .topic-row")).not.toHaveTextContent("Lesson coming");
  });

  it("says when the course does not exist", async () => {
    vi.spyOn(api, "courses").mockResolvedValue([]);
    vi.spyOn(api, "courseTopics").mockResolvedValue([]);
    renderPage();
    expect(await screen.findByRole("heading", { name: "Course not found" })).toBeInTheDocument();
  });
});
