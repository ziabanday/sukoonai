# packages/agent/nodes.py
from __future__ import annotations

from typing import Any, Literal, TypedDict, NotRequired


Confidence = Literal["low", "med", "high"]


class AgentState(TypedDict, total=False):
    """
    Minimal, node-local view of the state used by the LangGraph pipeline.

    NOTE: Nodes remain PURE. No IO, no randomness, no time/uuid usage here.
    The API layer (Task B) is responsible for injecting crisis_terms and trace_id.
    """
    org_id: str
    user_id: str
    q: str  # user query
    plan: NotRequired[str]
    sources: NotRequired[list[str]]
    notes: NotRequired[dict[str, Any]]
    answer: NotRequired[str]
    confidence: NotRequired[Confidence]
    tokens: NotRequired[int]


# ------------ helpers (pure) -------------------------------------------------


def _normalize_query(q: str) -> str:
    return " ".join(q.strip().split())


def _topic_from_query(q: str) -> str:
    # Deterministic, low-tech "topic" extraction: keep first 8 words.
    words = _normalize_query(q).split()
    return " ".join(words[:8]) if words else ""


def _dedupe_preserve_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for x in items:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


def _curated_sources_for(q: str) -> list[str]:
    """
    Deterministic stubbed RAG: return stable-ordered sources (MedlinePlus first, WHO second).
    No external IO, no retrieval — just curated links by simple keyword heuristics.
    """
    ql = q.lower()
    # A tiny, extensible mapping. Always MedlinePlus → WHO order.
    MEDLINEPLUS = "https://medlineplus.gov/encyclopedia.html"
    WHO_SLEEP = "https://www.who.int/health-topics/sleep"
    WHO_MENTAL = "https://www.who.int/health-topics/mental-health"
    WHO_GENERAL = "https://www.who.int/"

    if any(k in ql for k in ("sleep hygiene", "sleep", "insomnia")):
        return [MEDLINEPLUS, WHO_SLEEP]
    if any(k in ql for k in ("anxiety", "depression", "stress", "panic")):
        return [MEDLINEPLUS, WHO_MENTAL]
    # default, still stable
    return [MEDLINEPLUS, WHO_GENERAL]


def _is_crisis_text(q: str, crisis_terms: set[str] | None) -> bool:
    """
    Pure substring check against a lowercased set of crisis terms injected via state.notes["crisis_terms"].
    """
    if not crisis_terms:
        return False
    text = q.lower()
    return any(term in text for term in crisis_terms)


def _render_citations(sources: list[str]) -> str:
    """
    Render numbered citations ' [1][2]' in the same order as provided.
    """
    if not sources:
        return ""
    return " " + "".join(f"[{i+1}]" for i in range(len(sources)))


def _compose_normal_answer(topic: str, sources: list[str]) -> str:
    """
    Deterministic, compact bilingual answer:
    - English paragraph (citations inline as [1][2]… in the order of sources)
    - Roman-Urdu paragraph (no transliteration randomness; fixed template)
    """
    citations = _render_citations(sources)
    # English (neutral, short, non-coaching medical boundary)
    en = (
        f"{topic or 'This topic'}: Here’s a brief, general overview based on trusted health references"
        f"{citations}. This is educational information only and not a medical diagnosis or treatment."
    )

    # Roman-Urdu (stable template; warm, concise)
    ur = (
        f"{topic or 'Is mawzuʼ'} ke baare mein mukhtasar, aam maloomat di gayi hai{citations}. "
        "Yeh taleemi maqsad ke liye hai — yeh tibbi tashkhis ya ilaaj ka mashwara nahi hai."
    )

    return f"{en}\n\n{ur}"


def _compose_crisis_answer() -> str:
    """
    Safe escalation ONLY. No coaching/coping steps. Bilingual, deterministic wording.
    """
    en = (
        "I’m really sorry you’re feeling this way. If you are in immediate danger or at risk of harming "
        "yourself or someone else, please contact local emergency services right now, or reach a suicide "
        "prevention helpline. If you can, tell a trusted person nearby and seek urgent help from a qualified "
        "mental health professional."
    )
    ur = (
        "Mujhe afsos hai ke aap aisa mehsoos kar rahe hain. Agar foran khatra ho ya aap khud ko ya kisi "
        "aur ko nuqsan pohanchane ka irada mehsoos kar rahe hain, to barah-e-karam foran apni ilaqai "
        "emergency services se rabta karein, ya suicide prevention helpline ko call karein. Mumkin ho to "
        "kisi bharosemand shaks ko foran batayein aur kisi moʼtabar mental health professional se haji imdad "
        "hasil karein."
    )
    return f"{en}\n\n{ur}"


def _estimate_tokens(s: str) -> int:
    # Simple deterministic estimate: ~4 chars/token
    n = max(1, len(s) // 4)
    return n


# ------------ nodes (pure) ---------------------------------------------------


def plan_node(state: AgentState) -> AgentState:
    """
    Build a simple, deterministic plan summary from the query.
    """
    q = state.get("q", "") or ""
    topic = _topic_from_query(q)
    plan = f"plan: analyze → retrieve → guard → compose | topic='{topic}'"
    new_state = dict(state)
    new_state["plan"] = plan
    return new_state  # pure transform


def rag_node(state: AgentState) -> AgentState:
    """
    Return curated, stable-ordered sources (MedlinePlus → WHO). No IO.
    """
    q = state.get("q", "") or ""
    sources = _curated_sources_for(q)
    new_state = dict(state)
    new_state["sources"] = sources
    return new_state


def guard_node(state: AgentState) -> AgentState:
    """
    Crisis check using lowercased crisis terms set injected by API at state.notes['crisis_terms'].
    Sets state.notes['crisis'] = True/False. Pure (no IO).
    """
    q = state.get("q", "") or ""
    notes: dict[str, Any] = dict(state.get("notes") or {})
    crisis_terms = notes.get("crisis_terms")
    crisis = _is_crisis_text(q, crisis_terms if isinstance(crisis_terms, set) else None)
    notes["crisis"] = bool(crisis)

    new_state = dict(state)
    new_state["notes"] = notes
    return new_state


def compose_node(state: AgentState) -> AgentState:
    """
    Compose the final bilingual answer with numbered citations preserving source order.
    On crisis → safe escalation message; no sources are returned in the text body, but Result.sources stays consistent with DoD rules.
    confidence is set to 'low' by default for MVP.
    """
    notes: dict[str, Any] = dict(state.get("notes") or {})
    is_crisis = bool(notes.get("crisis"))
    sources: list[str] = list(state.get("sources") or [])
    sources = _dedupe_preserve_order(sources)  # stability + hygiene

    if is_crisis:
        answer = _compose_crisis_answer()
        out_sources: list[str] = []  # no citations on crisis path
    else:
        topic = _topic_from_query(state.get("q", "") or "")
        answer = _compose_normal_answer(topic, sources)
        out_sources = sources

    tokens = _estimate_tokens(answer)

    new_state = dict(state)
    new_state["answer"] = answer
    new_state["sources"] = out_sources
    new_state["confidence"] = "low"
    new_state["tokens"] = tokens
    return new_state
