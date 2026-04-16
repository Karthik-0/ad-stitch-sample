"""SCTE-35 cue detection and parsing from HLS manifests.

Extracts splice points from HLS tags:
  - #EXT-X-CUE-OUT:{duration}
  - #EXT-X-CUE-IN
  - #EXT-OATCLS-SCTE35:{base64_payload}
"""

import re
import logging
from typing import Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Match: #EXT-X-CUE-OUT:30 or #EXT-X-CUE-OUT:30.0
CUE_OUT_PATTERN = re.compile(r'^#EXT-X-CUE-OUT:(\d+(?:\.\d+)?)$')

# Match: #EXT-X-CUE-IN
CUE_IN_PATTERN = re.compile(r'^#EXT-X-CUE-IN')

# Match: #EXT-OATCLS-SCTE35:/DAAA... or #EXT-X-OATCLS-SCTE35:/DAAA...
SCTE35_PAYLOAD_PATTERN = re.compile(r'^#EXT-(?:X-)?OATCLS-SCTE35:(.+)$')


@dataclass
class Scte35Cue:
    """Represents a detected SCTE-35 splice point."""
    cue_id: str  # Unique identifier (UUID or hash of manifest position)
    duration_sec: float  # Duration of ad avail in seconds
    start_sequence: int  # Media sequence where #EXT-X-CUE-OUT appears
    state: str = "out"  # "out" (ad avail open) or "in" (ad avail closed)
    payload: Optional[str] = None  # Base64 SCTE-35 payload if present


def parse_cue_out(line: str) -> Optional[float]:
    """
    Extract duration from #EXT-X-CUE-OUT tag.
    
    Args:
        line: Manifest line (e.g., "#EXT-X-CUE-OUT:30")
    
    Returns:
        Duration in seconds, or None if not a valid CUE-OUT tag
    """
    match = CUE_OUT_PATTERN.match(line.strip())
    if match:
        return float(match.group(1))
    return None


def parse_cue_in(line: str) -> bool:
    """
    Detect #EXT-X-CUE-IN tag.
    
    Args:
        line: Manifest line
    
    Returns:
        True if this is a CUE-IN tag, False otherwise
    """
    return bool(CUE_IN_PATTERN.match(line.strip()))


def parse_scte35_payload(line: str) -> Optional[str]:
    """
    Extract Base64 SCTE-35 payload from manifest.
    
    Args:
        line: Manifest line (e.g., "#EXT-OATCLS-SCTE35:/DAAA...")
    
    Returns:
        Base64 payload string, or None if not a SCTE35 payload tag
    """
    match = SCTE35_PAYLOAD_PATTERN.match(line.strip())
    if match:
        return match.group(1)
    return None


def detect_scte35_cues(
    manifest: str,
    media_sequence: int,
    processed_cue_ids: Optional[list[str]] = None,
) -> list[Scte35Cue]:
    """
    Scan manifest for SCTE-35 cue tags and return newly detected cues.
    
    A cue is considered "new" if its ID hasn't been seen before (tracked in processed_cue_ids).
    
    Args:
        manifest: HLS playlist content
        media_sequence: Current MEDIA-SEQUENCE from manifest (used to anchor cue position)
        processed_cue_ids: List of cue IDs already handled; new cues excluded from this list
    
    Returns:
        List of Scte35Cue objects for previously unseen cues
    """
    if processed_cue_ids is None:
        processed_cue_ids = []
    
    lines = manifest.split('\n')
    new_cues = []
    current_state = "in"  # Tracks whether we're inside or outside an ad avail
    segment_index = 0
    last_payload = None
    
    for line in lines:
        stripped = line.strip()
        
        # Track segment progression
        if stripped.startswith('#EXTINF:'):
            segment_index += 1
            continue
        
        # Parse CUE-OUT (ad avail starts)
        duration = parse_cue_out(stripped)
        if duration is not None:
            current_state = "out"
            # Generate a deterministic cue ID based on manifest position
            # In production, use the SCTE-35 cue_id or splice_insert() splice_command_type
            cue_id = f"cue-seq{media_sequence + segment_index}"
            
            if cue_id not in processed_cue_ids:
                cue = Scte35Cue(
                    cue_id=cue_id,
                    duration_sec=duration,
                    start_sequence=media_sequence + segment_index,
                    state="out",
                    payload=last_payload,
                )
                new_cues.append(cue)
                logger.info(
                    f"✓ Detected new SCTE-35 CUE-OUT: {cue_id} "
                    f"duration={duration}s sequence={cue.start_sequence}"
                )
            continue
        
        # Parse CUE-IN (ad avail ends)
        if parse_cue_in(stripped):
            current_state = "in"
            logger.debug(f"✓ Detected SCTE-35 CUE-IN at sequence {media_sequence + segment_index}")
            continue
        
        # Parse SCTE-35 payload (optional, stored if present)
        payload = parse_scte35_payload(stripped)
        if payload:
            last_payload = payload
            continue
    
    return new_cues
