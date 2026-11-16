import { useEffect } from "react";
import { Link, Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

export function usePageTitle(title: string | null | undefined): void {
  useEffect(() => {
    document.title = title ? `${title} · AI-LMS` : "AI-LMS";
  }, [title]);
}

function Header() {
  const { user, signOut } = useAuth();
  return (
    <header className="app-header">
      <div className="app-header-inner">
        <Link to="/" className="brand">
          AI-LMS
        </Link>
        {user ? (
          <div className="account">
            <div className="account-who">
              <span className="account-name" title={user.email}>
                {user.display_name}
              </span>
              <span className="account-role">
                <span className="visually-hidden">Role: </span>
                {user.role}
              </span>
            </div>
            <button type="button" className="button button--small" onClick={() => void signOut()}>
              Sign out
            </button>
          </div>
        ) : null}
      </div>
    </header>
  );
}

/** Banner, header and the page. Shows a start-up state until /config and /me have answered. */
export function Layout() {
  const { loading, startError, config, retry } = useAuth();

  return (
    <>
      <a className="skip-link" href="#main">
        Skip to content
      </a>
      {config?.banner ? (
        <p className="banner" role="note">
          {config.banner}
        </p>
      ) : null}
      <Header />
      <main id="main" className="page-outer">
        {loading ? (
          <div className="page">
            <p className="status" role="status">
              Loading…
            </p>
          </div>
        ) : startError ? (
          <div className="page page--narrow">
            <h1>Cannot reach the server</h1>
            <p className="notice notice--error" role="alert">
              {startError}
            </p>
            <button type="button" className="button button--primary" onClick={retry}>
              Try again
            </button>
          </div>
        ) : (
          <Outlet />
        )}
      </main>
    </>
  );
}

/** Pages below this need a session; others go to sign-in and come back afterwards. */
export function RequireAuth() {
  const { user } = useAuth();
  const location = useLocation();
  if (!user) {
    return <Navigate to="/sign-in" replace state={{ from: `${location.pathname}${location.search}` }} />;
  }
  return <Outlet />;
}
