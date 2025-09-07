import asyncio
from pathlib import Path
from typing import List, Tuple

from langchain_community.vectorstores import FAISS
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from langchain.docstore.document import Document

from app.utils.env import load_settings

settings = load_settings()

INDEX_DIR = Path(__file__).resolve().parents[2] / "data" / "indices" / "faiss"

_sys_prompt = """You are SukoonAI, a medical evidence navigator.
- Answer using ONLY the provided context.
- If the answer is not in the context, say you don't know.
- Keep answers short, clear, and suitable for patient education.
- Always include a brief disclaimer: "Not medical advice; for education only."
"""

_prompt = ChatPromptTemplate.from_messages([
    ("system", _sys_prompt),
    ("human", "Question: {question}\n\nContext:\n{context}")
])

def _load_vectorstore() -> FAISS:
    if not INDEX_DIR.exists():
        raise FileNotFoundError("FAISS index not found. Run: python scripts/ingest.py")
    return FAISS.load_local(
        INDEX_DIR.as_posix(),
        OpenAIEmbeddings(model=settings.EMBEDDING_MODEL, api_key=settings.OPENAI_API_KEY),
        allow_dangerous_deserialization=True
    )

_vectorstore = None

def get_vectorstore() -> FAISS:
    global _vectorstore
    if _vectorstore is None:
        _vectorstore = _load_vectorstore()
    return _vectorstore

async def _aretrieve(query: str, k: int = 4) -> List[Document]:
    vs = get_vectorstore()
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: vs.similarity_search(query, k=k))

async def get_answer(question: str) -> Tuple[str, List[str]]:
    docs = await _aretrieve(question, k=4)
    context = "\n\n---\n\n".join([d.page_content for d in docs])
    sources = [str(d.metadata.get("source", "unknown")) for d in docs]

    llm = ChatOpenAI(model=settings.OPENAI_MODEL, temperature=0.0, api_key=settings.OPENAI_API_KEY)
    messages = _prompt.format_messages(question=question, context=context)
    resp = await llm.ainvoke(messages)

    answer = resp.content.strip()
    if "Not medical advice" not in answer:
        answer += "\n\n_Not medical advice; for education only._"

    seen = set()
    uniq_sources = []
    for s in sources:
        if s not in seen:
            seen.add(s)
            uniq_sources.append(s)

    return answer, uniq_sources
