from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


StimType = Literal["teorico", "empirico", "criativo", "reflexivo", "sistemico"]


class PipelineRequest(BaseModel):
    stimulus: str = Field(..., min_length=3, description="Entrada semântica do usuário")
    stim_type: StimType = "sistemico"
    model: str | None = None
    temperature: float = Field(0.35, ge=0.0, le=2.0)
    save: bool = True


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    limit: int = Field(5, ge=1, le=20)


class ApiResponse(BaseModel):
    ok: bool
    data: Any | None = None
    error: str | None = None
