from __future__ import annotations
import time
from typing import Optional

from .state import AgentState, Result
from .nodes import plan_node, rag_node, guard_node, compose_node


def _hitl_escalation_answer(state: AgentState) -> str:
    """Deterministic escalation message (bilingual) with citations."""
    srcs = state.sources or []
    cites = ", ".join(f"[{i+1}] {s}" for i, s in enumerate(srcs))
    en = (
        "This looks like a crisis. I can’t provide crisis support here. "
        "Please contact local emergency services or a trusted person immediately."
    )
    ur = (
        "Yeh surat-e-haal imdadi lagti hai. Main yahan crisis support nahi de sakta. "
        "Barah-e-karam foran emergency services ya kisi bharosemand shakhs se rabta karein."
    )
    return f"Answer (EN): {en}\n\nJawab (Roman Urdu): {ur}\n\nSources: {cites}"


def run_graph(query: str, org_id: Optional[str] = None, user_id: Optional[str] = None) -> Result:
    """
    Deterministic execution for Chat-3: plan → rag → guard → (hitl?) → compose
    If guard marks crisis, we short-circuit to a safe escalation message.
    """
    t0 = time.perf_counter()
    state = AgentState(org_id=org_id, user_id=user_id, query=query)

    # Sequential, deterministic run (LangGraph integration comes later)
    state = plan_node(state)
    state = rag_node(state)
    state = guard_node(state)

    if state.notes.get("crisis"):
        composed = _hitl_escalation_answer(state)
        tokens = max(1, len(composed) // 4)  # simple estimator
        elapsed_ms = int((time.perf_counter() - t0) * 1000)
        return Result(
            answer=composed,
            sources=state.sources,
            confidence="low",
            cost_ms=elapsed_ms,
            tokens=tokens,
        )

    state = compose_node(state)
    composed = state.notes.get("composed_answer", "")
    tokens = int(state.notes.get("estimated_tokens", max(1, len(composed) // 4)))
    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    return Result(
        answer=composed,
        sources=state.sources,
        confidence="low",  # fixed for Chat-3
        cost_ms=elapsed_ms,
        tokens=tokens,
    )


# Optional: build a LangGraph object in Chat-4+ without changing the API.
try:  # pragma: no cover
    from langgraph.graph import StateGraph, START, END  # type: ignore

    def build_langgraph():
        graph = StateGraph(AgentState)
        graph.add_node("plan", plan_node)
        graph.add_node("rag", rag_node)
        graph.add_node("guard", guard_node)
        graph.add_node("compose", compose_node)
        graph.add_edge(START, "plan")
        graph.add_edge("plan", "rag")
        graph.add_edge("rag", "guard")
        graph.add_edge("guard", "compose")  # crisis branch handled in run_graph for now
        graph.add_edge("compose", END)
        return graph
except Exception:
    # LangGraph is not required for Chat-3
    pass
