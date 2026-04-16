# SCTE-35 Integration Implementation Summary

**Date**: April 16, 2026  
**Status**: ✅ Complete and Tested

## Overview

SCTE-35 integration has been added to the SSAI POC, enabling **automatic ad break insertion** based on splice markers in HLS manifests. This replaces manual `/trigger-ad-break` HTTP requests with passive detection and auto-triggering.

## What Was Implemented

### 1. **SCTE-35 Parser Module** (`scte35_parser.py`)

Detects and extracts splice points from HLS manifests:

| Function | Purpose |
|----------|---------|
| `parse_cue_out(line)` | Extract duration from `#EXT-X-CUE-OUT:30` tags |
| `parse_cue_in(line)` | Detect `#EXT-X-CUE-IN` end-of-ad markers |
| `parse_scte35_payload(line)` | Extract Base64 SCTE-35 binary payload |
| `detect_scte35_cues(manifest, media_sequence, processed_cue_ids)` | Scan manifest for new cues; prevents re-triggering |

**Data Structure:**
```python
@dataclass
class Scte35Cue:
    cue_id: str           # Unique identifier (e.g., "cue-seq723")
    duration_sec: float   # Ad avail duration in seconds
    start_sequence: int   # Media sequence where cue appears
    state: str            # "out" or "in"
    payload: Optional[str]  # Base64 SCTE-35 payload if present
```

### 2. **Session State Tracking** (Updated `models.py`)

Added field to `Session` dataclass:
```python
processed_scte35_cue_ids: list[str] = field(default_factory=list)
```

Prevents re-injection of the same cue across multiple manifest polls.

### 3. **Auto-Trigger Logic** (Updated `routes/segment.py`)

In `serve_variant_manifest()`:
- After reading live variant, detect new SCTE-35 cues
- For each new cue:
  - Mark as processed (add to `processed_scte35_cue_ids`)
  - Fetch and condition ad creative (reusing VAST pipeline)
  - Set session state to `PENDING` with splice_at_sequence = cue.start_sequence
  - On next manifest request, inject ad at that splice point

### 4. **Comprehensive Unit Tests** (`tests/test_scte35_parser.py`)

**16 tests covering:**
- Tag parsing: `#EXT-X-CUE-OUT:30`, `#EXT-X-CUE-IN`, payloads
- Cue detection: single, multiple, filtering
- Sequence calculation: media-sequence anchoring
- State tracking: processed cue deduplication
- Edge cases: whitespace, invalid tags, empty manifests

**Result**: `Ran 16 tests in 0.000s OK`

### 5. **Documentation**

- `SCTE35_EXAMPLES.md`: Sample HLS manifests with SCTE-35 markers
- Updated `README.md`: Testing section + SCTE-35 auto-trigger guide

## How It Works

### Data Flow

```
Live FFmpeg Output (with SCTE-35 markers)
          ↓
    manifest: #EXT-X-CUE-OUT:30
          ↓
Player requests /session/{sid}/720p.m3u8
          ↓
Stitcher reads manifest
          ↓
scte35_parser.detect_scte35_cues()
          ↓
New cue detected? → Check processed_scte35_cue_ids
          ↓ (new cue)
Auto-fetch VAST → Condition ad → Set session.pending_pod
          ↓
          ├─ If splice_at_sequence reached: inject ad
          ├─ Else: return live-only manifest
          ↓
Player sees #EXT-X-DISCONTINUITY + ad segments + #EXT-X-CUE-IN
          ↓
Beacon firing during ad playback
```

## Behavior

### ✅ What it Does

1. **Detects New Cues**: Scans manifest for `#EXT-X-CUE-OUT` every variant request
2. **Prevents Re-Triggering**: Tracks `cue_id` in session state
3. **Auto-Fetches Ads**: Calls VAST without manual operator action
4. **Respects Ad State**: Won't trigger if already processing an ad
5. **Segment-Aligned**: Splice occurs at exact live-window edge (no frame-level precision needed)
6. **Backward Compatible**: Manual `/trigger-ad-break` still works alongside SCTE-35

### ⚠️ Current Limitations

