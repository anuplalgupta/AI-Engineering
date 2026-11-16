import { Link, useLocation, useParams } from "react-router-dom";
import { api } from "../api/client";
import { usePageTitle } from "../components/Layout";
import { useAsync } from "../components/useAsync";
import { LessonDocumentView } from "../reader/LessonDocumentView";
import { Markdown } from "../reader/Markdown";

export function LessonPage() {
  const { lessonId = "" } = useParams();
  const location = useLocation();
  const { loading, data: lesson, error, status } = useAsync(() => api.lesson(lessonId), [lessonId]);
  usePageTitle(lesson?.title ?? "Lesson");

  // The lesson does not say which course it belongs to; the course page passes it along.
  const courseId = (location.state as { courseId?: unknown } | null)?.courseId;
  const back =
    typeof courseId === "string"
      ? { to: `/courses/${encodeURIComponent(courseId)}`, label: "← Back to topics" }
      : { to: "/courses", label: "← All courses" };

  return (
    <div className="page">
      <Link to={back.to} className="back-link">
        {back.label}
      </Link>

      {loading ? (
        <p className="status" role="status">
          Loading lesson…
        </p>
      ) : null}

      {error ? (
        status === 404 ? (
          <>
            <h1>Lesson not available</h1>
            <p className="notice">This lesson does not exist or has not been published yet.</p>
          </>
        ) : (
          <p className="notice notice--error" role="alert">
            {error}
          </p>
        )
      ) : null}

      {lesson ? (
        <article>
          <header className="lesson-header">
            <h1>{lesson.title}</h1>
            <p className="lesson-meta">About {lesson.estimated_minutes} min read</p>
          </header>

          <LessonDocumentView document={lesson.document} />

          {lesson.attribution ? (
            <footer className="lesson-attribution">
              <h2>Attribution</h2>
              <Markdown source={lesson.attribution} />
            </footer>
          ) : null}
        </article>
      ) : null}
    </div>
  );
}
