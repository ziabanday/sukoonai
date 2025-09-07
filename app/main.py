from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.routers.chat import router as chat_router
from app.utils.env import load_settings

app = FastAPI(title="SukoonAI - Medical Evidence Navigator (MVP)")

# Load settings early to fail fast if env is missing
_ = load_settings()

# Mount static files for simple web UI
base_dir = Path(__file__).resolve().parent.parent
web_dir = base_dir / "web"
static_dir = web_dir / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/", response_class=HTMLResponse)
def home():
    index_file = web_dir / "index.html"
    if index_file.exists():
        return index_file.read_text(encoding="utf-8")
    return HTMLResponse("<h1>SukoonAI</h1><p>Static UI not found.</p>")

# API routes
app.include_router(chat_router, prefix="/api")

@app.get("/healthz")
def health():
    return {"status": "ok"}
