import type {
  AppConfig,
  AuthResponse,
  Course,
  DemoLoginBody,
  Health,
  Lesson,
  RequestCodeBody,
  Topic,
  User,
  VerifyCodeBody,
} from "./types";

export class ApiError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

let onUnauthorised: (() => void) | null = null;

/** Called when a signed-in request comes back 401 (the session has ended). */
export function setUnauthorisedHandler(handler: (() => void) | null): void {
  onUnauthorised = handler;
}

function messageFrom(body: unknown, status: number): string {
  if (typeof body === "object" && body !== null && "detail" in body) {
    const detail = (body as { detail: unknown }).detail;
    if (typeof detail === "string") return detail;
  }
  if (status === 0) return "Could not reach the server. Check your connection and try again.";
  if (status === 422) return "Please check what you entered and try again.";
  return `Something went wrong (error ${status}).`;
}

interface RequestOptions {
  body?: unknown;
  // Auth calls handle their own 401s.
  notifyUnauthorised?: boolean;
}

async function request<T>(method: string, path: string, options: RequestOptions = {}): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`/api${path}`, {
      method,
      credentials: "same-origin",
      headers: {
        Accept: "application/json",
        ...(options.body === undefined ? {} : { "Content-Type": "application/json" }),
      },
      body: options.body === undefined ? undefined : JSON.stringify(options.body),
    });
  } catch {
    throw new ApiError(0, messageFrom(null, 0));
  }

  if (response.status === 204) return undefined as T;

  let parsed: unknown = null;
  try {
    parsed = await response.json();
  } catch {
    parsed = null;
  }

  if (!response.ok) {
    if (response.status === 401 && options.notifyUnauthorised !== false) onUnauthorised?.();
    throw new ApiError(response.status, messageFrom(parsed, response.status));
  }
  return parsed as T;
}

const seg = (value: string) => encodeURIComponent(value);

export const api = {
  health: () => request<Health>("GET", "/health"),
  config: () => request<AppConfig>("GET", "/config"),

  requestCode: (body: RequestCodeBody) =>
    request<void>("POST", "/auth/request-code", { body, notifyUnauthorised: false }),
  verifyCode: (body: VerifyCodeBody) =>
    request<AuthResponse>("POST", "/auth/verify-code", { body, notifyUnauthorised: false }),
  demoLogin: (body: DemoLoginBody) =>
    request<AuthResponse>("POST", "/auth/demo-login", { body, notifyUnauthorised: false }),
  logout: () => request<void>("POST", "/auth/logout", { notifyUnauthorised: false }),
  me: () => request<User>("GET", "/me", { notifyUnauthorised: false }),

  courses: () => request<Course[]>("GET", "/courses"),
  courseTopics: (courseId: string) => request<Topic[]>("GET", `/courses/${seg(courseId)}/topics`),
  lesson: (lessonId: string) => request<Lesson>("GET", `/lessons/${seg(lessonId)}`),
};

/** URL of a stored file. Slashes in the key are kept as path separators. */
export function mediaUrl(key: string): string {
  return `/api/media/${key.split("/").map(encodeURIComponent).join("/")}`;
}
