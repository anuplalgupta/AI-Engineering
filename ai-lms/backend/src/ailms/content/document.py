"""The lesson document, format version 1 (ADR 0007 item 3).

Text is Markdown. Maths is LaTeX inside $...$ (inline) and $$...$$ (display).
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

FORMAT_VERSION = 1

SectionType = Literal[
    "explanation",
    "derivation",
    "worked_example",
    "diagram",
    "table",
    "key_points",
    "common_mistakes",
    "summary",
]


class _DocModel(BaseModel):
    # Fields with defaults are always sent, so the API description marks them required.
    model_config = ConfigDict(json_schema_serialization_defaults_required=True)


class Source(_DocModel):
    source_title: str
    pages: list[int] = Field(default_factory=list)


class Step(_DocModel):
    id: str
    body_md: str


class Image(_DocModel):
    key: str
    alt: str
    caption: str


class Table(_DocModel):
    headers: list[str]
    rows: list[list[str]]


class Section(_DocModel):
    # Stable across versions of a lesson, so a student's place survives an edit.
    id: str = Field(min_length=1, max_length=80)
    type: SectionType
    title: str | None = None
    body_md: str | None = None
    steps: list[Step] | None = None
    image: Image | None = None
    table: Table | None = None
    items: list[str] | None = None
    sources: list[Source]

    @model_validator(mode="after")
    def _has_its_content(self) -> "Section":
        missing = None
        if self.type in ("explanation", "summary") and not self.body_md:
            missing = "body_md"
        elif self.type == "derivation" and not self.steps:
            missing = "steps"
        elif self.type == "worked_example" and not (self.body_md or self.steps):
            missing = "body_md or steps"
        elif self.type == "diagram" and self.image is None:
            missing = "image"
        elif self.type == "table" and self.table is None:
            missing = "table"
        elif self.type in ("key_points", "common_mistakes") and not self.items:
            missing = "items"
        if missing:
            raise ValueError(f"section {self.id!r} of type {self.type} needs {missing}")
        return self


class LessonDocument(_DocModel):
    schema_version: Literal[1]
    sections: list[Section] = Field(min_length=1)

    @model_validator(mode="after")
    def _ids_are_unique(self) -> "LessonDocument":
        seen: set[str] = set()
        for section in self.sections:
            ids = [section.id] + [f"{section.id}/{step.id}" for step in section.steps or []]
            for item in ids:
                if item in seen:
                    raise ValueError(f"duplicate id in lesson document: {item}")
                seen.add(item)
        return self
