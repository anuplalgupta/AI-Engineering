// API types for the M1 contract, taken from the generated schema.gen.ts.
// After a backend route changes: export ../backend/openapi.json, run `npm run gen:api`,
// then fix any type errors here. This is the only file that names API types by hand.
import type { components } from "./schema.gen";

type Schemas = components["schemas"];

export type Health = Schemas["HealthOut"];
export type AppConfig = Schemas["ConfigOut"];
export type Organisation = Schemas["OrganisationOut"];
export type User = Schemas["UserOut"];
export type Role = User["role"];

export type RequestCodeBody = Schemas["RequestCodeIn"];
export type VerifyCodeBody = Schemas["VerifyCodeIn"];
export type DemoLoginBody = Schemas["DemoLoginIn"];
export type AuthResponse = Schemas["SignedInOut"];

export type ProgrammeRef = Schemas["ProgrammeOut"];
export type Course = Schemas["CourseOut"];
export type TopicLesson = Schemas["TopicLessonOut"];
export type Topic = Schemas["TopicOut"];

// The server always sends these keys (null when unused); the contract and the
// reader treat them as optional, so fixtures and older documents may leave them out.
type OptionalSectionKeys = "title" | "body_md" | "steps" | "image" | "table" | "items";
export type Section = Omit<Schemas["Section"], OptionalSectionKeys> &
  Partial<Pick<Schemas["Section"], OptionalSectionKeys>>;
export type SectionType = Section["type"];
export type SectionStep = Schemas["Step"];
export type SectionImage = Schemas["Image"];
export type SectionTable = Schemas["Table"];
export type SectionSource = Schemas["Source"];
export type LessonDocument = Omit<Schemas["LessonDocument"], "sections"> & { sections: Section[] };
export type Lesson = Omit<Schemas["LessonOut"], "document"> & { document: LessonDocument };
export type LessonFormat = Lesson["format"];

export type ErrorBody = Schemas["ErrorOut"];
