# SukoonAI – Content Sourcing Checklist (RAG Pipeline)

## Step 1 — Define Scope
- Focus only on **MedlinePlus (Mental Health topics)** + **WHO (Fact Sheets, public guides)**.

## Step 2 — Collect Content
- Save/download MedlinePlus encyclopedia pages and WHO fact sheets related to anxiety, depression, stress, sleep.

## Step 3 — Clean Content
- Remove headers, navigation, references.
- Keep definitions, FAQs, and explanations only.

## Step 4 — Segment
- Split into **200–400 token chunks** with 50-token overlap.
- Add metadata (source, topic, language).

## Step 5 — Build FAISS Index
- Generate embeddings (**OpenAI text-embedding-3-small**) and store with metadata.

## Step 6 — Integrate RAG
- User query → embed → retrieve top chunks → **GPT-4o-mini** → response with disclaimer + source.

## Step 7 — Testing
- Use Postman to test `/api/query/ask`.
- Validate retrieved answers with MedlinePlus/WHO originals.

---

✅ **Outcome:** SukoonAI answers are safe, evidence-based, and grounded in **MedlinePlus + WHO**.
