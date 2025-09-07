# SukoonAI — Migration Log
> Rebranding SehatAI (HF demo) → SukoonAI (“Mental Wellness Agent”) on the standard stack:
> Python · LangChain · FastAPI · Supabase pgvector · Streamlit · Docker
> Monitoring: LangSmith · Postman · Pytest. Model: GPT-4o-mini. Deploy: Railway/Render, Streamlit Cloud, Supabase (free tiers).

## Conventions
- Status: ✅ done · 🔜 next · ⏸ blocked
- Branches: `sehatai-legacy` (frozen), `sukoonai-mvp` (active)
- This log mirrors the 8-step migration checklist: Rename → Backend → LangChain → Data → UI → Monitoring → Deployment → Testing.

---

## 2025-09-05
### Step 1 — Rename & Rebrand
- ✅ **1.0 Checkpoint created**  
  - `git init && git add -A && git commit -m "checkpoint: pre-rebrand SehatAI"`  
  - Branch **`sehatai-legacy`** created (backup).
- ✅ **1.1 Working branch**  
  - `git checkout -b sukoonai-mvp`
- ✅ **1.2 Bulk rename** `SehatAI → SukoonAI`  
  - VS Code global replace (51 matches in 13 files). Verified zero residual hits.
- ✅ **1.3 Tagline audit**  
  - Text tagline “Mind Wellness Chatbot” not present in code/docs (only embedded in logo).
- ✅ **1.4 Assets integration**  
  - New `SukoonAI-Logo-Final.png` + `favicon.png` placed inside `/static/`.
  - Updated `app.py` to mount `/static` via FastAPI’s `StaticFiles`.
  - Updated `program.html` to reference `/static/favicon.png` and `/static/SukoonAI-Logo-Final.png`.
  - Removed redundant manual routes for favicon/logo.
  - Verified favicon and logo accessible at `/static/...` inside Docker container.
- Notes
  - Keep HF Space `banday/sehatai-mvp` as legacy later; new space will be `banday/sukoonai-mvp`.

---

## Running To-Dos (rolling)
- [ ] Replace logo references in README.md.
- [ ] Decide: same repo vs new repo for HF space (default = new space `sukoonai-mvp`).

---

## Links
- (add HF space links / dashboards here when created)
