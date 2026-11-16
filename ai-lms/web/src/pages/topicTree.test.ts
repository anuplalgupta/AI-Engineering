import { describe, expect, it } from "vitest";
import type { Topic } from "../api/types";
import { buildTopicTree } from "./topicTree";

const topic = (id: string, parent_id: string | null, position: number): Topic => ({
  id,
  parent_id,
  title: id,
  position,
  lesson: null,
});

describe("buildTopicTree", () => {
  it("nests children under parents and orders by position", () => {
    const tree = buildTopicTree([
      topic("b", null, 2),
      topic("a2", "a", 2),
      topic("a", null, 1),
      topic("a1", "a", 1),
    ]);
    expect(tree.map((node) => node.topic.id)).toEqual(["a", "b"]);
    expect(tree[0]?.children.map((node) => node.topic.id)).toEqual(["a1", "a2"]);
  });

  it("keeps a topic whose parent is missing", () => {
    const tree = buildTopicTree([topic("orphan", "gone", 1)]);
    expect(tree.map((node) => node.topic.id)).toEqual(["orphan"]);
  });
});
