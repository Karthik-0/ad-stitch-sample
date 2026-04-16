# Server-Side Ad Stitching POC — Technical Specification

## 1. Overview

### 1.1 Purpose
Build a local proof-of-concept for Server-Side Ad Insertion (SSAI) into a live HLS stream, using Google's public sample VAST tags as the ad source. This POC replaces functionality currently provided by AWS MediaTailor.

### 1.2 Scope
**In scope:**
- Live RTMP ingest via OSSRS
- Multi-rendition HLS transcoding via FFmpeg
- Pre-roll ad insertion (single ad and ad pods)
- Per-session manifest generation
- VAST/VMAP parsing from Google sample tags
- On-demand ad creative conditioning (transcoding to match live renditions)
- Manifest splicing with `#EXT-X-DISCONTINUITY`
- Server-side firing of VAST tracking beacons (impression, quartiles, complete)
- Manual mid-roll trigger via HTTP endpoint (simulating SCTE-35)

**Out of scope (POC):**
- Real SCTE-35 cue extraction from RTMP
- DRM / encrypted content
- Companion ads, VPAID, OMID viewability
- Production-grade caching (Redis, S3) — in-memory + local disk only
- Multi-instance horizontal scaling
- Authentication / authorization

### 1.3 Success Criteria
1. Player loads a session URL and sees pre-roll ad → seamless transition → live content.
2. Mid-roll trigger via HTTP POST inserts ad pod within 1–2 segments.
3. Two concurrent sessions can have independent ad state.
4. GAM beacon URLs are fired server-side at correct quartile points (verified via stitcher logs).
5. Playback works on hls.js (Chrome) and Safari (native HLS).

---

## 2. System Architecture

### 2.1 Component Diagram

```
┌──────────────┐     RTMP      ┌──────────┐    RTMP pull   ┌──────────────┐
│  OBS Studio  │──────────────▶│  OSSRS   │◀──────────────│   FFmpeg     │
│  (streamer)  │  :1935        │  :1935   │                │  (transcode) │
└──────────────┘               └──────────┘                └──────┬───────┘
                                                                  │ writes
                                                                  ▼
                                                        ┌─────────────────┐
                                                        │  ~/livestream/  │
                                                        │  video.m3u8     │
                                                        │  video-240p.m3u8│
                                                        │  video-480p.m3u8│
                                                        │  video-720p.m3u8│
                                                        │  *.ts segments  │
                                                        └────────┬────────┘
                                                                 │ reads
                                                                 ▼
┌──────────────┐    HTTP       ┌────────────────────────────────────────┐
│   Player     │──────────────▶│      Stitcher Proxy (FastAPI)          │
│  (hls.js)    │  :8080        │                                        │
└──────────────┘               │  - Session manager                     │
                               │  - Manifest rewriter                   │
                               │  - VAST client ──────┐                 │
                               │  - Ad conditioner    │                 │
                               │  - Beacon firer      │                 │
                               └──────────┬───────────┼─────────────────┘
                                          │           │
                                          │           │ HTTPS
                                          ▼           ▼
                                  ┌──────────────┐  ┌─────────────────┐
                                  │ Conditioned  │  │ Google Ad       │
                                  │ Ad Cache     │  │ Manager         │
                                  │ (local disk) │  │ (sample tags)   │
                                  └──────────────┘  └─────────────────┘
```

### 2.2 Data Flow — Pre-Roll

1. Player requests `GET /session/new?content_id=demo`
2. Stitcher creates session, calls VAST tag, parses response, downloads ad MP4, conditions it for all renditions, caches segments. Returns `session_id` + master manifest URL.
3. Player requests `GET /session/{sid}/master.m3u8` → stitcher returns master with rewritten variant URLs pointing back at itself.
4. Player picks variant (e.g., 720p), requests `GET /session/{sid}/720p.m3u8`.
5. Stitcher returns manifest with ad segments first, `#EXT-X-DISCONTINUITY`, then live segments proxied from FFmpeg output.
6. Player fetches ad `.ts` segments via `GET /session/{sid}/seg/ad/{creative_id}/720p/{n}.ts`. Stitcher serves from disk cache and fires quartile beacons based on segment index.
7. Player fetches live `.ts` segments via `GET /session/{sid}/seg/live/{filename}` → stitcher proxies/redirects to FFmpeg's output directory.

