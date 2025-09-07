# SukoonAI — Release Checklist (repeat each deploy)

## Branding
- [ ] Repo & README say **SukoonAI — Mental Wellness Agent**
- [ ] Logo loads in UI; `favicon.png` (32×32) present
- [ ] No “SehatAI” remnants: `git grep -n SehatAI` → no hits

## Environment
- [ ] `.env` contains OPENAI_API_KEY, SUPABASE_URL, SUPABASE_KEY, LANGSMITH keys
- [ ] `requirements.txt` installs clean; Docker build OK

## App Health
- [ ] FastAPI `/health` returns 200
- [ ] Streamlit chat renders; bilingual output + source tags visible
- [ ] RAG retrieval returns at least 1 source for seeded queries

## Monitoring & Tests
- [ ] LangSmith traces visible for one full conversation
- [ ] `pytest -q` green; Postman collection passes

## Deploy
- [ ] Backend on Railway/Render (free) running
- [ ] Streamlit Cloud app connected to backend URL
- [ ] Supabase pgvector reachable; tables migrated
