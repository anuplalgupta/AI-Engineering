import { Link } from "react-router-dom";
import { api } from "../api/client";
import { usePageTitle } from "../components/Layout";
import { useAsync } from "../components/useAsync";

export function CoursesPage() {
  usePageTitle("Courses");
  const { loading, data: courses, error } = useAsync(() => api.courses(), []);

  return (
    <div className="page">
      <h1>Courses</h1>
      {loading ? (
        <p className="status" role="status">
          Loading courses…
        </p>
      ) : null}
      {error ? (
        <p className="notice notice--error" role="alert">
          {error}
        </p>
      ) : null}
      {courses && courses.length === 0 ? <p className="notice">There are no courses yet.</p> : null}
      {courses && courses.length > 0 ? (
        <ul className="plain-list course-list">
          {courses.map((course) => (
            <li key={course.id}>
              <Link to={`/courses/${encodeURIComponent(course.id)}`} className="course-card">
                <span className="course-card-title">{course.title}</span>
                <span className="course-card-meta">
                  {[course.subject, course.level].filter(Boolean).join(" · ")}
                </span>
                <span className="course-card-meta">Programme: {course.programme.title}</span>
              </Link>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
