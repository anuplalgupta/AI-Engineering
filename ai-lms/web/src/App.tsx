import { Suspense, lazy } from "react";
import { Link, Navigate, Route, Routes } from "react-router-dom";
import { Layout, RequireAuth, usePageTitle } from "./components/Layout";
import { CoursePage } from "./pages/CoursePage";
import { CoursesPage } from "./pages/CoursesPage";
import { SignInPage } from "./pages/SignInPage";

// The reader carries the Markdown and maths libraries, so it is loaded only when a lesson is opened.
const LessonPage = lazy(() => import("./pages/LessonPage").then((module) => ({ default: module.LessonPage })));

function LessonRoute() {
  return (
    <Suspense
      fallback={
        <div className="page">
          <p className="status" role="status">
            Loading lesson…
          </p>
        </div>
      }
    >
      <LessonPage />
    </Suspense>
  );
}

function NotFoundPage() {
  usePageTitle("Page not found");
  return (
    <div className="page page--narrow">
      <h1>Page not found</h1>
      <p className="page-lead">That address does not lead anywhere.</p>
      <Link to="/courses" className="button button--primary">
        Go to courses
      </Link>
    </div>
  );
}

export function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/sign-in" element={<SignInPage />} />
        <Route element={<RequireAuth />}>
          <Route path="/" element={<Navigate to="/courses" replace />} />
          <Route path="/courses" element={<CoursesPage />} />
          <Route path="/courses/:courseId" element={<CoursePage />} />
          <Route path="/lesson/:lessonId" element={<LessonRoute />} />
        </Route>
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
}
