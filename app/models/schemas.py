from pydantic import BaseModel, Field
from typing import List

class ChatRequest(BaseModel):
    question: str = Field(..., min_length=3, description="User's medical question")

class ChatResponse(BaseModel):
    answer: str
    sources: List[str] = []
