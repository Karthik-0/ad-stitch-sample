from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel


class AdState(str, Enum):
    NONE = "none"
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"


@dataclass
class TrackingEvent:
    event: str
    url: str
    fired: bool = False


@dataclass
class BeaconEvent:
    """Task 2.3: Record of a beacon firing event for audit trail."""
    event_type: str  # impression, firstQuartile, midpoint, thirdQuartile, complete
    url: str
    timestamp: datetime
    outcome: str  # success, 4xx, 5xx, timeout, error


@dataclass
class ConditionedAd:
    creative_id: str
    duration_sec: float
    renditions: dict[str, list[tuple[str, float]]] = field(default_factory=dict)
    tracking: list[TrackingEvent] = field(default_factory=list)
    impression_urls: list[str] = field(default_factory=list)


@dataclass
class AdPod:
    pod_id: str
    ads: list[ConditionedAd]
    total_duration: float
    segments_served: dict[str, int] = field(default_factory=dict)  # Task 2.1: rendition → count
    beacon_history: list[BeaconEvent] = field(default_factory=list)  # Task 2.2: audit trail


@dataclass
class Session:
    session_id: str
    created_at: float
    content_id: str
    ad_state: AdState = AdState.NONE
    pending_pod: Optional[AdPod] = None
    active_pod: Optional[AdPod] = None
    pod_history: list[str] = field(default_factory=list)
    splice_at_sequence: Optional[int] = None
    last_live_sequence: Optional[int] = None
    pod_progress_lock: asyncio.Lock = field(default_factory=asyncio.Lock)  # Task 2.4: concurrency coordination
    processed_scte35_cue_ids: list[str] = field(default_factory=list)  # SCTE-35: Track seen cues to prevent re-trigger


class NewSessionRequest(BaseModel):
    content_id: str
    preroll: bool = True


class NewSessionResponse(BaseModel):
    session_id: str
    master_url: str


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
