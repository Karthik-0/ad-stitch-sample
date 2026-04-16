from fastapi import APIRouter, Request

from models import NewSessionRequest, NewSessionResponse
from session_manager import session_manager

router = APIRouter(prefix="/session", tags=["session"])


@router.post("/new", response_model=NewSessionResponse)
async def create_session(payload: NewSessionRequest, request: Request) -> NewSessionResponse:
    session = await session_manager.create_session(content_id=payload.content_id)
    base_url = str(request.base_url).rstrip("/")
    master_url = f"{base_url}/session/{session.session_id}/master.m3u8"
    return NewSessionResponse(session_id=session.session_id, master_url=master_url)
