import { useId, useState, type FormEvent } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { api } from "../api/client";
import type { Role } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { usePageTitle } from "../components/Layout";

const DEMO_ROLES: Role[] = ["student", "reviewer", "admin"];
const MAIL_VIEWER_URL = "http://localhost:8025";

function isLocalUse(): boolean {
  const host = window.location.hostname;
  return host === "localhost" || host === "127.0.0.1" || host === "[::1]" || host.endsWith(".localhost");
}

function errorText(error: unknown): string {
  return error instanceof Error ? error.message : "Something went wrong. Please try again.";
}

function DemoEntry({ accessCodeRequired }: { accessCodeRequired: boolean }) {
  const { setUser } = useAuth();
  const [accessCode, setAccessCode] = useState("");
  const [busyRole, setBusyRole] = useState<Role | null>(null);
  const [error, setError] = useState<string | null>(null);
  const codeId = useId();

  async function enter(role: Role) {
    if (accessCodeRequired && accessCode.trim() === "") {
      setError("Enter the access code first.");
      return;
    }
    setBusyRole(role);
    setError(null);
    try {
      const { user } = await api.demoLogin(
        accessCodeRequired ? { role, access_code: accessCode.trim() } : { role },
      );
      setUser(user);
    } catch (caught) {
      setError(errorText(caught));
      setBusyRole(null);
    }
  }

  return (
    <section className="card" aria-labelledby="demo-heading">
      <h2 id="demo-heading">Try the demo</h2>
      <p>Enter with a ready-made demo account. No email needed.</p>
      {accessCodeRequired ? (
        <div className="field">
          <label htmlFor={codeId}>Access code</label>
          <input
            id={codeId}
            type="password"
            autoComplete="off"
            value={accessCode}
            onChange={(event) => setAccessCode(event.target.value)}
          />
        </div>
      ) : null}
      {error ? (
        <p className="notice notice--error" role="alert">
          {error}
        </p>
      ) : null}
      <div className="stack">
        {DEMO_ROLES.map((role) => (
          <button
            key={role}
            type="button"
            className={`button button--block ${role === "student" ? "button--primary" : ""}`}
            disabled={busyRole !== null}
            onClick={() => void enter(role)}
          >
            {busyRole === role ? "Entering…" : `Enter as demo ${role}`}
          </button>
        ))}
      </div>
    </section>
  );
}

function EmailCodeSignIn({ signupOpen }: { signupOpen: boolean }) {
  const { setUser } = useAuth();
  const [step, setStep] = useState<"email" | "code">("email");
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const emailId = useId();
  const codeId = useId();

  async function sendCode(event?: FormEvent) {
    event?.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api.requestCode({ email: email.trim() });
      setCode("");
      setStep("code");
    } catch (caught) {
      setError(errorText(caught));
    } finally {
      setBusy(false);
    }
  }

  async function verify(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const { user } = await api.verifyCode({ email: email.trim(), code: code.trim() });
      setUser(user);
    } catch (caught) {
      setError(errorText(caught));
      setBusy(false);
    }
  }

  const heading = signupOpen ? "Sign in or create an account" : "Sign in with your email";

  return (
    <section className="card" aria-labelledby="email-heading">
      <h2 id="email-heading">{heading}</h2>

      {step === "email" ? (
        <form onSubmit={(event) => void sendCode(event)} noValidate={false}>
          <p>
            {signupOpen
              ? "Enter your email and we will send you a one-time code. If you are new, an account is created for you."
              : "Enter your email and we will send you a one-time code."}
          </p>
          <div className="field">
            <label htmlFor={emailId}>Email</label>
            <input
              id={emailId}
              type="email"
              inputMode="email"
              autoComplete="email"
              autoCapitalize="none"
              spellCheck={false}
              required
              value={email}
              onChange={(event) => setEmail(event.target.value)}
            />
          </div>
          {error ? (
            <p className="notice notice--error" role="alert">
              {error}
            </p>
          ) : null}
          <button type="submit" className="button button--primary button--block" disabled={busy}>
            {busy ? "Sending…" : "Send me a code"}
          </button>
        </form>
      ) : (
        <form onSubmit={(event) => void verify(event)}>
          <p className="notice notice--info" role="status">
            We sent a code to <strong>{email.trim()}</strong>
            {signupOpen ? "." : ", if that email has an account."}
          </p>
          {isLocalUse() ? (
            <p className="field-hint">
              Running on this computer: the email appears in the local mail viewer at{" "}
              <a href={MAIL_VIEWER_URL} target="_blank" rel="noopener noreferrer">
                {MAIL_VIEWER_URL}
              </a>
              . Nothing is sent outside this machine.
            </p>
          ) : null}
          <div className="field field--spaced">
            <label htmlFor={codeId}>One-time code</label>
            <input
              id={codeId}
              className="code-input"
              type="text"
              inputMode="numeric"
              autoComplete="one-time-code"
              autoFocus
              required
              maxLength={12}
              value={code}
              onChange={(event) => setCode(event.target.value)}
            />
          </div>
          {error ? (
            <p className="notice notice--error" role="alert">
              {error}
            </p>
          ) : null}
          <button type="submit" className="button button--primary button--block" disabled={busy}>
            {busy ? "Checking…" : "Sign in"}
          </button>
          <div className="stack stack--spaced">
            <button type="button" className="button button--link" disabled={busy} onClick={() => void sendCode()}>
              Send a new code
            </button>
            <button
              type="button"
              className="button button--link"
              disabled={busy}
              onClick={() => {
                setStep("email");
                setError(null);
              }}
            >
              Use a different email
            </button>
          </div>
        </form>
      )}
    </section>
  );
}

export function SignInPage() {
  const { user, config } = useAuth();
  const location = useLocation();
  usePageTitle("Sign in");

  if (user) {
    const from = (location.state as { from?: unknown } | null)?.from;
    // Only ever return to a path inside this app.
    const target = typeof from === "string" && from.startsWith("/") && !from.startsWith("//") ? from : "/courses";
    return <Navigate to={target} replace />;
  }

  return (
    <div className="page page--narrow">
      <h1>Welcome</h1>
      <p className="page-lead">Lessons, practice and a study plan built around your textbook.</p>
      {config?.demo_mode ? <DemoEntry accessCodeRequired={config.access_code_required} /> : null}
      <EmailCodeSignIn signupOpen={config?.signup_open ?? false} />
    </div>
  );
}
