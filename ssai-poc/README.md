# SSAI POC Operational Guide

Version: 1.0.0
Last Updated: 2026-04-16

This guide explains how to run, test, and troubleshoot the Server-Side Ad Stitching (SSAI) POC locally.

## Setup Checklist

- [ ] Install Python 3.11+, FFmpeg (with libx264), Docker, and optional OBS Studio
- [ ] Start OSSRS with Docker Compose
- [ ] Push an RTMP stream from OBS to OSSRS
- [ ] Start FFmpeg live transcoding to HLS
- [ ] Start the FastAPI stitcher service
- [ ] Verify health endpoint and playlists
- [ ] Create a session and play the master manifest
- [ ] Trigger a mid-roll break and verify ad insertion

## Quick Start

Run these commands from this directory.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
docker compose up -d

# Start stitcher
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

In another terminal:

```bash
curl http://localhost:8000/health
```

Expected response:

```json
{"status":"ok"}
```

## Prerequisites

- Python 3.11+
- FFmpeg compiled with libx264
- Docker + Docker Compose
- OBS Studio (optional, only needed to generate RTMP live input)

### Install on macOS (Homebrew)

```bash
brew install python ffmpeg docker
```

Verify FFmpeg has libx264:

```bash
ffmpeg -version | grep libx264
```

### Install on Linux (APT)

```bash
sudo apt-get update
sudo apt-get install -y python3 python3-venv python3-pip ffmpeg docker.io docker-compose-plugin
```

Verify FFmpeg has libx264:

```bash
ffmpeg -version | grep libx264
```

## Local Deployment

### 1) Start OSSRS

`docker-compose.yml` is included in this folder.

```bash
docker compose up -d
```

Verify OSSRS is ready:

```bash
curl http://localhost:1985/api/v1/servers
```

Expected: JSON payload describing running SRS server state.

### 2) Send RTMP Input (OBS)

In OBS Studio:

- Server: `rtmp://localhost:1935/live`
- Stream Key: `livestream`

Full ingest URL:

`rtmp://localhost:1935/live/livestream`

### 3) Start FFmpeg Multi-Rendition HLS Output

Create live output directory:

```bash
mkdir -p storage/live
cd storage/live
```

Run FFmpeg:

```bash
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
```

Important:

- The stitcher reads live files from `ssai-poc/storage/live` by default.
- If you write FFmpeg output somewhere else (for example `ffmpeg-outputs/`), either move files into `ssai-poc/storage/live` or start the API with `LIVE_DIR` set:

```bash
LIVE_DIR=/absolute/path/to/your/ffmpeg-outputs uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Parameter highlights:

- Per-rendition bitrates: 240p=192k, 480p=500k, 720p=1000k
- GOP: `-g 48 -keyint_min 48 -sc_threshold 0`
- Frame rate: `-r 24`
- Audio: `-ar 44100 -ac 2`
- Codec: `libx264`

Verify output:

```bash
ls -1
```

Expect files similar to:

- `video.m3u8`
- `video-240p.m3u8`, `video-480p.m3u8`, `video-720p.m3u8`
- multiple `.ts` segments per rendition

Stop FFmpeg with `Ctrl+C`.

### 4) Start Stitcher

From the `ssai-poc` folder:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Verify stitcher health:

```bash
curl http://localhost:8000/health
```

If port 8000 is busy:

```bash
lsof -i :8000
uvicorn main:app --host 0.0.0.0 --port 8081 --reload
```

## API Endpoints

Core endpoints implemented in this POC:

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Liveness check |
| POST | `/session/new` | Create SSAI session |
| GET | `/session/{sid}/master.m3u8` | Master playlist with rewritten variants |
| GET | `/session/{sid}/{rendition}.m3u8` | Variant playlist with live or ad splice |
| GET | `/session/{sid}/seg/live/{filename}` | Live segment serving |
| GET | `/session/{sid}/seg/ad/{rendition}/{index}` | Ad segment serving |
| POST | `/session/{sid}/trigger-ad-break?duration=N` | Queue a mid-roll ad break |

### Create Session

```bash
BASE_URL=${BASE_URL:-http://localhost:8000}

curl -X POST "$BASE_URL/session/new" \
  -H "Content-Type: application/json" \
  -d '{"content_id":"demo","preroll":true}'
```

Response:

```json
{
  "session_id": "abc-123",
  "master_url": "http://localhost:8000/session/abc-123/master.m3u8"
}
```

### Fetch Master Playlist

```bash
SID="abc-123"  # Use the real session_id returned above
curl "$BASE_URL/session/$SID/master.m3u8"
```

Example output:

```m3u8
#EXTM3U
#EXT-X-STREAM-INF:...
/session/abc-123/240p.m3u8
```

### Fetch Variant Playlist

```bash
curl "$BASE_URL/session/$SID/720p.m3u8"
```

If an ad break is active or pending, playlist includes ad splice markers such as:

- `#EXT-X-DISCONTINUITY`
- `#EXT-X-CUE-OUT`
- `#EXT-X-CUE-IN`

### Fetch Live Segment

```bash
curl -sS -o /tmp/live.ts "$BASE_URL/session/$SID/seg/live/video-720p0.ts" && ls -lh /tmp/live.ts
```

Notes:

- Filename is validated to prevent path traversal.
- Missing segment returns `404`.
- Content type is `video/mp2t`.

### Fetch Ad Segment

```bash
curl -sS -o /tmp/ad.ts "$BASE_URL/session/$SID/seg/ad/720p/0" && ls -lh /tmp/ad.ts
```

Notes:

- Ad segments are served from conditioned ad cache.
- Serving ad segments contributes to quartile/impression tracking in server logs.

### Trigger Mid-Roll

```bash
curl -X POST "$BASE_URL/session/$SID/trigger-ad-break?duration=30"
```

Response example:

```json
{
  "status": "accepted",
  "message": "Mid-roll trigger scheduled"
}
```

Notes:

- The trigger schedules the ad break approximately `duration` seconds after the player's observed playback position.
- In practice, insertion is segment-aligned, so actual timing is rounded up by one segment.

## Testing

### Pre-Roll Validation

1. Create session with `preroll=true`.
2. Open returned `master_url` in a player.
3. Expected behavior: ad plays before transition to live stream.

### Mid-Roll Validation

1. Start playback from `master_url`.
2. Trigger break while playback is already running:

```bash
curl -X POST "http://localhost:8000/session/<sid>/trigger-ad-break?duration=30"
```

3. Expected behavior: after roughly `duration` seconds of playback, playlist refreshes include `#EXT-X-CUE-OUT`, ad segment URIs under `/seg/ad/`, then `#EXT-X-CUE-IN`, and playback returns to live.

### SCTE-35 Auto-Trigger Testing

SCTE-35 allows automatic ad break injection via manifest splice markers. The stitcher detects `#EXT-X-CUE-OUT` tags and automatically triggers ad breaks without manual HTTP requests.

**Testing SCTE-35 auto-trigger:**

1. Modify your live FFmpeg output to include SCTE-35 markers (example below).
2. Create a session and start playback.
3. Observe stitcher logs: when a new `#EXT-X-CUE-OUT` is detected, the stitcher automatically triggers a mid-roll ad break.

**Example FFmpeg command with simulated SCTE-35 cues:**

```bash
ffmpeg -y -i rtmp://... \
  ... (standard encoding options) \
  -hls_flags independent_segments+program_date_time+scte35_preroll_allowed \
  -hls_playlist_type event \
  -hls_time 6 \
  -master_pl_name "video.m3u8" \
  -var_stream_map "..." \
  video-%v.m3u8
```

Alternatively, manually inject cues into the live manifest for testing:

```bash
# Edit storage/live/video-720p.m3u8 and add:
#EXT-X-CUE-OUT:30
#EXTINF:6.0,
segment-xyz.ts
```

**Expected stitcher log output:**

```
✓ Detected new SCTE-35 CUE-OUT: cue-seq723 duration=30.0s sequence=723
✓ SCTE-35 auto-trigger: cue cue-seq723 duration=30.0s at sequence 723
```

**Limitations:**

- SCTE-35 cue IDs are auto-generated based on manifest position; they are not read from binary payloads.
- Only `#EXT-X-CUE-OUT` duration is used; full SCTE-35 binary splice commands are parsed but not decoded.
- Each detected cue triggers exactly one ad break; re-entry is prevented via `processed_scte35_cue_ids` tracking.

**For production SCTE-35:**

See [SCTE35_EXAMPLES.md](SCTE35_EXAMPLES.md) for detailed manifest examples and refer to SCTE-35 RFC and SMPTE standards for binary payload encoding.

### Test Player

You can test with either:

- hls.js demo: https://hlsjs.video-dev.org/demo/
- Safari native playback: paste `master_url` directly in Safari.

### Beacon Verification

Watch stitcher logs while ad segments are requested.

Example pattern checks:

```bash
grep -Ei "impression|start|firstquartile|midpoint|thirdquartile|complete|beacon" <stitcher-log-file>
```

Look for quartile progression:

- 25% -> `firstQuartile`
- 50% -> `midpoint`
- 75% -> `thirdQuartile`
- 100% -> `complete`

### Multi-Session Independence Test

1. Create two sessions.
2. Trigger ad break only on session A.
3. Keep both sessions playing.
4. Expected: session A receives ad splice; session B remains unaffected.

Note: A dedicated state inspection endpoint (`GET /session/{sid}/state`) is not currently available in this codebase.

### Browser Compatibility

- Safari: open the master playlist URL directly.
- Chrome: use hls.js demo and inspect browser console.

Expected for both:

- Master and variants load.
- Discontinuities transition without fatal playback failure.

## Troubleshooting

### `ffmpeg: command not found`

```bash
which ffmpeg
ffmpeg -version | grep libx264
```

Install FFmpeg via Homebrew or APT if missing.

### `Address already in use`

```bash
lsof -i :8000
```

Stop the conflicting process or change stitcher port.

### VAST fetch timeout

- Check internet access.
- Verify VAST URL is reachable with curl.
- Retry with a smaller duration and inspect stitcher logs.

### No `.ts` output from FFmpeg

- Verify OBS is actually pushing RTMP.
- Check OSSRS API:

```bash
curl http://localhost:1985/api/v1/servers
```

- Confirm output path is `ssai-poc/storage/live`.
- Review FFmpeg terminal output for decode/encode errors.

### Player black screen or stuck

- Check stitcher logs for 404 on playlist or segments.
- Fetch master and variant manually with curl.
- Confirm CORS/network restrictions when using browser-based player tools.

For broader constraints and production gaps, see TechSpecs sections "Known Limitations" and "References".

## Architecture Overview

```text
OBS (RTMP source)
  -> OSSRS (RTMP ingress)
    -> FFmpeg (live transcode)
      -> storage/live/*.m3u8 + *.ts

Player
  -> FastAPI Stitcher (/session/...)
    -> session_manager (per-session state)
    -> vast_client (VAST fetch/parse)
    -> ad_conditioner (ad transcoding/cache)
    -> manifest_builder (playlist rewrite/splice)
    -> beacon_firer (tracking beacons)
```

## Component Summary

| Component | Responsibility |
|---|---|
| SessionManager | Create and track per-session ad state |
| VastClient | Fetch and parse VAST/VMAP and tracking metadata |
| AdConditioner | Convert ad media into HLS renditions matching live settings |
| ManifestBuilder | Rewrite playlists and inject ad breaks |
| Segment Routes | Serve live/ad segments with validation |
| BeaconFirer | Fire impression and quartile tracking beacons |

## File Layout

```text
ssai-poc/
  main.py
  config.py
  models.py
  session_manager.py
  vast_client.py
  ad_conditioner.py
  manifest_builder.py
  beacon_firer.py
  routes/
    health.py
    session.py
    segment.py
    control.py
  storage/
    live/
    ads/
```

## Data Flow (Pre-Roll)

1. Client calls `POST /session/new`.
2. Stitcher creates session and prepares/queues ad pod.
3. Client requests `/session/{sid}/master.m3u8`.
4. Client requests `/session/{sid}/{rendition}.m3u8`.
5. Stitcher returns ad segments followed by discontinuity back to live.
6. Client fetches ad and live segments through stitcher routes.

## Configuration Reference

Key constants in `config.py`:

| Constant | Purpose |
|---|---|
| `RENDITIONS` | ABR rendition dimensions and bitrates |
| `SEGMENT_DURATION` | HLS segment duration target |
| `FRAME_RATE` | Framerate used for conditioning/transcode alignment |
| `VAST_TAG_SINGLE_LINEAR` | Default Google sample VAST tag |
| `ACTIVE_VAST_TAG` | Active tag source for control flow |

Override strategy:

- Change constants directly in `config.py` for local experimentation.
- For ad break duration, use query parameter on trigger endpoint.

## Repository Notes

- Main app source: this folder
- Sample HLS outputs: `../ffmpeg-outputs/`
- OpenSpec artifacts: `../openspec/changes/`

## Further Reading

- Workspace tech spec: `../TechSpecs.md`
- SCTE-35 integration guide: `SCTE35_EXAMPLES.md`
- Data models: `models.py`
- Session management: `session_manager.py`
- VAST parsing: `vast_client.py`
- Manifest logic: `manifest_builder.py`
- SCTE-35 parser: `scte35_parser.py`
- Beacon logic: `beacon_firer.py`

TechSpecs deep links:

- Architecture: Section 2
- Data Models: Section 6
- Component Specifications: Section 7

External references:

- HLS RFC 8216: https://datatracker.ietf.org/doc/html/rfc8216
- SCTE-35 Specification: https://www.smpte.org/standards/st-2034-1
- VAST spec: https://iabtechlab.com/standards/vast/
- Google IMA sample tags: https://developers.google.com/interactive-media-ads/docs/sdks/html5/client-side/tags
- hls.js demo: https://hlsjs.video-dev.org/demo/
- Apple HLS ad insertion guidance: https://developer.apple.com/documentation/http-live-streaming/incorporating-ads-into-a-playlist

## Appendix: docker-compose.yml (OSSRS)

```yaml
services:
  ossrs:
    image: ossrs/srs:5
    ports:
      - "1935:1935"
      - "1985:1985"
      - "8085:8080"
    command: ./objs/srs -c conf/srs.conf
```