### 2.3 Data Flow — Mid-Roll Trigger

1. Operator calls `POST /session/{sid}/trigger-ad-break` with `{duration: 30}`.
2. Stitcher fetches a fresh VAST response, conditions creative(s) if not cached.
3. On the next variant manifest request from the player, stitcher injects `#EXT-X-DISCONTINUITY` + ad segments + `#EXT-X-DISCONTINUITY` after the current live segment position.
4. Player continues playback through the discontinuity into the ad, then back to live.

---

## 3. Tech Stack

| Component | Choice | Rationale |
|---|---|---|
| Language | Python 3.11+ | Matches production codebase |
| Web framework | FastAPI | Async I/O for concurrent sessions, simple to write |
| ASGI server | Uvicorn | Standard FastAPI runtime |
| HTTP client | httpx (async) | VAST fetching + beacon firing |
| XML parsing | Standard `xml.etree.ElementTree` | No external dep needed for VAST |
| Transcoding | FFmpeg subprocess | Same tool as production |
| Session store | In-memory dict (POC) | Redis in production |
| Ad cache | Local disk + in-memory metadata | S3 + Redis in production |
| RTMP server | OSSRS (Docker) | Matches production |

---

## 4. Directory Layout

```
ssai-poc/
├── README.md
├── requirements.txt
├── docker-compose.yml          # OSSRS only
├── config.py                   # All constants/paths/URLs
├── main.py                     # FastAPI entrypoint
├── models.py                   # Pydantic models, dataclasses
├── session_manager.py          # Session creation, state, lookup
├── vast_client.py              # VAST/VMAP fetch + parse
├── ad_conditioner.py           # MP4 → HLS rendition transcoding
├── manifest_builder.py         # Master + variant manifest generation
├── beacon_firer.py             # Async beacon HTTP firing
├── live_proxy.py               # Live segment serving from FFmpeg output
├── routes/
│   ├── __init__.py
│   ├── session.py              # /session/new
│   ├── manifest.py             # /session/{sid}/master.m3u8, /{rendition}.m3u8
│   ├── segment.py              # /session/{sid}/seg/...
│   └── control.py              # /session/{sid}/trigger-ad-break
├── storage/
│   ├── live/                   # FFmpeg output mount (~/livestream)
│   └── ads/                    # Conditioned ad segments cache
│       └── {creative_id}/
│           ├── 240p.m3u8
│           ├── 240p_0.ts
│           ├── 480p.m3u8
│           └── ...
└── tests/
    ├── test_vast_parse.py
    ├── test_manifest_builder.py
    └── sample_vast_response.xml
```

---

## 5. Configuration (`config.py`)

```python
HOME_DIR = "~/ssai-poc"
LIVE_DIR = f"{HOME_DIR}/storage/live"           # FFmpeg writes here
ADS_DIR = f"{HOME_DIR}/storage/ads"             # Conditioned ads
PUBLIC_BASE_URL = "http://localhost:8080"        # For URL rewriting in manifests

RTMP_URL = "rtmp://localhost:1935/live/livestream"

# Renditions — must match FFmpeg output exactly
RENDITIONS = [
    {"name": "240p", "width": 426, "height": 240, "v_bitrate": 192000, "a_bitrate": 72000},
    {"name": "480p", "width": 854, "height": 480, "v_bitrate": 500000, "a_bitrate": 128000},
    {"name": "720p", "width": 1280, "height": 720, "v_bitrate": 1000000, "a_bitrate": 128000},
]

# HLS encoding params — must match for clean splices
FRAME_RATE = 24
GOP_SIZE = 48
SEGMENT_DURATION = 6
AUDIO_SAMPLE_RATE = 44100
AUDIO_CHANNELS = 2

# Google sample VAST tags
VAST_TAG_SINGLE_LINEAR = (
    "https://pubads.g.doubleclick.net/gampad/ads?"
    "iu=/21775744923/external/single_ad_samples&sz=640x480"
    "&cust_params=sample_ct%3Dlinear&ciu_szs=300x250%2C728x90"
    "&gdfp_req=1&output=vast&unviewed_position_start=1&env=vp&impl=s&correlator="
)
VAST_TAG_VMAP_POD = (
    "https://pubads.g.doubleclick.net/gampad/ads?"
    "iu=/21775744923/external/vmap_ad_samples&sz=640x480"
    "&cust_params=sample_ar%3Dpremidpostpod&ciu_szs=300x250%2C728x90"
    "&gdfp_req=1&ad_rule=1&output=vmap&unviewed_position_start=1&env=vp&impl=s"
    "&cmsid=496&vid=short_onecue&correlator="
)

# Active VAST tag for POC
ACTIVE_VAST_TAG = VAST_TAG_SINGLE_LINEAR
```

