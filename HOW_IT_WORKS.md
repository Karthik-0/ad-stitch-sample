# How This Project Works (SSAI POC)

This document explains the project in practical terms for developers, QA, and teammates who need to run or demo it.

## 1. What This Project Is

This repository is a **Server-Side Ad Insertion (SSAI) proof of concept** for live HLS streams.

At a high level:
1. A live stream is generated as HLS playlists/segments.
2. A FastAPI app rewrites those manifests per viewer session.
3. Ads are stitched into the stream by inserting ad segments and discontinuities.
4. The player sees one continuous HLS stream URL.

## 2. End-to-End Pipeline

```
OBS (or any RTMP source)
  -> OSSRS
    -> FFmpeg (multi-rendition HLS output)
      -> ffmpeg-outputs/ (video.m3u8, video-240p.m3u8, .ts files)

FastAPI SSAI Stitcher
  -> reads live HLS from LIVE_DIR
  -> creates session-scoped manifests
  -> fetches/conditions ads from VAST tags
  -> serves ad + live segments from one session URL

Browser Player
  -> opens /session/{sid}/master.m3u8
  -> receives stitched pre-roll/mid-roll
```

## 3. Core Concepts

### 3.1 Session
Each viewer gets a unique `session_id`.
The stitcher keeps state per session (ad state, pending pod, splice point, history).

Why it matters:
- Two viewers can receive different ad timing/state.
- Mid-roll triggers apply to one session, not globally.

### 3.2 Live Manifest Rewriting
The stitcher does not modify FFmpeg files on disk.
It reads live playlists, then returns rewritten playlists under `/session/{sid}/...`.

### 3.3 Ad Pod Lifecycle
A session can move through:
- `none` -> no ad scheduled
- `pending` -> break scheduled, waiting for splice sequence
- `active` -> ad currently being stitched/served
- `completed` -> break finished

### 3.4 Splice Scheduling
Mid-roll insertion is playback-relative:
- Trigger request includes `duration` (seconds from now).
- Stitcher maps that to segment sequence using segment duration.
- Splice occurs at/after that sequence boundary.

### 3.5 Live Behavior vs VOD Behavior
This is **live replacement**, not rewindable VOD continuity by default.
During ad playback, live source continues moving forward.
So after a 10s ad, playback resumes at a newer live point (some live content is skipped).

## 4. Ad Sources and Tag Selection

Ad creatives are obtained from VAST/VMAP tags.
Current UI allows:
1. Default server tag
2. Google sample presets
3. Custom ad tag URL per trigger

If ads look visually identical repeatedly, that typically means:
- The chosen test tag returns the same creative frequently, or
- A cached/previous conditioned pod is reused in that path.

## 5. Main Components (Code Map)

### API app and routing
- `ssai-poc/main.py`: app creation, router registration, lifecycle cleanup task
- `ssai-poc/routes/session.py`: creates sessions
- `ssai-poc/routes/segment.py`: serves master/variant manifests and segment files
- `ssai-poc/routes/control.py`: mid-roll trigger endpoint (`duration`, optional `ad_tag`)

### Stitching internals
- `ssai-poc/manifest_builder.py`: rewrites master/variant playlists and inserts ad boundaries
- `ssai-poc/session_manager.py`: in-memory session store + TTL cleanup
- `ssai-poc/models.py`: session/ad data models

### Ad pipeline
- `ssai-poc/vast_client.py`: fetches/parses VAST/VMAP
- `ssai-poc/ad_conditioner.py`: transcodes ad media into rendition-aligned HLS segments
- `ssai-poc/beacon_firer.py`: fires tracking beacons (impression/quartiles)
- `ssai-poc/scte35_parser.py`: parses cue markers from playlist tags

### UI
- `ssai-poc/index.html`: control room UI (new session, ad trigger, ad tag selection, player, rewind slider)

## 6. Key Endpoints

- `GET /health` -> service status
- `POST /session/new` -> returns `session_id` + master URL
- `GET /session/{sid}/master.m3u8` -> session master playlist
- `GET /session/{sid}/{rendition}.m3u8` -> session variant playlist
- `GET /session/{sid}/seg/live/{filename}` -> live segment passthrough
- `GET /session/{sid}/seg/ad/{rendition}/{index}` -> ad segment serving
- `POST /session/{sid}/trigger-ad-break?duration=N[&ad_tag=...]` -> schedule mid-roll

## 7. Typical Demo Flow

1. Start FFmpeg output (ensure `video.m3u8` + variants are present in `LIVE_DIR`).
2. Start FastAPI stitcher with `LIVE_DIR` pointing to those outputs.
3. Open UI (`/`).
4. Click **New Session**.
5. Player loads session master manifest and begins playback.
6. Choose ad preset/custom URL + delay.
7. Click **Insert Ad Break**.
8. Observe ad splice and resume to live edge.

## 8. Deployment Summary

This project is intended to run behind Supervisor (and optionally Nginx).
Primary deployment guide:
- `DEPLOYMENT.md`

Important deployment gotchas:
1. `LIVE_DIR` must point to real HLS output directory containing `video.m3u8`.
2. Service user must have execute/read permission for app path and live directory.
3. If using reverse proxy, pass forwarded host/scheme headers.
4. In restricted environments, external Video.js CDN may be blocked (native fallback is present).

## 9. Limitations (POC)

- In-memory session state (not distributed)
- No auth/authorization
- No DRM
- No real broadcast SCTE-35 ingestion from transport stream metadata
- Local-disk caching only
- Not hardened yet for high concurrency/HA production

## 10. Where to Read Next

- `ssai-poc/README.md` -> operational commands and testing steps
- `TechSpecs.md` -> detailed architecture/spec-level behavior
- `DEPLOYMENT.md` -> server setup with Supervisor + Nginx
