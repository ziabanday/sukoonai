from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

# Import routers
import api_program
import query_api   # Q&A chatbot API

app = FastAPI(title="SukoonAI MVP")

# Templates (UI pages)
templates = Jinja2Templates(directory="templates")

# Mount static directory (for favicon + logo)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Include routers
app.include_router(api_program.router, prefix="/api/program", tags=["programs"])
app.include_router(query_api.router,  prefix="/api/query",   tags=["query"])

# Root → serve the wellness UI
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("program.html", {"request": request})

# Simple health check
@app.get("/ping")
async def ping():
    return {"status": "ok", "message": "SukoonAI is running"}
