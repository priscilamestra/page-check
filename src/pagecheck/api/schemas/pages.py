"""Contrato HTTP para prévia de metadados de páginas públicas."""

from pydantic import BaseModel, Field


class PageInspectionRequest(BaseModel):
    url: str = Field(min_length=1, max_length=2048)


class Heading(BaseModel):
    level: str
    text: str


class Link(BaseModel):
    text: str
    href: str
    resolved_url: str


class Image(BaseModel):
    src: str | None
    data_src: str | None
    alt: str | None
    loading: str | None


class PreviewFlags(BaseModel):
    headings: bool
    links: bool
    images: bool


class PageInspectionResponse(BaseModel):
    requested_url: str
    final_url: str
    status_code: int
    redirects: list[str]
    title: str | None
    meta_description: str | None
    meta_robots: str | None
    canonical: str | None
    headings_count: int
    headings: list[Heading]
    links_count: int
    links_preview: list[Link]
    images_count: int
    images_preview: list[Image]
    previews_truncated: PreviewFlags
    audit_scored: bool = False