---

## 6. Data Models (`models.py`)

```python
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum

class AdState(str, Enum):
    NONE = "none"           # No ad break active
    PENDING = "pending"     # Ad break queued for next manifest
    ACTIVE = "active"       # Player currently inside ad break
    COMPLETED = "completed" # Ad break done

@dataclass
class TrackingEvent:
    event: str              # "impression", "start", "firstQuartile", "midpoint", "thirdQuartile", "complete"
    url: str
    fired: bool = False

@dataclass
class ConditionedAd:
    creative_id: str
    duration_sec: float
    # Per-rendition: list of (segment_filename, segment_duration)
    renditions: dict[str, list[tuple[str, float]]] = field(default_factory=dict)
    tracking: list[TrackingEvent] = field(default_factory=list)
    impression_urls: list[str] = field(default_factory=list)

@dataclass
class AdPod:
    pod_id: str
    ads: list[ConditionedAd]                # Played in order
    total_duration: float
    segments_served: dict[str, int] = field(default_factory=dict)  # rendition -> count

@dataclass
class Session:
    session_id: str
    created_at: float
    content_id: str
    ad_state: AdState = AdState.NONE
    pending_pod: Optional[AdPod] = None     # Queued for splice
    active_pod: Optional[AdPod] = None      # Currently being served
    pod_history: list[str] = field(default_factory=list)  # Played pod_ids
    # For mid-roll: live media sequence at which to splice
    splice_at_sequence: Optional[int] = None
```

---

## 7. Component Specifications

### 7.1 Session Manager (`session_manager.py`)

**Responsibilities:**
- Create sessions with UUID, store in-memory dict.
- Provide thread-safe accessors (use `asyncio.Lock` per session).
- TTL cleanup task (remove sessions inactive > 1 hour).

**API:**
```python
async def create_session(content_id: str) -> Session
async def get_session(session_id: str) -> Session  # raises 404
async def update_session(session_id: str, **fields) -> Session
async def cleanup_expired() -> None  # background task
```

### 7.2 VAST Client (`vast_client.py`)

**Responsibilities:**
- Build VAST request URL with fresh `correlator` (timestamp).
- HTTP GET via httpx, follow redirects (VAST wrappers).
- Parse XML for: `MediaFile` (pick highest bitrate progressive MP4), `Duration`, `Impression`, `Tracking` events, `ClickThrough`.
- Handle VAST wrappers (one level of redirect minimum, max 5).
- Handle VMAP: extract list of `AdBreak` elements with their VAST tags.

**Key parsing rules:**
- `<MediaFile>` filter: `delivery="progressive"`, `type="video/mp4"`, sort by `bitrate` descending.
- `<Duration>` format: `HH:MM:SS` or `HH:MM:SS.mmm` → convert to seconds.
- `<Impression>` and `<Tracking event="...">` URLs may contain `[CACHEBUSTING]` macro → replace with random int.

**API:**
```python
async def fetch_vast(tag_url: str) -> list[ParsedAd]
async def fetch_vmap(tag_url: str) -> list[AdBreakInfo]

@dataclass
class ParsedAd:
    creative_id: str
    media_url: str
    duration_sec: float
    impression_urls: list[str]
    tracking_events: list[TrackingEvent]
```

**VAST wrapper handling:** If response contains `<Wrapper><VASTAdTagURI>`, recursively fetch (limit recursion to 5 to prevent loops).

### 7.3 Ad Conditioner (`ad_conditioner.py`)

**Responsibilities:**
- Download MP4 from MediaFile URL to temp file.
- For each rendition in `RENDITIONS`, run FFmpeg to produce HLS segments matching live encoding params.
- Store in `{ADS_DIR}/{creative_id}/{rendition}_*.ts` and `{rendition}.m3u8`.
- Parse output `.m3u8` to extract segment list with durations.
- Cache: if `{ADS_DIR}/{creative_id}/.done` exists, skip transcoding.
- Return `ConditionedAd` object.

