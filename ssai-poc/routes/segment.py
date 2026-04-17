"""
HLS segment serving routes for live passthrough and conditioned ad segments.

Endpoints:
  - GET /session/{sid}/seg/live/{filename}: Serve live TS segments with validation
  - GET /session/{sid}/seg/ad/{rendition}/{index}: Serve conditioned ad TS segments
"""

import re
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Path as PathParam
from fastapi.responses import FileResponse

from config import LIVE_DIR, ADS_DIR
from session_manager import session_manager


router = APIRouter(prefix="/session", tags=["segment"])

PLAYLIST_RESPONSE_HEADERS = {
    "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
    "Pragma": "no-cache",
    "Expires": "0",
}


# Filename validation: restricts to expected FFmpeg naming pattern
LIVE_FILENAME_PATTERN = re.compile(r'^video-[a-z0-9]+\d+\.ts$')


def _flatten_pod_segments(active_pod, rendition: str):
    flattened = []
    for ad in active_pod.ads:
        segments = ad.renditions.get(rendition, [])
        for filename, duration in segments:
            flattened.append((ad, filename, duration))
    return flattened


def _playlist_response(content: str):
    from fastapi.responses import Response

    return Response(
        content=content,
        media_type="application/vnd.apple.mpegurl",
        headers=PLAYLIST_RESPONSE_HEADERS,
    )


@router.get("/{sid}/seg/live/{filename}")
async def serve_live_segment(
    sid: str = PathParam(..., description="Session ID"),
    filename: str = PathParam(..., description="Live segment filename"),
):
    """
    Serve live TS segments from configured live storage.
    
    Validates filename against strict pattern to prevent path traversal.
    Returns video/mp2t with segment bytes or 404 if not found.
    
    Args:
        sid: Session identifier (UUID)
        filename: Segment filename (video-*.ts)
        
    Returns:
        FileResponse with segment data, video/mp2t media type
        
    Raises:
        HTTPException 400: Invalid filename format
        HTTPException 404: Segment not found
    """
    # Task 3.2: Strict filename validation
    if not LIVE_FILENAME_PATTERN.match(filename):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid live segment filename: {filename}",
        )
    
    # Construct safe path (no traversal possible due to validation)
    segment_path = Path(LIVE_DIR) / filename
    
    # Task 3.3: Stream valid live TS files with video/mp2t
    if not segment_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Live segment not found",
        )
    
    return FileResponse(
        segment_path,
        media_type="video/mp2t",
        filename=filename,
    )


