"""Input contract for the combined HTML audit."""
from typing import Literal
from pydantic import BaseModel, Field, field_validator

from pagecheck.audits.seo.content_guidance import normalize_keywords

Objective = Literal["leads", "meetings", "sales", "signup", "organic_traffic"]
ContentLanguage = Literal["en", "pt", "es"]

class PageAuditRequest(BaseModel):
    url: str = Field(min_length=1, max_length=2048)
    niche: str = Field(min_length=2, max_length=120)
    objective: Objective
    language: ContentLanguage = "en"  # Backward compatible with previous clients
    keywords: list[str] = Field(default_factory=list, max_length=8)

    @field_validator("keywords")
    @classmethod
    def validate_keywords(cls, value: list[str]) -> list[str]:
        return normalize_keywords(value)
