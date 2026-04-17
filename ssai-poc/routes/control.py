"""
Mid-roll ad break trigger control endpoint.

Allows operators to manually trigger ad insertion via HTTP POST,
simulating SCTE-35 cue reception for testing and validation.
"""

import logging
import math
from typing import Optional
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from config import ACTIVE_VAST_TAG, LIVE_DIR, RENDITIONS, SEGMENT_DURATION
from manifest_builder import get_next_media_sequence
from session_manager import session_manager
from models import AdState

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/session", tags=["control"])


def _calculate_splice_sequence(
    last_live_sequence: Optional[int],
    fallback_next_sequence: int,
    duration_seconds: int,
) -> int:
    """Schedule the splice into a future portion of the live window.

    The per-session playback anchor can lag behind the current source playlist when
    the client or an intermediate proxy serves a stale manifest. If we schedule a
    mid-roll into that already-published window, the stitched variant can jump
    backwards and leave the player buffering at the live edge. Guard against that
    by never scheduling earlier than the source playlist's current next sequence.
    """
    observed_next_sequence = (
        last_live_sequence + 1 if last_live_sequence is not None else fallback_next_sequence
    )
    base_sequence = max(observed_next_sequence, fallback_next_sequence)
    segment_offset = max(1, math.ceil(duration_seconds / SEGMENT_DURATION))
    return base_sequence + segment_offset


def _normalize_ad_tag(ad_tag: Optional[str]) -> Optional[str]:
    if ad_tag is None:
        return None
    normalized = ad_tag.strip()
    if not normalized:
        return None
    if not (normalized.startswith("http://") or normalized.startswith("https://")):
        raise HTTPException(status_code=400, detail="ad_tag must be a valid http/https URL")
    return normalized


class TriggerAdBreakRequest(BaseModel):
    duration: int  # seconds


@router.post("/{sid}/trigger-ad-break")
async def trigger_ad_break(
    sid: str,
    duration: int = Query(..., ge=1, le=120, description="Ad break duration in seconds"),
    ad_tag: Optional[str] = Query(None, description="Optional ad tag URL override for this break"),
):
    """
    Task 5.2: Manually trigger an ad break insertion with duration parameter.
    
    Returns 202 Accepted immediately, fetches VAST and conditions in background.
    
    Args:
        sid: Session ID
        duration: Ad duration in seconds (1-120)
        
    Returns:
        202 Accepted with marker to inject on next variant request
        
    Raises:
        400: Invalid duration
        404: Session not found
        503: Ad conditioning failed
    """
    # Task 5.3: Validate duration parameter
    if duration < 1 or duration > 120:
        raise HTTPException(
            status_code=400,
            detail="Invalid duration; must be 1–120 seconds",
        )
    
    # Get session
    try:
        session = await session_manager.get_session(sid)
    except Exception:
        raise HTTPException(status_code=404, detail="Session not found")
    
    live_variant_path = None
    for rendition in reversed(RENDITIONS):
        candidate = Path(LIVE_DIR) / f"video-{rendition['name']}.m3u8"
        if candidate.exists():
            live_variant_path = candidate
            break

    if live_variant_path is None:
        raise HTTPException(status_code=503, detail="No live playlist available for splice scheduling")

    next_media_sequence = get_next_media_sequence(live_variant_path.read_text())
    splice_at_sequence = _calculate_splice_sequence(
        last_live_sequence=session.last_live_sequence,
        fallback_next_sequence=next_media_sequence,
        duration_seconds=duration,
    )
    selected_ad_tag = _normalize_ad_tag(ad_tag)

    # Task 5.4: Mark session as pending and anchor it at the next live media sequence.
    session.ad_state = AdState.PENDING
    session.splice_at_sequence = splice_at_sequence
    session.pending_ad_tag = selected_ad_tag
    logger.info(
        f"Mid-roll trigger set PENDING for session {sid}, duration={duration}s, "
        f"last_live_sequence={session.last_live_sequence}, splice_at={splice_at_sequence}, "
        f"ad_tag={'default' if selected_ad_tag is None else selected_ad_tag}"
    )

    # Return 202 Accepted immediately
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=202,
        content={
            "status": "accepted",
            "message": "Mid-roll trigger scheduled",
            "ad_tag": selected_ad_tag or ACTIVE_VAST_TAG,
        },
    )
