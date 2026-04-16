import asyncio
from contextlib import asynccontextmanager, suppress
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse

from config import CLEANUP_INTERVAL_SECONDS
from routes.health import router as health_router
from routes.session import router as session_router
from routes.segment import router as segment_router
from routes.control import router as control_router  # Task 6.2: Register control router
from session_manager import SessionNotFoundError, session_manager


async def _cleanup_loop() -> None:
	while True:
		await asyncio.sleep(CLEANUP_INTERVAL_SECONDS)
		await session_manager.cleanup_expired()


@asynccontextmanager
async def lifespan(_: FastAPI):
	cleanup_task = asyncio.create_task(_cleanup_loop())
	try:
		yield
	finally:
		cleanup_task.cancel()
		with suppress(asyncio.CancelledError):
			await cleanup_task

app = FastAPI(title="SSAI POC", version="0.1.0-day5", lifespan=lifespan)
app.include_router(health_router)
app.include_router(session_router)
app.include_router(segment_router)  # Day 4: manifest and segment serving routes
app.include_router(control_router)   # Day 5: mid-roll trigger control


@app.get("/", include_in_schema=False)
async def serve_ui():
    return FileResponse(Path(__file__).parent / "index.html", media_type="text/html")


@app.exception_handler(SessionNotFoundError)
async def handle_session_not_found(_: Request, exc: SessionNotFoundError) -> JSONResponse:
	return JSONResponse(status_code=404, content={"detail": str(exc)})
