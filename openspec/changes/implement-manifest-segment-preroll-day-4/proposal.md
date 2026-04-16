## Why

Even with VAST parsing and ad conditioning in place, playback still cannot deliver stitched ad experiences until manifests and segment routes are orchestrated per session. Implementing Day 4 provides the first end-to-end playback splice path by injecting a hardcoded pre-roll pod and serving both live and ad segments through the stitcher API.

## What Changes

- Add manifest builder logic for session-specific master and variant playlist generation.
- Rewrite master and variant URIs to stitcher-owned endpoints.
- Support Day 4 scope pre-roll splice flow with discontinuity markers and hardcoded ad pod playback.
- Add segment routes for live TS passthrough and conditioned ad TS serving.
- Enforce filename/path validation on live segment access to prevent traversal abuse.
- Update session state transitions when pre-roll is first materialized in a fetched variant manifest.
- Add tests for manifest rewrite behavior and segment route validation/response semantics.

## Capabilities

### New Capabilities
- `session-manifest-splice-preroll`: Builds session-specific HLS manifests and injects pre-roll ad segments into variant playlists.
- `session-segment-serving`: Serves live and conditioned ad media segments through controlled session routes with input validation.

### Modified Capabilities
- None.

## Impact

- Adds `manifest_builder.py` and segment route module implementation in `ssai-poc`.
- Expands API surface with playback-critical HLS endpoints.
- Connects conditioned ad artifacts to session playback responses.
- Establishes state progression from `pending_pod` to `active_pod` in manifest serving flow.
