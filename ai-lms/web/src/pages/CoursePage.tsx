import { useMemo } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api/client";
import { usePageTitle } from "../components/Layout";
import { useAsync } from "../components/useAsync";
import { buildTopicTree, type TopicNode } from "./topicTree";

function minutes(value: number): string {
  return `${value} min read`;
}

function TopicItem({ node, courseId }: { node: TopicNode; courseId: string }) {
  const { topic, children } = node;
  const isGroup = children.length > 0 && !topic.lesson;

  return (
    <li className="topic">
      {topic.lesson ? (
        <Link
          to={`/lesson/${encodeURIComponent(topic.lesson.id)}`}
          state={{ courseId }}
          className="topic-row"
        >
          <span className="topic-title">{topic.title}</span>
          <span className="topic-meta topic-meta--ready">
            Lesson ready · {minutes(topic.lesson.estimated_minutes)}
          </span>
        </Link>
      ) : (
        <div className={`topic-row ${isGroup ? "topic-row--group" : ""}`}>
          <span className="topic-title">{topic.title}</span>
          {isGroup ? null : <span className="topic-meta">Lesson coming</span>}
        </div>
      )}
      {children.length > 0 ? (
        <ul>
          {children.map((child) => (
            <TopicItem key={child.topic.id} node={child} courseId={courseId} />
          ))}
        </ul>
      ) : null}
    </li>
  );
}

export function CoursePage() {
  const { courseId = "" } = useParams();
  const courses = useAsync(() => api.courses(), []);
  const topics = useAsync(() => api.courseTopics(courseId), [courseId]);

  const course = courses.data?.find((candidate) => candidate.id === courseId) ?? null;
  const tree = useMemo(() => (topics.data ? buildTopicTree(topics.data) : []), [topics.data]);
  usePageTitle(course?.title ?? "Course");

  const notFound = topics.status === 404 || (courses.data !== null && course === null);

  return (
    <div className="page">
      <Link to="/courses" className="back-link">
        ← All courses
      </Link>
      {notFound ? (
        <>
          <h1>Course not found</h1>
          <p className="notice">This course does not exist or you do not have access to it.</p>
        </>
      ) : (
        <>
          <h1>{course?.title ?? "Course"}</h1>
          {course ? (
            <p className="page-lead">
              {[course.subject, course.level, course.programme.title].filter(Boolean).join(" · ")}
            </p>
          ) : null}
          {topics.loading ? (
            <p className="status" role="status">
              Loading topics…
            </p>
          ) : null}
          {topics.error ? (
            <p className="notice notice--error" role="alert">
              {topics.error}
            </p>
          ) : null}
          {topics.data && tree.length === 0 ? <p className="notice">This course has no topics yet.</p> : null}
          {tree.length > 0 ? (
            <nav aria-label="Topics">
              <ul className="topic-tree">
                {tree.map((node) => (
                  <TopicItem key={node.topic.id} node={node} courseId={courseId} />
                ))}
              </ul>
            </nav>
          ) : null}
        </>
      )}
    </div>
  );
}
