// Hand-written types for the M1 API contract.
// This is the only file with hand-written API types: once ../backend/openapi.json
// exists, run `npm run gen:api` and re-export the generated types from here.

export type Role = "admin" | "reviewer" | "student";

export interface Health {
  status: "ok";
  version: string;
}

export interface AppConfig {
  demo_mode: boolean;
  signup_open: boolean;
  access_code_required: boolean;
  banner: string | null;
}

export interface Organisation {
  id: string;
  name: string;
}

export interface User {
  id: string;
  email: string;
  display_name: string;
  role: Role;
  organisation: Organisation;
}

export interface RequestCodeBody {
  email: string;
}

export interface VerifyCodeBody {
  email: string;
  code: string;
}

export interface DemoLoginBody {
  role: Role;
  access_code?: string;
}

export interface AuthResponse {
  user: User;
}

export interface ProgrammeRef {
  id: string;
  title: string;
}

export interface Course {
  id: string;
  title: string;
  subject: string;
  level: string;
  programme: ProgrammeRef;
}

export type LessonFormat = "tutorial";

export interface TopicLesson {
  id: string;
  format: string;
  title: string;
  estimated_minutes: number;
}

export interface Topic {
  id: string;
  parent_id: string | null;
  title: string;
  position: number;
  lesson: TopicLesson | null;
}

export type SectionType =
  | "explanation"
  | "derivation"
  | "worked_example"
  | "diagram"
  | "table"
  | "key_points"
  | "common_mistakes"
  | "summary";

export interface SectionStep {
  id: string;
  body_md: string;
}

export interface SectionImage {
  key: string;
  alt: string;
  caption: string;
}

export interface SectionTable {
  headers: string[];
  rows: string[][];
}

export interface SectionSource {
  source_title: string;
  pages: number[];
}

export interface Section {
  id: string;
  type: SectionType;
  title?: string | null;
  body_md?: string | null;
  steps?: SectionStep[] | null;
  image?: SectionImage | null;
  table?: SectionTable | null;
  items?: string[] | null;
  sources: SectionSource[];
}

export interface LessonDocument {
  schema_version: 1;
  sections: Section[];
}

export interface Lesson {
  id: string;
  topic_id: string;
  title: string;
  format: LessonFormat;
  version: number;
  estimated_minutes: number;
  attribution: string | null;
  document: LessonDocument;
}

export interface ErrorBody {
  detail: string;
}