@router.get("/{sid}/seg/ad/{rendition}/{index:int}")
async def serve_ad_segment(
    sid: str = PathParam(..., description="Session ID"),
    rendition: str = PathParam(..., description="Rendition name (e.g., 240p)"),
    index: int = PathParam(..., description="Segment index in rendition"),
):
    """
    Serve conditioned ad segments for active or completed ad pods.
    
    Tasks 4.1-4.6: Track progress, detect quartile thresholds, fire beacons asynchronously.
    """
    import asyncio
    import logging
    from beacon_firer import fire_tracking_event
    
    logger = logging.getLogger(__name__)
    
    # Get session and verify pod context
    try:
        session = await session_manager.get_session(sid)
    except Exception:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Check if there's an active pod
    if not session.active_pod:
        raise HTTPException(status_code=404, detail="No active pod for this session")
    
    active_pod = session.active_pod
    flattened_segments = _flatten_pod_segments(active_pod, rendition)
    if not flattened_segments:
        raise HTTPException(status_code=404, detail="Rendition not found")

    if index >= len(flattened_segments):
        raise HTTPException(status_code=404, detail="Segment index out of range")

    conditioned_ad, filename, _ = flattened_segments[index]
    
    # Task 4.1: Increment segments_served counter
    async with session.pod_progress_lock:  # Task 4.5: Coordinate with lock
        if rendition not in active_pod.segments_served:
            active_pod.segments_served[rendition] = 0
        active_pod.segments_served[rendition] += 1
        
        # Task 4.2: Calculate progress and detect quartile thresholds
        progress = active_pod.segments_served[rendition] / len(flattened_segments)
        
        # Determine which quartiles to fire
        quartile_events = []
        if progress >= 0.25 and 0.25 not in getattr(active_pod, '_fired_thresholds', []):
            active_pod._fired_thresholds = getattr(active_pod, '_fired_thresholds', []) + [0.25]
            quartile_events.append("firstQuartile")
        if progress >= 0.5 and 0.5 not in getattr(active_pod, '_fired_thresholds', []):
            active_pod._fired_thresholds = getattr(active_pod, '_fired_thresholds', []) + [0.5]
            quartile_events.append("midpoint")
        if progress >= 0.75 and 0.75 not in getattr(active_pod, '_fired_thresholds', []):
            active_pod._fired_thresholds = getattr(active_pod, '_fired_thresholds', []) + [0.75]
            quartile_events.append("thirdQuartile")
        if progress >= 1.0 and 1.0 not in getattr(active_pod, '_fired_thresholds', []):
            active_pod._fired_thresholds = getattr(active_pod, '_fired_thresholds', []) + [1.0]
            quartile_events.append("complete")
            from models import AdState
            if active_pod.pod_id not in session.pod_history:
                session.pod_history.append(active_pod.pod_id)
            session.ad_state = AdState.COMPLETED
            session.pending_ad_tag = None
            if active_pod.pod_id.startswith(f"midroll-{sid}-"):
                session.splice_at_sequence = None
        
        # Task 4.6: Record events in beacon_history
        for event in conditioned_ad.tracking:
            if event.event in quartile_events and not event.fired:
                # Create beacon event record
                from models import BeaconEvent
                from datetime import datetime
                beacon_event = BeaconEvent(
                    event_type=event.event,
                    url=event.url,
                    timestamp=datetime.utcnow(),
                    outcome="pending",
                )
                active_pod.beacon_history.append(beacon_event)
                event.fired = True
        
        # Session object is stored as reference, changes are automatically persisted
        
        # Task 4.4: Fire beacons asynchronously without blocking response
        for event in conditioned_ad.tracking:
            if event.event in quartile_events and event.url:
                asyncio.create_task(
                    fire_tracking_event(url=event.url, event_type=event.event)
                )
    
    # Serve the segment
    creative_id = conditioned_ad.creative_id
    segment_path = Path(ADS_DIR) / creative_id / filename
    
    if not segment_path.exists():
        raise HTTPException(status_code=404, detail="Ad segment not found on disk")
    
    return FileResponse(
        segment_path,
        media_type="video/mp2t",
        filename=filename,
    )


@router.get("/{sid}/master.m3u8")
async def serve_master_manifest(
    sid: str = PathParam(..., description="Session ID"),
):
    """
    Serve session-specific master playlist.
    
    Returns rewritten master with variant URIs routed to /session/{sid}/{rendition}.m3u8
    """
    from manifest_builder import build_master
    
    try:
        session = await session_manager.get_session(sid)
    except Exception:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Accept both common master filenames produced by local FFmpeg workflows.
    live_master_path = Path(LIVE_DIR) / "video.m3u8"
    if not live_master_path.exists():
        live_master_path = Path(LIVE_DIR) / "master.m3u8"
    if not live_master_path.exists():
        raise HTTPException(status_code=500, detail="Live master not available")
    
    live_master = live_master_path.read_text()
    rewritten = build_master(live_master, sid)

    return _playlist_response(rewritten)


