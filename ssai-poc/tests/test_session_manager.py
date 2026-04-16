import unittest

from session_manager import SessionManager, SessionNotFoundError


class SessionManagerTestCase(unittest.IsolatedAsyncioTestCase):
    async def test_create_and_get_session(self) -> None:
        manager = SessionManager(ttl_seconds=3600)
        session = await manager.create_session(content_id="demo")
        loaded = await manager.get_session(session.session_id)
        self.assertEqual(loaded.session_id, session.session_id)
        self.assertEqual(loaded.content_id, "demo")

    async def test_update_session(self) -> None:
        manager = SessionManager(ttl_seconds=3600)
        session = await manager.create_session(content_id="demo")
        updated = await manager.update_session(session.session_id, content_id="demo-2")
        self.assertEqual(updated.content_id, "demo-2")

    async def test_get_unknown_session_raises(self) -> None:
        manager = SessionManager(ttl_seconds=3600)
        with self.assertRaises(SessionNotFoundError):
            await manager.get_session("missing")

    async def test_cleanup_expired_sessions(self) -> None:
        manager = SessionManager(ttl_seconds=-1)
        session = await manager.create_session(content_id="demo")
        removed = await manager.cleanup_expired()
        self.assertEqual(removed, 1)
        with self.assertRaises(SessionNotFoundError):
            await manager.get_session(session.session_id)


if __name__ == "__main__":
    unittest.main()
