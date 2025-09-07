from fastapi import APIRouter
from pydantic import BaseModel
from program_engine import ProgramEngine, is_crisis

router = APIRouter()

engine = ProgramEngine(db_path="sehat.db", programs_folder="programs")

class EnrollReq(BaseModel):
    user_id: str
    program_id: str

class NextReq(BaseModel):
    user_id: str
    program_id: str
    user_message: str | None = None  # optional reflection; crisis check


@router.get("/list")
def list_programs():
    return engine.registry.list_programs()


@router.post("/enroll")
def enroll(r: EnrollReq):
    engine.enroll(r.user_id, r.program_id)
    return {"ok": True}


@router.post("/next")
def next_step(r: NextReq):
    if r.user_message and is_crisis(r.user_message):
        return {
            "message": (
                "⚠️ If you’re in immediate danger, please contact local emergency services now. "
                "You are not alone—reach out to someone you trust. "
                "In Pakistan, consider the Umang helpline (1099) or local emergency numbers."
            ),
            "stopped": True
        }
    msg = engine.next_step(r.user_id, r.program_id)
    return {"message": msg, "stopped": False}
