from __future__ import annotations
import os
import time
import uuid
from functools import wraps
from typing import Callable, Iterable, List

from .state import AgentState


# ---------------- decorators (budget/retry stubs) ----------------
def with_timeout(timeout_ms: int) -> Callable:
    """Lightweight budget guard (stub for now)."""
    def deco(fn: Callable) -> Callable:
        @wraps(fn)
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            result = fn(*args, **kwargs)
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            if elapsed_ms > timeout_ms:
                raise TimeoutError(f"{fn.__name__} exceeded {timeout_ms}ms (took {elapsed_ms}ms)")
            return result
        return wrapper
    return deco


def with_backoff(retries: int = 0) -> Callable:
    """Deterministic stub retry (no sleep/jitter)."""
    def deco(fn: Callable) -> Callable:
        @wraps(fn)
        def wrapper(*args, **kwargs):
            attempts = max(1, retries + 1)
            last_exc = None
            for _ in range(attempts):
                try:
                    return fn(*args, **kwargs)
                except Exception as exc:  # pragma: no cover (not expected in stub)
                    last_exc = exc
            raise last_exc
        return wrapper
    return deco


# ---------------- helpers ----------------
def _load_crisis_terms() -> List[str]:
    here = os.path.dirname(__file__)
    path = os.path.join(here, "crisis_terms.txt")
    fallback = ["suicide", "self harm", "kill myself"]
    try:
        with open(path, "r", encoding="utf-8") as f:
            terms = [ln.strip() for ln in f if ln.strip()]
            return terms or fallback
    except FileNotFoundError:
        return fallback


def _format_citations(sources: Iterable[str]) -> str:
    return ", ".join(f"[{i+1}] {src}" for i, src in enumerate(sources))


def _estimate_tokens(s: str) -> int:
    # simple deterministic stub (~4 chars per token)
    return max(1, len(s) // 4)


# ---------------- nodes (pure; state in/out) ----------------
@with_timeout(50)
@with_backoff(0)
def plan_node(state: AgentState) -> AgentState:
    q = state.query.strip().lower()
    if "sleep" in q:
        plan = "Explain sleep hygiene basics; cite MedlinePlus/WHO; keep warm and brief."
    else:
        plan = "Provide a short wellbeing-oriented explanation; cite MedlinePlus/WHO; be supportive."
    state.plan = plan
    state.notes.setdefault("trace_id", str(uuid.uuid4()))  # not used in answer (keeps determinism)
    return state


@with_timeout(50)
@with_backoff(0)
def rag_node(state: AgentState) -> AgentState:
    """
    STUB ONLY: deterministic evidence + sources.
    Real retrieval plugs in Chat-4, keeping the same interface.
    """
    sources = [
        "https://medlineplus.gov/sleepdisorders.html",
        "https://www.who.int/news-room/fact-sheets/detail/mental-health-strengthening-our-response",
        "https://medlineplus.gov/ency/article/000801.htm",
    ]
    evidence = [
        "Sleep hygiene includes consistent bed/wake times, limiting caffeine late, and a dark quiet room.",
        "WHO emphasizes mental wellbeing practices like routine, activity, and social support.",
        "Short daytime naps (if needed) and reduced screen time before bed can help.",
    ]
    state.sources = sources[:3]
    state.evidence = evidence[:3]
    return state


@with_timeout(30)
@with_backoff(0)
def guard_node(state: AgentState) -> AgentState:
    q = state.query.lower()
    crisis_terms = _load_crisis_terms()
    triggered = any(term in q for term in crisis_terms)
    if triggered:
        state.notes["crisis"] = True
    else:
        state.notes.pop("crisis", None)
    return state


@with_timeout(60)
@with_backoff(0)
def compose_node(state: AgentState) -> AgentState:
    """Compose bilingual placeholder with numbered citations; confidence fixed to 'low'."""
    cites = _format_citations(state.sources or [])

    if state.notes.get("crisis"):
        en = (
            "I’m really sorry you’re feeling this way. I can’t help with crisis support, "
            "but you’re not alone—please seek immediate help from a trusted person or local "
            "emergency services/helpline."
        )
        ru = (
            "Mujhe afsos hai ke aap aisa mehsoos kar rahe hain. Main crisis mein madad nahi kar sakta, "
            "lekin meherbani karke foran kisi bharosemand shakhs, emergency service, ya helpline se rabta karein."
        )
        msg = f"Answer (EN): {en}\n\nJawab (Roman Urdu): {ru}\n\nSources: {cites}"
    else:
        plan = state.plan or "Provide a brief, supportive explanation."
        en = (
            "Good sleep hygiene means keeping regular bed/wake times, limiting caffeine late, "
            "reducing screens before bed, and making your room dark and quiet."
        )
        ru = (
            "Behtar neend ki aadatein ka matlab hai ke roz marra aik hi waqt par sona/uthna, "
            "der raat caffeine kam karna, sone se pehle screen time kam rakhna, "
            "aur kamra andhera aur khamosh rakhna."
        )
        msg = f"Answer (EN): {en} ({plan})\n\nJawab (Roman Urdu): {ru}\n\nSources: {cites}"

    state.notes["confidence_label"] = "low"
    state.notes["estimated_tokens"] = _estimate_tokens(msg)
    state.notes.setdefault("trace_id", state.notes.get("trace_id"))  # keep if already set
    state.notes["composed_answer"] = msg
    return state
