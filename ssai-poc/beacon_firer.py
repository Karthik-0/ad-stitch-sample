"""
Async beacon URL firing for VAST tracking events.

Handles server-side firing of impression, quartile, and completion tracking URLs
without blocking segment responses. Provides resilience to network failures and
comprehensive logging for audit trails.
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional

import httpx

from models import BeaconEvent

logger = logging.getLogger(__name__)


async def fire_tracking_event(
    url: str,
    event_type: str,
    timeout: float = 10.0,
) -> BeaconEvent:
    """
    Fire a single beacon URL asynchronously with timeout and error handling.
    
    Task 1.2: Async HTTP GET request with 10s timeout, resilience to errors.
    
    Args:
        url: Tracking URL to fire (impression, quartile, etc.)
        event_type: Event type for logging (impression, firstQuartile, etc.)
        timeout: Timeout in seconds for HTTP request
        
    Returns:
        BeaconEvent with outcome status for audit trail
    """
    timestamp = datetime.utcnow()
    outcome = "error"
    
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(url)
            
            # Task 1.4: Error handling for different response statuses
            if response.status_code == 200:
                outcome = "success"
                logger.info(f"✓ Fired {event_type} beacon: {url}")
            elif 400 <= response.status_code < 500:
                outcome = "4xx"
                logger.warning(f"✗ 4xx beacon error ({response.status_code}): {event_type} {url}")
            else:
                outcome = "5xx"
                logger.warning(f"✗ 5xx beacon error ({response.status_code}): {event_type} {url}")
    
    except asyncio.TimeoutError:
        outcome = "timeout"
        logger.warning(f"✗ Beacon timeout ({timeout}s): {event_type} {url}")
    
    except httpx.RequestError as e:
        outcome = "error"
        logger.error(f"✗ Beacon request error: {event_type} {url} — {e}")
    
    except Exception as e:
        outcome = "error"
        logger.error(f"✗ Unexpected beacon error: {event_type} {url} — {e}")
    
    # Task 1.5: Return event for recording to beacon_history
    event = BeaconEvent(
        event_type=event_type,
        url=url,
        timestamp=timestamp,
        outcome=outcome,
    )
    
    return event


async def fire_tracking_events(
    pod,  # AdPod
    event_types: list[str],
) -> list[BeaconEvent]:
    """
    Task 1.3: Fire multiple beacon events from a pod's tracking_events list.
    
    Collects all tracking events matching the requested event types and fires
    them asynchronously in parallel.
    
    Args:
        pod: AdPod with ads and tracking metadata
        event_types: List of event types to fire (e.g., ["impression", "firstQuartile"])
        
    Returns:
        List of BeaconEvent outcomes for each fired URL
    """
    events = []
    
    # Extract tracking URLs from pod's first conditioned ad
    if not pod.ads or len(pod.ads) == 0:
        logger.warning("No conditioned ads in pod; skipping beacon firing")
        return events
    
    conditioned_ad = pod.ads[0]
    
    # Iterate through tracking events and find matching URLs
    for tracking_event in conditioned_ad.tracking:
        if tracking_event.event in event_types:
            # Fire beacon asynchronously and collect event
            beacon_event = await fire_tracking_event(
                url=tracking_event.url,
                event_type=tracking_event.event,
            )
            events.append(beacon_event)
    
    return events
