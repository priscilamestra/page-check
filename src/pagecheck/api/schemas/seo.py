"""Contrato HTTP da auditoria SEO, separado da prévia de inspeção."""

from typing import Any, Literal

from pydantic import BaseModel, Field

Objective = Literal["leads", "meetings", "sales", "signup", "organic_traffic"]
Status = Literal["passed", "failed", "warning", "not_verified", "not_applicable"]
Severity = Literal["critical", "high", "medium", "low", "info"]


class SeoAuditRequest(BaseModel):
    url: str = Field(min_length=1, max_length=2048)
    niche: str = Field(min_length=2, max_length=120)
    objective: Objective


class SeoCheck(BaseModel):
    check_id: str
    module: Literal["seo"]
    status: Status
    severity: Severity
    title: str
    weight: int
    target_url: str
    team: str
    evidence: dict[str, Any]
    recommendation: str


class SeoAuditResponse(BaseModel):
    requested_url: str
    final_url: str
    status_code: int
    redirects: list[str]
    niche: str
    module: Literal["seo"]
    ruleset_version: str
    objective: Objective
    score: float | None = Field(default=None, ge=0, le=100)
    coverage: float = Field(ge=0, le=1)
    partial_score: bool
    checks_executed: int
    checks_applicable: int
    checks: list[SeoCheck]
    findings: list[SeoCheck]