**FFmpeg command per rendition (CRITICAL — must match live):**
```bash
ffmpeg -y -i {input.mp4} \
  -vf scale={W}:{H} \
  -c:v libx264 -profile:v main -level 4.0 \
  -b:v {V_BITRATE} -maxrate {V_BITRATE} -bufsize {V_BITRATE*2} \
  -r 24 -g 48 -keyint_min 48 -sc_threshold 0 \
  -c:a aac -b:a {A_BITRATE} -ar 44100 -ac 2 \
  -f hls -hls_time 6 -hls_playlist_type vod \
  -hls_flags independent_segments \
  -hls_segment_filename "{ADS_DIR}/{creative_id}/{rendition}_%d.ts" \
  "{ADS_DIR}/{creative_id}/{rendition}.m3u8"
```

**Critical params (must match live FFmpeg):**
- `-r 24` framerate
- `-g 48 -keyint_min 48 -sc_threshold 0` GOP exactly 48 frames, no scene-cut keyframes
- `-ar 44100 -ac 2` audio sample rate + stereo
- `-profile:v main -level 4.0` H.264 profile (matches `libx264` defaults but lock it)

**API:**
```python
async def condition_ad(parsed_ad: ParsedAd) -> ConditionedAd
```

Run rendition transcodes in parallel via `asyncio.gather` + `asyncio.create_subprocess_exec`.

### 7.4 Manifest Builder (`manifest_builder.py`)

**Master manifest (`master.m3u8`):**
Read FFmpeg's `video.m3u8`, parse `#EXT-X-STREAM-INF` blocks, rewrite variant URIs to `{PUBLIC_BASE_URL}/session/{sid}/{rendition}.m3u8`.

**Variant manifest (`{rendition}.m3u8`):**
Two cases:

**Case A — No active/pending ad pod:**
Read FFmpeg's `video-{rendition}.m3u8`, rewrite each segment URI from `video-720p0.ts` to `{PUBLIC_BASE_URL}/session/{sid}/seg/live/video-720p0.ts`.

**Case B — Pending pre-roll or pending mid-roll splice:**
Construct manifest:
```
#EXTM3U
#EXT-X-VERSION:6
#EXT-X-TARGETDURATION:6
#EXT-X-MEDIA-SEQUENCE:0
#EXT-X-DISCONTINUITY-SEQUENCE:0
#EXT-X-PLAYLIST-TYPE:EVENT

# (For mid-roll: live segments up to splice point first, with original URIs)

#EXT-X-DISCONTINUITY
#EXT-X-CUE-OUT:DURATION={pod_duration}

# For each ad in pod, for each segment:
#EXTINF:{seg_duration},
{PUBLIC_BASE_URL}/session/{sid}/seg/ad/{pod_id}/{creative_id}/{rendition}/{n}.ts

#EXT-X-CUE-IN
#EXT-X-DISCONTINUITY

# Live segments resume here (rewritten URIs)
#EXTINF:6.0,
{PUBLIC_BASE_URL}/session/{sid}/seg/live/video-720p123.ts
...
```

**Important:** Update session state — move `pending_pod` → `active_pod` once the ad has been written into a manifest the player has fetched.

**API:**
```python
def build_master(session: Session, ffmpeg_master_path: str) -> str
def build_variant(session: Session, rendition: str, ffmpeg_variant_path: str) -> str
```

### 7.5 Segment Routes (`routes/segment.py`)

**`GET /session/{sid}/seg/live/{filename}`:**
- Validate filename (no path traversal: regex `^video-[a-z0-9]+\d+\.ts$`).
- Stream file from `{LIVE_DIR}/{filename}` with `Content-Type: video/mp2t`.
- Return 404 if not found (segment may not exist yet for live edge).

**`GET /session/{sid}/seg/ad/{pod_id}/{creative_id}/{rendition}/{n}.ts`:**
- Validate session, pod_id matches active or completed pod.
- Stream `{ADS_DIR}/{creative_id}/{rendition}_{n}.ts`.
- **Beacon trigger:** Increment `session.active_pod.segments_served[rendition]`. Calculate progress = segments_served / total_segments. Fire beacons:
  - First segment of first ad → fire `impression` + `start` for that ad
  - Crosses 25% → `firstQuartile`
  - Crosses 50% → `midpoint`
  - Crosses 75% → `thirdQuartile`
  - Last segment → `complete`, mark ad done; if last ad in pod, transition state to `COMPLETED`
