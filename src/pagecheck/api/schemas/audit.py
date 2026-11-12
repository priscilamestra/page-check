"""Entrada da auditoria HTML combinada."""
from typing import Literal
from pydantic import BaseModel, Field

Objective = Literal["leads", "meetings", "sales", "signup", "organic_traffic"]

class PageAuditRequest(BaseModel):
    url: str = Field(min_length=1, max_length=2048)
    niche: str = Field(min_length=2, max_length=120)
    objective: Objective