- **Cue IDs are auto-generated** based on manifest sequence, not parsed from SCTE-35 binary
  - *Improvement*: Can parse splice_insert() command type from binary payload (future)
- **Only `#EXT-X-CUE-OUT` duration is used**; full SCTE-35 metadata ignored
- **Single cue triggers one ad break**; concurrent ads not supported
- **No provision for cue update/replacement** after trigger (cue marked processed permanently)

## Testing

### Unit Tests
```bash
cd ssai-poc
python -m unittest tests.test_scte35_parser -v
# Result: 16 tests, all passed
```

### Integration Test (Manual)

1. **Prepare a manifest with SCTE-35 markers** (edit `storage/live/video-720p.m3u8`):
   ```m3u8
   #EXT-X-CUE-OUT:30
   #EXTINF:6.0,
   segment-xyz.ts
   ```

2. **Create session and playback:**
   ```bash
   SID=$(curl -X POST http://localhost:8000/session/new \
     -H "Content-Type: application/json" \
     -d '{"content_id":"scte35-test"}' \
     | jq -r .session_id)
   
   curl http://localhost:8000/session/$SID/720p.m3u8
   ```

3. **Watch logs for auto-trigger:**
   ```
   ✓ Detected new SCTE-35 CUE-OUT: cue-seq723 duration=30.0s sequence=723
   ✓ SCTE-35 auto-trigger: cue cue-seq723 duration=30.0s at sequence 723
   ```

## Files Changed

| File | Change |
|------|--------|
| `scte35_parser.py` | New module (160 lines) |
| `models.py` | Added `processed_scte35_cue_ids` field to Session |
| `routes/segment.py` | Added SCTE-35 detection + auto-trigger logic (50 lines) |
| `tests/test_scte35_parser.py` | New test suite (200 lines, 16 tests) |
| `README.md` | Added SCTE-35 testing section |
| `SCTE35_EXAMPLES.md` | New guide with manifest examples |

## Comparison: Manual vs. SCTE-35

| Aspect | Manual `/trigger-ad-break` | SCTE-35 Auto |
|--------|--------------------------|--------------|
| **Trigger** | HTTP endpoint (operator-driven) | Manifest splice marker (automated) |
| **Timing** | Playback-relative (delay from now) | Sequence-aligned (at cue position) |
| **Use Case** | Ad testing, on-demand breaks | Broadcast with pre-planned breaks |
| **Workflow** | Operator clicks trigger, waits for ad | Encoder embeds cues, stitcher reacts |
| **Scaling** | Per-session HTTP overhead | Zero overhead per cue |

## Next Steps (Optional Enhancements)

1. **Binary SCTE-35 Payload Parsing**
   - Decode `/DAAA...` Base64 to extract splice_command_type, splice_insert details
   - Use UTC time from payload for timestamp-based triggering

2. **Cue Update Support**
   - Allow cue re-submission with updated duration
   - Reset `processed_cue_ids` when manifest updates

3. **Multiple Concurrent Ads**
   - Queue multiple cues instead of ignoring during ad_state != NONE
   - Inject sequentially after current ad completes

4. **SCTE-35 Playback Position Tracking**
   - Correlate splices to player's actual playback position
   - Adjust splice timing for player drift

## Verification Checklist

- ✅ SCTE-35 parser module created with full regex support
- ✅ Session model extended with cue tracking
- ✅ Auto-trigger logic integrated into segment routes
- ✅ 16 new unit tests, all passing
- ✅ Backward compatibility: manual triggers still work
- ✅ Documentation updated (README, examples)
- ✅ No syntax errors or runtime issues
- ✅ All 45 tests pass (16 new + 29 existing)

## Usage

With SCTE-35 enabled, operators can:

1. **Embed cues in broadcast stream** via encoder settings
2. **Let stitcher auto-detect** on manifest polls
3. **Focus on monitoring** rather than manual triggering
4. **Combine with manual triggers** for testing/fallback

For details, see:
- Implementation: [scte35_parser.py](scte35_parser.py)
- Testing guide: [SCTE35_EXAMPLES.md](SCTE35_EXAMPLES.md)
- Integration: [README.md](README.md#scte-35-auto-trigger-testing)
