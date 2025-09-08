# packages/agent/graph.py
from __future__ import annotations

from typing import Any, Mapping

from .nodes import plan_node, rag_node, guard_node, compose_node


# ---------------------------- helpers (pure) ---------------------------------

def _normalize_state(state_in: Mapping[str, Any] | None) -> dict[str, Any]:
    """
    Make a clean, deterministic state dict for nodes:
    - Accept both "q" and legacy "query"; prefer "q".
    - Ensure notes is a dict.
    - Provide minimal defaults for org_id/user_id if absent.
    """
    s: dict[str, Any] = dict(state_in or {})

    # Accept legacy "query" from older callers, convert to "q"
    if "q" not in s and "query" in s:
        s["q"] = s.pop("query")

    # Hygiene defaults (safe for local/dev runs)
    s.setdefault("org_id", "demo")
    s.setdefault("user_id", "u1")

    # Notes must be a dict for guard/compose to read/write flags
    s["notes"] = dict(s.get("notes") or {})
    return s


# ---------------------------- public API -------------------------------------

def run_graph(state_in: Mapping[str, Any]) -> dict[str, Any]:
    """
    Deterministic execution for Chat-3b:
    plan → rag → guard → compose
    Nodes are pure (no IO, no randomness). Returns a plain dict state
    with keys like: answer, sources, confidence, tokens, notes, etc.
    """
    state = _normalize_state(state_in)

    state = plan_node(state)
    state = rag_node(state)
    state = guard_node(state)
    state = compose_node(state)

    # state now contains: answer, sources (possibly [] on crisis), confidence="low", tokens, etc.
    return state


# ---------------------------- optional LangGraph ------------------------------
# (Not required for Chat-3b; kept here to ease future migration)

try:  # pragma: no cover
    from langgraph.graph import StateGraph, START, END  # type: ignore

    def build_langgraph():
        # Use dict as the state type; our nodes operate on dict[str, Any]
        graph = StateGraph(dict)  # type: ignore[type-arg]
        graph.add_node("plan", plan_node)
        graph.add_node("rag", rag_node)
        graph.add_node("guard", guard_node)
        graph.add_node("compose", compose_node)

        graph.add_edge(START, "plan")
        graph.add_edge("plan", "rag")
        graph.add_edge("rag", "guard")
        graph.add_edge("guard", "compose")  # crisis handling is inside compose_node
        graph.add_edge("compose", END)
        return graph
except Exception:
    # LangGraph is optional; ignore if not installed
    pass
