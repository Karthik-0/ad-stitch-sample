## 1. Conditioner Module Setup

- [x] 1.1 Create `ssai-poc/ad_conditioner.py` with public `condition_ad(parsed_ad)` API and internal helper structure.
- [x] 1.2 Add typed helper models/functions needed for download, transcode orchestration, and playlist parsing.
- [x] 1.3 Ensure output paths are created under `ADS_DIR/{creative_id}` with deterministic rendition filename patterns.

## 2. Creative Download and Cache Flow

- [x] 2.1 Implement creative MP4 download to temporary local file with HTTP error handling.
- [x] 2.2 Implement cache-hit detection via `{ADS_DIR}/{creative_id}/.done` and expected rendition playlist presence.
- [x] 2.3 Implement cache-return path that parses existing playlists and bypasses FFmpeg execution.

## 3. FFmpeg Transcoding Pipeline

- [x] 3.1 Implement FFmpeg command builder that locks required live-compatibility flags (`-r`, `-g`, `-keyint_min`, `-sc_threshold`, `-ar`, `-ac`, profile/level).
- [x] 3.2 Implement rendition-level transcode execution with `asyncio.create_subprocess_exec`.
- [x] 3.3 Execute per-rendition transcodes concurrently using `asyncio.gather` and propagate failures clearly.
- [x] 3.4 Mark cache completion only after all renditions transcode and parse successfully.

## 4. Playlist Parsing and Output Assembly

- [x] 4.1 Parse generated rendition playlists for ordered `#EXTINF` duration and segment filename tuples.
- [x] 4.2 Build and return `ConditionedAd` output with creative id, source duration, rendition map, tracking events, and impression URLs.
- [x] 4.3 Ensure malformed or missing playlist artifacts raise explicit conditioning errors.

## 5. Test Coverage

- [x] 5.1 Add unit tests for FFmpeg command construction and required codec/GOP/audio flags.
- [x] 5.2 Add unit tests for playlist parsing behavior with representative HLS fixture content.
- [x] 5.3 Add tests validating cache-hit bypass (no FFmpeg invocation) and cache-miss transcode path.
- [x] 5.4 Add tests for subprocess failure handling and partial-output safety behavior.

## 6. Documentation and Validation

- [x] 6.1 Document ad conditioner usage and expected local output layout in `ssai-poc/README.md`.
- [x] 6.2 Run test suite and verify Day 3 conditioner requirements pass deterministically.
- [x] 6.3 Document known Day 3 limitations and deferred concerns (transcode retries, distributed cache, production hardening).
