from __future__ import annotations

import asyncio
import time
import uuid

from config import SESSION_TTL_SECONDS
from models import Session


class SessionNotFoundError(KeyError):
    pass


class SessionManager:
    def __init__(self, ttl_seconds: int = SESSION_TTL_SECONDS) -> None:
        self._ttl_seconds = ttl_seconds
        self._sessions: dict[str, Session] = {}
        self._locks: dict[str, asyncio.Lock] = {}
        self._global_lock = asyncio.Lock()

    async def create_session(self, content_id: str) -> Session:
        session_id = str(uuid.uuid4())
        session = Session(
            session_id=session_id,
            created_at=time.time(),
            content_id=content_id,
        )
        async with self._global_lock:
            self._sessions[session_id] = session
            self._locks[session_id] = asyncio.Lock()
        return session

    async def get_session(self, session_id: str) -> Session:
        session = self._sessions.get(session_id)
        if session is None:
            raise SessionNotFoundError(f"session '{session_id}' not found")
        return session

    async def update_session(self, session_id: str, **fields: object) -> Session:
        session = await self.get_session(session_id)
        lock = await self._get_lock(session_id)
        async with lock:
            for key, value in fields.items():
                if not hasattr(session, key):
                    raise AttributeError(f"session has no field '{key}'")
                setattr(session, key, value)
        return session

    async def cleanup_expired(self) -> int:
        now = time.time()
        async with self._global_lock:
            expired_ids = [
                session_id
                for session_id, session in self._sessions.items()
                if (now - session.created_at) > self._ttl_seconds
            ]
            for session_id in expired_ids:
                self._sessions.pop(session_id, None)
                self._locks.pop(session_id, None)
        return len(expired_ids)

    async def _get_lock(self, session_id: str) -> asyncio.Lock:
        async with self._global_lock:
            lock = self._locks.get(session_id)
            if lock is None:
                raise SessionNotFoundError(f"session '{session_id}' not found")
            return lock


session_manager = SessionManager()
