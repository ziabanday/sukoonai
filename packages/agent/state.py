from __future__ import annotations
from typing import Any, Literal, List, Optional
from pydantic import BaseModel, Field, ConfigDict


class AgentState(BaseModel):
    """
    Mutable working state passed between nodes in the agent graph.
    """
    model_config = ConfigDict(extra="forbid")

    org_id: Optional[str] = None
    user_id: Optional[str] = None
    query: str

    plan: Optional[str] = None
    evidence: List[str] = Field(default_factory=list)
    sources: List[str] = Field(default_factory=list)

    # numeric confidence score placeholder for future scoring (Chat-5/6)
    confidence: Optional[float] = None

    # scratchpad / flags (e.g., {"crisis": True, "trace_id": "..."} )
    notes: dict[str, Any] = Field(default_factory=dict)


class Result(BaseModel):
    """
    Final API contract returned to callers.
    """
    model_config = ConfigDict(extra="forbid")

    answer: str
    sources: list[str]
    confidence: Literal["low", "med", "high"]
    cost_ms: int = 0
    tokens: int = 0
