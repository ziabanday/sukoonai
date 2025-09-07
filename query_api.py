import os
from fastapi import APIRouter
from pydantic import BaseModel
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings, ChatOpenAI

router = APIRouter()

# ------------------------
# Load FAISS Index
# ------------------------
INDEX_PATH = "data/index/index"
try:
    db = FAISS.load_local(
        INDEX_PATH,
        OpenAIEmbeddings(),
        allow_dangerous_deserialization=True
    )
    retriever = db.as_retriever(search_kwargs={"k": 5})
except Exception as e:
    print("[ERROR] Could not load FAISS index:", e)
    db = None
    retriever = None

# ------------------------
# Setup LLM
# ------------------------
api_key = os.environ.get("OPENAI_API_KEY")
if api_key:
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, openai_api_key=api_key)
    mode = "retriever+LLM"
else:
    llm = None
    mode = "retriever-only"

# ------------------------
# SYSTEM PROMPT
# ------------------------
SYSTEM_PROMPT = """
You are SukoonAI, a bilingual (English + Roman Urdu) mind-wellness chatbot designed to give concise, conversational, and human-like answers in two languages. 
You always follow this structure:

1. **English Answer**: Short conversational answer (max 3–4 sentences).  
2. **Roman Urdu Answer**: Short conversational answer (max 3–4 sentences).  
3. **Source**: Cite the knowledge source(s) clearly (e.g., MedlinePlus, WHO, HSA).  
4. **Disclaimer**: Always append:  
   - English: "Disclaimer: SukoonAI is for educational purposes and not a substitute for professional medical or mental health advice."  
   - Roman Urdu: "Wazahat: SukoonAI taleemi maqsad ke liye hai. Yeh kisi tabibi ya zehni sehat ke mashwaray ka badal nahi."

Guidelines:
- Keep tone empathetic, warm, and natural.  
- Do not bullet-point answers, write in short flowing paragraphs.  
- Always provide both languages.  
- Always provide the disclaimer.  
"""

# ------------------------
# Pydantic Models
# ------------------------
class QueryRequest(BaseModel):
    user_id: str
    question: str

class QueryResponse(BaseModel):
    answer: str
    mode: str

# ------------------------
# Endpoint
# ------------------------
@router.post("/ask", response_model=QueryResponse)
async def ask_question(req: QueryRequest):
    user_q = req.question

    if not retriever:
        return {"answer": "Error: FAISS index not available.", "mode": mode}

    # Retrieve docs
    docs_and_scores = db.similarity_search_with_score(user_q, k=5)
    results = []
    for doc, score in docs_and_scores:
        norm_sim = 1 / (1 + score)
        src = doc.metadata.get("source", "unknown")
        snippet = doc.page_content[:300]
        results.append((src, norm_sim, snippet))
    results.sort(key=lambda x: x[1], reverse=True)
    top_results = results[:3]

    # Build context
    context_text = "\n\n".join(
        [f"Source: {src}\nContent: {snippet}" for src, sim, snippet in top_results]
    )

    # LLM synthesis
    if llm:
        final_prompt = f"""{SYSTEM_PROMPT}

User query: {user_q}

Relevant context from knowledge sources:
{context_text}

Now answer bilingually (English + Roman Urdu) in a natural conversational style.
"""
        try:
            answer = llm.invoke(final_prompt).content
        except Exception as e:
            answer = f"[ERROR] LLM call failed: {e}"
    else:
        # fallback to retrieval-only
        answer = "\n".join([f"- {src} → {snippet}" for src, _, snippet in top_results])

    return {"answer": answer, "mode": mode}