- Use `beacon_firer.fire_async()` — non-blocking.

### 7.6 Beacon Firer (`beacon_firer.py`)

**Responsibilities:**
- Async fire-and-forget HTTP GET to tracking URLs.
- Replace VAST macros: `[CACHEBUSTING]` → random 8-digit int, `[TIMESTAMP]` → ISO timestamp URL-encoded.
- Log success/failure (don't retry in POC).
- Mark `TrackingEvent.fired = True` to prevent duplicates.

**API:**
```python
async def fire(event: TrackingEvent) -> None
async def fire_batch(events: list[TrackingEvent]) -> None
```

### 7.7 Control Routes (`routes/control.py`)

**`POST /session/{sid}/trigger-ad-break`:**
- Body: `{"tag_url": "<optional override>", "duration_hint": 30}`
- Fetch VAST, condition ads, build `AdPod`, set `session.pending_pod`, set `session.ad_state = PENDING`.
- Set `session.splice_at_sequence` = current live media sequence + 2 (gives player time to receive the updated manifest).
- Return `{"pod_id": "...", "ad_count": N, "duration": X}`.

**`GET /session/{sid}/state`:** (debug)
Returns full session JSON for inspection.

---

## 8. Endpoint Reference

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/session/new` | Create session, optionally with pre-roll. Body: `{"content_id": "demo", "preroll": true}`. Returns `{"session_id", "master_url"}`. |
| `GET` | `/session/{sid}/master.m3u8` | Master playlist with rewritten variants |
| `GET` | `/session/{sid}/{rendition}.m3u8` | Variant playlist with ad splices if applicable |
| `GET` | `/session/{sid}/seg/live/{filename}` | Live segment proxy |
| `GET` | `/session/{sid}/seg/ad/{pod_id}/{creative_id}/{rendition}/{n}.ts` | Conditioned ad segment |
| `POST` | `/session/{sid}/trigger-ad-break` | Manually inject ad break (mid-roll) |
| `GET` | `/session/{sid}/state` | Debug — return session state |
| `GET` | `/health` | Liveness check |

---

## 9. Local Setup

### 9.1 Prerequisites
- Python 3.11+
- FFmpeg with libx264 (`ffmpeg -version` should show `--enable-libx264`)
- Docker (for OSSRS)
- OBS Studio or any RTMP source

### 9.2 OSSRS via Docker (`docker-compose.yml`)
```yaml
services:
  ossrs:
    image: ossrs/srs:5
    ports:
      - "1935:1935"   # RTMP
      - "1985:1985"   # HTTP API
      - "8085:8080"   # HTTP server
    command: ./objs/srs -c conf/srs.conf
```

### 9.3 Run Steps
```bash
# 1. Start OSSRS
docker-compose up -d

# 2. Stream from OBS to rtmp://localhost:1935/live/livestream

# 3. Start FFmpeg transcode (in ssai-poc/storage/live/)
mkdir -p storage/live
cd storage/live
ffmpeg -y -i rtmp://localhost:1935/live/livestream \
  -map 0:v:0 -map 0:a:0 -s:v:0 426x240 -c:v:0 libx264 -b:v:0 192000 -b:a:0 72000 \
  -map 0:v:0 -map 0:a:0 -s:v:1 854x480 -c:v:1 libx264 -b:v:1 500000 -b:a:1 128000 \
  -map 0:v:0 -map 0:a:0 -s:v:2 1280x720 -c:v:2 libx264 -b:v:2 1000000 -b:a:2 128000 \
  -c:a aac -ar 44100 -ac 2 \
  -preset ultrafast -hls_list_size 0 -threads 0 -f hls -tune zerolatency \
  -hls_playlist_type event -hls_time 6 -g 48 -keyint_min 48 -sc_threshold 0 \
  -hls_flags independent_segments+program_date_time \
  -r 24 \
  -master_pl_name "video.m3u8" \
  -var_stream_map "v:0,a:0,name:240p v:1,a:1,name:480p v:2,a:2,name:720p" \
  video-%v.m3u8

# 4. Start stitcher
cd ssai-poc
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8080 --reload

# 5. Create session
curl -X POST http://localhost:8080/session/new \
  -H "Content-Type: application/json" \
  -d '{"content_id": "demo", "preroll": true}'

# Returns: {"session_id": "abc-123", "master_url": "http://localhost:8080/session/abc-123/master.m3u8"}

# 6. Open test player at http://localhost:8080/test-player.html?sid=abc-123
#    OR: paste master_url into https://hlsjs.video-dev.org/demo/

# 7. Trigger mid-roll
curl -X POST http://localhost:8080/session/abc-123/trigger-ad-break \
  -H "Content-Type: application/json" \
  -d '{"duration_hint": 30}'
```

### 9.4 Test Player (`static/test-player.html`)
Bundle a minimal hls.js page that reads `sid` from query params, loads `/session/{sid}/master.m3u8`, and shows playback events in a debug panel.

---

## 10. `requirements.txt`

```
fastapi==0.115.0
uvicorn[standard]==0.32.0
httpx==0.27.2
pydantic==2.9.0
python-multipart==0.0.12
```

---

## 11. Validation Checklist

| Test | How to verify |
|---|---|
| Pre-roll ad plays | Create session with `preroll: true`, observe ad in player before live content |
| Discontinuity transition clean | No stall, no audio glitch, no decoder reset error in browser console |
| Beacons fire at correct quartiles | Check stitcher logs for "fired: firstQuartile" at 25% of ad duration |
| Two sessions independent | Create 2 sessions, trigger ad on only one, verify other unaffected |
| Mid-roll trigger works | Start playback, wait 30s, POST trigger, verify ad appears within 12s |
| Cache hit on repeat ad | Second session with same creative_id loads instantly (no FFmpeg run) |
| Cross-rendition consistency | Force player rendition switch during ad — playback continues |
| Safari native HLS | Open master URL directly in Safari, verify playback |
| hls.js compatibility | Open in Chrome via hls.js demo page, check error log |

---

## 12. Known Limitations & Production Gaps

1. **No SCTE-35 extraction** — production needs OSSRS or upstream encoder to inject SCTE-35 cues, which the stitcher would parse from the live manifest's `#EXT-X-DATERANGE` or `#EXT-OATCLS-SCTE35` tags.
2. **In-memory session state** — process restart loses all sessions; production needs Redis.
3. **Local disk ad cache** — production needs S3 + CDN for conditioned ad segments.
4. **No ABR-aware ad selection** — VAST tag is static; production should send player capabilities (resolution, bitrate) as VAST params.
5. **No retry/backoff for VAST** — production should handle GAM timeouts gracefully (skip ad, continue live).
6. **Beacon firing is best-effort** — no retry queue; production needs durable beacon delivery.
7. **No DVR window handling** — pure live only.
8. **No client-side ad reporting** — relies entirely on server-side beacons. For viewability metrics, OMID would be needed.

---

## 13. Implementation Order (Suggested)

1. **Day 1:** Project skeleton, config, models, session manager, `/session/new` + `/health`. Verify Postman.
2. **Day 2:** VAST client — fetch + parse the Google sample tag, log MediaFile URL and tracking URLs. Unit test with saved XML response.
3. **Day 3:** Ad conditioner — transcode one MP4 to one rendition, verify segments play in VLC standalone.
4. **Day 4:** Manifest builder + segment routes — pre-roll only, hardcoded ad. Verify in hls.js.
5. **Day 5:** Wire VAST → conditioner → manifest end-to-end. First real Google ad plays.
6. **Day 6:** Beacon firer + quartile logic. Verify with logging.
7. **Day 7:** Mid-roll trigger endpoint, splice logic.
8. **Day 8:** Multi-session testing, test player HTML, polish, documentation.

---

## 14. References

- HLS spec (RFC 8216): https://datatracker.ietf.org/doc/html/rfc8216
- VAST 4.2 spec: https://iabtechlab.com/standards/vast/
- VMAP 1.0 spec: https://iabtechlab.com/standards/video-multiple-ad-playlist-vmap/
- Google IMA sample tags: https://developers.google.com/interactive-media-ads/docs/sdks/html5/client-side/tags
- HLS ad insertion best practices (Apple): https://developer.apple.com/documentation/http-live-streaming/incorporating-ads-into-a-playlist
- hls.js debug demo: https://hlsjs.video-dev.org/demo/

---