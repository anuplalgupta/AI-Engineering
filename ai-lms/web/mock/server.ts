// A stand-in for the backend, used only by `npm run dev:mock`.
// It answers the M1 API contract from fixtures so the app can be developed alone.
import { readFileSync } from "node:fs";
import type { IncomingMessage, ServerResponse } from "node:http";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import type { Plugin } from "vite";
import type { AppConfig, Course, Role, Topic, User } from "../src/api/types";
import { fixtureLesson } from "../src/fixtures/lesson";

const here = dirname(fileURLToPath(import.meta.url));
const MOCK_CODE = "123456";

const config: AppConfig = {
  demo_mode: true,
  signup_open: true,
  access_code_required: false,
  banner: "Mock mode: fixture data only. Any email works; the code is 123456.",
};

const courses: Course[] = [
  {
    id: "course-fixture-1",
    title: "Mechanics",
    subject: "Physics",
    level: "Class 11",
    programme: { id: "programme-fixture-1", title: "Fixture programme" },
  },
];

const topics: Topic[] = [
  { id: "topic-root", parent_id: null, title: "Laws of motion", position: 1, lesson: null },
  {
    id: fixtureLesson.topic_id,
    parent_id: "topic-root",
    title: "Newton's second law",
    position: 1,
    lesson: {
      id: fixtureLesson.id,
      format: fixtureLesson.format,
      title: fixtureLesson.title,
      estimated_minutes: fixtureLesson.estimated_minutes,
    },
  },
  { id: "topic-third", parent_id: "topic-root", title: "Newton's third law", position: 2, lesson: null },
];

function userFor(role: Role, email?: string): User {
  return {
    id: `user-${role}`,
    email: email ?? `demo-${role}@example.test`,
    display_name: email ? (email.split("@")[0] ?? "Student") : `Demo ${role}`,
    role,
    organisation: { id: "org-fixture-1", name: "Fixture Institute" },
  };
}

function send(res: ServerResponse, status: number, body?: unknown): void {
  res.statusCode = status;
  if (body === undefined) {
    res.end();
    return;
  }
  res.setHeader("Content-Type", "application/json");
  res.end(JSON.stringify(body));
}

async function readJson(req: IncomingMessage): Promise<Record<string, unknown>> {
  const chunks: Buffer[] = [];
  for await (const chunk of req) chunks.push(chunk as Buffer);
  try {
    const parsed: unknown = JSON.parse(Buffer.concat(chunks).toString("utf8") || "{}");
    return typeof parsed === "object" && parsed !== null ? (parsed as Record<string, unknown>) : {};
  } catch {
    return {};
  }
}

export function mockApi(): Plugin {
  // One signed-in user for the whole dev server is enough for a mock.
  let current: User | null = null;

  async function handle(req: IncomingMessage, res: ServerResponse, path: string): Promise<void> {
    const method = req.method ?? "GET";
    const route = `${method} ${path}`;

    if (route === "GET /health") return send(res, 200, { status: "ok", version: "mock" });
    if (route === "GET /config") return send(res, 200, config);
    if (route === "POST /auth/request-code") return send(res, 204);
    if (route === "POST /auth/verify-code") {
      const body = await readJson(req);
      if (body.code !== MOCK_CODE || typeof body.email !== "string") {
        return send(res, 400, { detail: "That code is wrong or has expired." });
      }
      current = userFor("student", body.email);
      return send(res, 200, { user: current });
    }
    if (route === "POST /auth/demo-login") {
      const body = await readJson(req);
      const role = body.role;
      if (role !== "admin" && role !== "reviewer" && role !== "student") {
        return send(res, 422, { detail: "Unknown role." });
      }
      current = userFor(role);
      return send(res, 200, { user: current });
    }
    if (route === "POST /auth/logout") {
      current = null;
      return send(res, 204);
    }

    if (!current) return send(res, 401, { detail: "Not signed in." });

    if (route === "GET /me") return send(res, 200, current);
    if (route === "GET /courses") return send(res, 200, courses);
    if (route === `GET /courses/${courses[0]?.id}/topics`) return send(res, 200, topics);
    if (route === `GET /lessons/${fixtureLesson.id}`) return send(res, 200, fixtureLesson);
    if (route === "GET /media/fixtures/forces-on-block.svg") {
      res.statusCode = 200;
      res.setHeader("Content-Type", "image/svg+xml");
      res.end(readFileSync(resolve(here, "media", "forces-on-block.svg")));
      return;
    }
    return send(res, 404, { detail: "Not found." });
  }

  return {
    name: "ailms-mock-api",
    configureServer(server) {
      server.middlewares.use((req, res, next) => {
        const url = new URL(req.url ?? "/", "http://localhost");
        if (!url.pathname.startsWith("/api/")) return next();
        handle(req, res, decodeURIComponent(url.pathname.slice(4))).catch(next);
      });
    },
  };
}
