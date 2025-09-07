import os
import sys
import datetime
import csv
import argparse
import textwrap
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import OpenAIEmbeddings
from langchain_openai import ChatOpenAI   # new API

# ------------------------
# Paths
# ------------------------
INDEX_PATH = "data/index/index"
LOG_DIR = "logs"

os.makedirs(LOG_DIR, exist_ok=True)

# ------------------------
# CLI argument parsing
# ------------------------
parser = argparse.ArgumentParser()
parser.add_argument("--no-log", action="store_true", help="Disable saving logs for this run")
parser.add_argument("--wrap", type=int, default=80, help="Set console text wrap width (default=80)")
args = parser.parse_args()

NO_LOG = args.no_log
WRAP_WIDTH = args.wrap

if NO_LOG:
    print("[INFO] Logging disabled (--no-log)")
print(f"[INFO] Wrap width set to {WRAP_WIDTH} characters")

# ------------------------
# Helper: Language detection (basic heuristic)
# ------------------------
def detect_language(text: str) -> str:
    for ch in text:
        if '\u0600' <= ch <= '\u06FF':
            return "urdu-script"
    roman_urdu_markers = ["hai", "kya", "nahi", "ka", "ki", "tum", "main"]
    if any(marker in text.lower() for marker in roman_urdu_markers):
        return "roman-urdu"
    return "english"

# ------------------------
# Load FAISS index
# ------------------------
print("[INFO] Starting SukoonAI query engine...")

try:
    db = FAISS.load_local(INDEX_PATH, OpenAIEmbeddings(), allow_dangerous_deserialization=True)
except Exception as e:
    print("[ERROR] Could not load FAISS index:", e)
    exit(1)

retriever = db.as_retriever(search_kwargs={"k": 5})

# ------------------------
# OpenAI LLM setup
# ------------------------
api_key = os.environ.get("OPENAI_API_KEY")
if api_key:
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, openai_api_key=api_key)
    mode = "retriever+LLM"
    print("[OK] Found OPENAI_API_KEY → Using retriever+LLM mode.")
else:
    llm = None
    mode = "retriever-only"
    print("[WARN] No OPENAI_API_KEY found → Using retriever-only mode.")

# ------------------------
# Updated System Prompt (with your exact Urdu corrections)
# ------------------------
SYSTEM_PROMPT = """
You are SukoonAI, a bilingual mind-wellness chatbot for Pakistan.

Output format:
- Two sections only: [English] and [Roman Urdu].
- No bullet points. Use short, flowing sentences (aim for 3–5 per section; use more only if truly needed).
- Keep the tone friendly, calm, and supportive. Do not diagnose or prescribe; share general wellness information.
- Roman Urdu must sound casual and natural (like friends talking). Avoid stiff textbook style and also avoid bazari slang.

Grounding:
- Use only the provided context. Prefer simple, everyday wording.
- At the end of EACH section, add a source line on its own line:
  (Source: MedlinePlus / WHO)

Safety (append to EACH section as the last sentence, on its own line):
- English: This is general wellness info, not medical care. If you feel unsafe, seek help.
- Roman Urdu: Yeh aam maloomat hai, tibbi mashwara nahi. Agar unsafe mehsoos karen to madad lein.

Roman Urdu style guide:
- Keep sentences short and natural, like spoken conversation.
- Avoid overly formal words (e.g., alamat, zahir hota hai, tareeqa). Use everyday ones (nishani, samne aata hai, andaaz).
- Avoid bazari slang (scene, mast, chill). Stick with soft, friendly words (acha lagta hai, bura lagta hai, thoda sa, kabhi kabhi).
- Use warm connectors: “dekhein”, “aisa hota hai”, “bas”, “achi baat yeh hai”.
- End with gentle encouragement instead of commands. Example: “…baat karna acha rahega” instead of “…baat karna zaroori hai.”

Examples (follow the vibe, not exact words):
- EN: “It’s normal to feel nervous before an exam.”
  RU: “Exam se pehle ghabrahat hona bilkul normal baat hai.”
- EN: “Feeling low sometimes doesn’t mean you’re weak.”
  RU: “Kabhi kabhi udaas hona iska matlab yeh nahi ke aap kamzor ho.”
- EN: “If you can’t sleep, it’s okay. Many people go through this.”
  RU: “Neend na aana aam baat hai, aur bohot log isse guzarte hain.”
- EN: “Talking to someone you trust can make things easier.”
  RU: “Apne bharose ke insaan se baat karna cheezon ko halka bana deta hai.”
- EN: “When things feel heavy, it’s okay to ask for help.”
  RU: “Jab sab kuch bhaari lage to madad lena bilkul theek hai.”
- EN: “Things you used to enjoy might not feel the same anymore.”
  RU: “Jo cheezen pehle pasand thi, ab utni aachi nahi lagti.”
- EN: “Feeling irritable doesn’t always mean you’re angry — sometimes it’s just stress.”
  RU: “Chirh Chirhana ka matlab hamesha gusse nahi hota, kabhi kabhi bas stress hota hai.”
- EN: “Anxiety can be a sign of stress; sometimes that’s normal.”
  RU: “Anxiety aksar stress ki aik nishani hoti hai; kabhi kabhi aisa hona bilkul normal hai.”
- EN: “Depression shows up differently for each person. Some feel tired all the time.”
  RU: “Har insaan mai depression ki alamaat muktalif ho sakti hain. Kuch log hamesha thake hue rehte hain.”

Now, answer the user in [English] and [Roman Urdu] exactly in that order, following all rules above.
"""

