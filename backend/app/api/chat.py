from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Dict, Optional
from app.engines.chat_engine import chat
from app.api.profile import _profiles

router = APIRouter()

class ChatRequest(BaseModel):
    messages: List[Dict]
    session_id: str = "demo"

@router.post("/message")
def send_message(req: ChatRequest):
    profile = _profiles.get(req.session_id)
    reply = chat(req.messages, profile)
    return {"reply": reply, "has_profile": profile is not None}