@router.get("/{sid}/{rendition}.m3u8")
async def serve_variant_manifest(
    sid: str = PathParam(..., description="Session ID"),
    rendition: str = PathParam(..., description="Rendition name (e.g., 240p)"),
):
    """
    Serve session-specific variant playlist.
    
    Day 5 dynamic ad pod loading:
      - If session has no active_pod: fetch VAST, condition, load (with 5s timeout)
      - If soft timeout or conditioning fails: return live-only variant
      - If active_pod exists: inject pre-roll and return
    """
    import asyncio
    import logging
    from manifest_builder import (
        build_variant_live_only,
        build_variant_with_preroll,
        get_next_media_sequence,
        get_last_media_sequence,
    )
    from vast_client import fetch_vast
    from ad_conditioner import condition_ad
    from beacon_firer import fire_tracking_event
    from config import ACTIVE_VAST_TAG
    
    logger = logging.getLogger(__name__)

    async def _condition_ads(parsed_ads):
        conditioned_ads = []
        for parsed_ad in parsed_ads:
            conditioned_ads.append(await condition_ad(parsed_ad))
        return conditioned_ads
    
    try:
        session = await session_manager.get_session(sid)
    except Exception:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Read live variant from live storage
    live_variant_path = Path(LIVE_DIR) / f"video-{rendition}.m3u8"
    if not live_variant_path.exists():
        raise HTTPException(status_code=404, detail=f"Rendition {rendition} not available")
    
    live_variant = live_variant_path.read_text()
    
    # SCTE-35 detection: Check for new cues in manifest
    from scte35_parser import detect_scte35_cues
    from manifest_builder import get_last_media_sequence as get_media_seq
    
    try:
        current_media_seq = get_media_seq(live_variant)
        new_cues = detect_scte35_cues(
            live_variant,
            current_media_seq,
            processed_cue_ids=session.processed_scte35_cue_ids,
        )
        
        # Auto-trigger ad breaks for newly detected SCTE-35 cues
        for cue in new_cues:
            session.processed_scte35_cue_ids.append(cue.cue_id)
            
            # Automatically trigger mid-roll with cue duration
            if session.ad_state == AdState.NONE or session.ad_state == AdState.COMPLETED:
                session.ad_state = AdState.PENDING
                session.splice_at_sequence = cue.start_sequence
                
                # Fetch and condition the ad for this cue
                try:
                    parsed_ads = await asyncio.wait_for(
                        fetch_vast(ACTIVE_VAST_TAG),
                        timeout=5.0,
                    )
                    if parsed_ads:
                        conditioned_ads = await _condition_ads(parsed_ads)
                        total_duration = sum(ad.duration_sec for ad in conditioned_ads)
                        from models import AdPod
                        session.pending_pod = AdPod(
                            pod_id=f"scte35-cue-{cue.cue_id}",
                            ads=conditioned_ads,
                            total_duration=total_duration,
                        )
                        logger.info(
                            f"✓ SCTE-35 auto-trigger: cue {cue.cue_id} "
                            f"pod_duration={total_duration}s at sequence {cue.start_sequence}"
                        )
                except Exception as e:
                    logger.warning(f"✗ SCTE-35 ad conditioning failed for {cue.cue_id}: {e}")
                    session.ad_state = AdState.NONE
            else:
                logger.info(f"⊘ SCTE-35 cue {cue.cue_id} ignored (ad_state={session.ad_state})")
    except Exception as e:
        logger.warning(f"✗ SCTE-35 detection error: {e}")
    
    # Mid-roll queue handling: if trigger set PENDING, condition the ad inline here.
    from models import AdState
    if session.ad_state == AdState.PENDING and not session.pending_pod:
        selected_ad_tag = session.pending_ad_tag
        # Prefer reusing an already-conditioned creative (from pre-roll cache) to
        # avoid an unnecessary VAST round-trip during mid-roll insertion.
        source_pod = session.active_pod
        if selected_ad_tag:
            try:
                parsed_ads = await asyncio.wait_for(
                    fetch_vast(selected_ad_tag),
                    timeout=5.0,
                )
                if parsed_ads:
                    conditioned_ads = await _condition_ads(parsed_ads)
                    total_duration = sum(ad.duration_sec for ad in conditioned_ads)
                    from models import AdPod
                    session.pending_pod = AdPod(
                        pod_id=f"midroll-{sid}-{session.splice_at_sequence}",
                        ads=conditioned_ads,
                        total_duration=total_duration,
                    )
                    logger.info(f"✓ Mid-roll pod conditioned from selected ad tag for session {sid}")
            except Exception as e:
                logger.warning(f"✗ Mid-roll conditioning failed for session {sid}: {e}")
                if source_pod:
                    from models import AdPod
                    session.pending_pod = AdPod(
                        pod_id=f"midroll-{sid}-{session.splice_at_sequence}",
                        ads=source_pod.ads,
                        total_duration=source_pod.total_duration,
                    )
                    logger.info(f"↺ Mid-roll fallback: reused cached pod for session {sid}")
                else:
                    session.ad_state = AdState.NONE
                    session.pending_ad_tag = None
        elif source_pod:
            from models import AdPod
            session.pending_pod = AdPod(
                pod_id=f"midroll-{sid}-{session.splice_at_sequence}",
                ads=source_pod.ads,
                total_duration=source_pod.total_duration,
            )
            logger.info(f"✓ Mid-roll pod built from pre-roll cache for session {sid}")
        else:
            # No pre-roll cache yet — fetch and condition fresh
            try:
                parsed_ads = await asyncio.wait_for(
                    fetch_vast(ACTIVE_VAST_TAG),
                    timeout=5.0,
                )
                if parsed_ads:
                    conditioned_ads = await _condition_ads(parsed_ads)
                    total_duration = sum(ad.duration_sec for ad in conditioned_ads)
                    from models import AdPod
                    session.pending_pod = AdPod(
                        pod_id=f"midroll-{sid}-{session.splice_at_sequence}",
                        ads=conditioned_ads,
                        total_duration=total_duration,
                    )
                    logger.info(f"✓ Mid-roll pod conditioned inline for session {sid}")
            except Exception as e:
                logger.warning(f"✗ Mid-roll conditioning failed for session {sid}: {e}")
                session.ad_state = AdState.NONE
                session.pending_ad_tag = None

    current_next_sequence = get_next_media_sequence(live_variant)
    current_last_sequence = get_last_media_sequence(live_variant)
    session.last_live_sequence = current_last_sequence

    if session.pending_pod and session.splice_at_sequence is not None:
        if current_last_sequence < session.splice_at_sequence:
            rewritten = build_variant_live_only(live_variant, sid)
            return _playlist_response(rewritten)

        rewritten, should_promote = build_variant_with_preroll(
            live_variant,
            sid,
            session.pending_pod,
            rendition,
            ADS_DIR,
            splice_at_sequence=session.splice_at_sequence,
        )
        if should_promote:
            session.active_pod = session.pending_pod
            session.pending_pod = None
            session.ad_state = AdState.ACTIVE
            session.pending_ad_tag = None
            # The splice anchor is only needed for the first stitched response.
            # Keeping it set pins subsequent manifests to an old media sequence.
            session.splice_at_sequence = None
            session.last_live_sequence = max(
                session.last_live_sequence or current_last_sequence,
                current_next_sequence - 1,
            )
        return _playlist_response(rewritten)

    # Task 3.1-3.5: Dynamic ad pod loading on first variant request
    if not session.active_pod:
        try:
            # Task 3.2: Soft timeout on VAST fetch
            parsed_ads = await asyncio.wait_for(
                fetch_vast(ACTIVE_VAST_TAG),
                timeout=5.0
            )
            
            if parsed_ads:
                try:
                    # Task 3.3: Wire through ad conditioner pipeline
                    conditioned_ads = await _condition_ads(parsed_ads)
                    total_duration = sum(ad.duration_sec for ad in conditioned_ads)
                    
                    # Task 3.4: Load into active_pod
                    from models import AdPod
                    session.active_pod = AdPod(
                        pod_id=f"preroll-{sid}",
                        ads=conditioned_ads,
                        total_duration=total_duration,
                    )
                    # Session object is stored as reference in session manager, changes persisted
                    
                    # Task 3.5: Fire impression beacon asynchronously
                    for conditioned_ad in conditioned_ads:
                        asyncio.create_task(
                            fire_tracking_event(
                                url=conditioned_ad.impression_urls[0] if conditioned_ad.impression_urls else "",
                                event_type="impression",
                            )
                        )
                    
                    logger.info(f"✓ Dynamic pod loaded for session {sid}")
                
                except Exception as e:
                    logger.warning(f"✗ Ad conditioning failed: {e}; using live-only variant")
                    session.active_pod = None
        
        except asyncio.TimeoutError:
            logger.warning(f"✗ VAST fetch timeout (5s) for session {sid}; using live-only variant")
            session.active_pod = None
        
        except Exception as e:
            logger.warning(f"✗ VAST fetch failed for session {sid}: {e}; using live-only variant")
            session.active_pod = None
    
    # Inject pre-roll if active pod exists
    active_pod_already_injected = bool(
        session.active_pod and session.active_pod.pod_id in session.pod_history
    )

    if session.active_pod and not active_pod_already_injected:
        splice_at_sequence = None
        if session.active_pod.pod_id.startswith(f"midroll-{sid}-") and session.splice_at_sequence is not None:
            # Safety valve for older sessions where splice anchor may still be set.
            if current_last_sequence < session.splice_at_sequence:
                splice_at_sequence = session.splice_at_sequence
            else:
                session.splice_at_sequence = None

        # Build variant with pre-roll injection
        rewritten, should_promote = build_variant_with_preroll(
            live_variant,
            sid,
            session.active_pod,
            rendition,
            ADS_DIR,
            splice_at_sequence=splice_at_sequence,
        )
        
        from models import AdState
        if should_promote:
            session.ad_state = AdState.ACTIVE
            # Session object is stored as reference, changes persisted
    else:
        # No active pod: return live-only variant with rewritten segment routes
        rewritten = build_variant_live_only(live_variant, sid)

    return _playlist_response(rewritten)