# ------------------------
# Logging setup
# ------------------------
def get_logfile():
    today = datetime.date.today().strftime("%Y-%m-%d")
    return os.path.join(LOG_DIR, f"query_log_{today}.csv")

def log_query(query, mode, results, answer=None):
    if NO_LOG:
        return
    logfile = get_logfile()
    newfile = not os.path.exists(logfile)
    with open(logfile, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if newfile:
            writer.writerow(["timestamp", "query", "mode", "source", "similarity", "snippet", "answer"])
        for src, sim, snippet in results:
            writer.writerow([
                datetime.datetime.now().isoformat(),
                query,
                mode,
                src,
                f"{sim:.4f}",
                snippet[:200].replace("\n", " "),
                (answer[:200].replace("\n", " ") if answer else "")
            ])

def save_last_answer(answer: str):
    if NO_LOG:
        return
    filepath = os.path.join(LOG_DIR, "last_answer.txt")
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(answer)

def append_answer_history(user_query: str, answer: str):
    if NO_LOG:
        return
    filepath = os.path.join(LOG_DIR, "all_answers.txt")
    with open(filepath, "a", encoding="utf-8") as f:
        f.write("="*60 + "\n")
        f.write(f"Timestamp: {datetime.datetime.now().isoformat()}\n")
        f.write(f"Query: {user_query}\n\n")
        f.write(answer.strip() + "\n")
        f.write("="*60 + "\n\n")

# ------------------------
# Helper: wrap text for console output
# ------------------------
def wrap_text(text, width=80):
    return "\n".join(textwrap.fill(line, width) for line in text.splitlines() if line.strip())

# ------------------------
# Main query loop
# ------------------------
print("🤖 Ready to query SukoonAI (type 'exit' to quit)")

while True:
    user_q = input("\nEnter your query: ")
    if user_q.strip().lower() == "exit":
        print("👋 Goodbye!")
        break

    lang = detect_language(user_q)
    query_for_retrieval = user_q
    if lang in ["urdu-script", "roman-urdu"] and llm:
        trans_prompt = f"Translate this {lang} question into English for retrieval only: {user_q}"
        query_for_retrieval = llm.invoke(trans_prompt).content.strip()

    docs_and_scores = db.similarity_search_with_score(query_for_retrieval, k=5)
    results = []
    for doc, score in docs_and_scores:
        norm_sim = 1 / (1 + score)
        results.append((doc.metadata.get("source", "unknown"),
                        norm_sim,
                        doc.page_content[:300]))

    results.sort(key=lambda x: x[1], reverse=True)
    top_results = results[:3]

    if llm:
        context_text = "\n\n".join([f"Source: {src}\nContent: {snippet}"
                                    for src, sim, snippet in top_results])
        final_prompt = f"""{SYSTEM_PROMPT}

User query: {user_q}

Relevant context from sources:
{context_text}

Now provide the bilingual answer strictly in flowing conversational style.
"""
        try:
            answer = llm.invoke(final_prompt).content
        except Exception as e:
            print("[ERROR] LLM call failed:", e)
            answer = None
    else:
        answer = None

    if answer:
        print("\n🧠 SukoonAI Bilingual Answer\n")
        if "[Roman Urdu]" in answer:
            english_part, roman_part = answer.split("[Roman Urdu]", 1)
            print(wrap_text(english_part.strip(), WRAP_WIDTH) + "\n")
            print("[Roman Urdu]\n" + wrap_text(roman_part.strip(), WRAP_WIDTH) + "\n")
        else:
            print(wrap_text(answer.strip(), WRAP_WIDTH) + "\n")

        final_answer = "🧠 SukoonAI Bilingual Answer\n\n" + answer.strip()
        save_last_answer(final_answer)
        append_answer_history(user_q, final_answer)
    else:
        print("\n🔎 Retriever Results Only (no LLM synthesis):\n")
        for src, sim, snippet in top_results:
            print(f"- {src} (similarity {sim:.3f}) → {snippet[:200]}...")

    log_query(user_q, mode, top_results, answer)
