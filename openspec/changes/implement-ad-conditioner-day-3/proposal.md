## Why

Day 2 can fetch and parse VAST metadata, but the system still cannot produce stitch-ready ad segments that match live stream encoding constraints. Implementing the Day 3 ad conditioner now enables conversion of ad media into compatible HLS outputs and unlocks manifest-level ad insertion work.

## What Changes

- Add a new ad conditioning module that downloads ad MP4 creatives to temporary local storage.
- Transcode creatives to HLS outputs per configured rendition using FFmpeg parameters aligned to live encoding settings.
- Parse generated rendition playlists to capture segment filenames and durations.
- Add local cache behavior that skips transcoding for already-conditioned creatives.
- Return a normalized `ConditionedAd` object that downstream manifest and segment components can consume.
- Add focused tests for command construction, cache behavior, and playlist parsing.

## Capabilities

### New Capabilities
- `ad-creative-conditioning`: Converts parsed ad creatives into local HLS rendition artifacts with live-compatible encoding parameters and cache-aware reuse.

### Modified Capabilities
- None.

## Impact

- Adds FFmpeg subprocess orchestration and local artifact generation in `ssai-poc`.
- Introduces conditioned ad cache layout under storage/ads for subsequent serving routes.
- Expands integration path from VAST parsed metadata to stitch-ready ad segment catalogs.
- Adds tests and fixtures for conditioning and playlist interpretation behavior.
