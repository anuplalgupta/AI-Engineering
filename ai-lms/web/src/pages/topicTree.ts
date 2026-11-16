import type { Topic } from "../api/types";

export interface TopicNode {
  topic: Topic;
  children: TopicNode[];
}

/** Turns the flat topic list into a tree ordered by position. */
export function buildTopicTree(topics: Topic[]): TopicNode[] {
  const nodes = new Map<string, TopicNode>();
  for (const topic of topics) nodes.set(topic.id, { topic, children: [] });

  const roots: TopicNode[] = [];
  for (const node of nodes.values()) {
    const parent = node.topic.parent_id === null ? undefined : nodes.get(node.topic.parent_id);
    // A topic whose parent is missing is shown at the top rather than lost.
    if (parent && parent !== node) parent.children.push(node);
    else roots.push(node);
  }

  const byPosition = (a: TopicNode, b: TopicNode) =>
    a.topic.position - b.topic.position || a.topic.title.localeCompare(b.topic.title);
  const sort = (list: TopicNode[]) => {
    list.sort(byPosition);
    for (const node of list) sort(node.children);
  };
  sort(roots);
  return roots;
}
