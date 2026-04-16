## Context

The current SSAI POC can bootstrap sessions and parse VAST/VMAP metadata, but cannot yet transform selected ad creatives into HLS segments that are compatible with the live stream profile. Day 3 introduces an ad conditioner module responsible for downloading creative media, transcoding per rendition with strict FFmpeg parameters, and returning structured metadata for manifest splicing.

This slice has strict compatibility requirements because ad/live transitions depend on matching codec and GOP characteristics.

## Goals / Non-Goals

**Goals:**
- Implement a conditioning pipeline that ingests parsed ad media URLs and emits per-rendition HLS playlists and `.ts` segments.
- Keep encoding settings aligned with live profile constraints (framerate, GOP, audio settings, profile/level).
- Add cache-aware behavior to reuse existing conditioned creatives.
- Parse generated playlists to provide deterministic segment order and durations.
- Return `ConditionedAd` values compatible with existing model contracts.

**Non-Goals:**
- Manifest splice logic.
- Segment serving routes.
- Beacon trigger logic.
- Multi-node/distributed cache management.
- Full production retry queue for failed transcodes.

## Decisions

1. Use FFmpeg subprocess execution directly from Python.
- Decision: Invoke FFmpeg with `asyncio.create_subprocess_exec` for each rendition.
- Rationale: Matches existing architecture constraints and allows async parallel execution.
- Alternative considered: wrapper libraries around FFmpeg.
- Why not: Adds abstraction overhead without improving required control of codec flags.

2. Run rendition transcodes concurrently.
- Decision: Use `asyncio.gather` for rendition-level parallelism per creative.
- Rationale: Reduces end-to-end conditioning latency while preserving isolated per-rendition outputs.
- Alternative considered: Sequential transcoding.
- Why not: Slower and unnecessary for local Day 3 POC.

3. Adopt file-system cache sentinel strategy.
- Decision: Skip transcode when `{ADS_DIR}/{creative_id}/.done` exists and playlists are readable.
- Rationale: Fast repeated ad reuse and aligns with POC local-disk cache constraints.
- Alternative considered: always transcode.
- Why not: wastes CPU and increases ad break preparation time.

4. Parse HLS manifests into deterministic segment catalogs.
- Decision: Extract `#EXTINF` durations and associated segment filenames for each rendition.
- Rationale: Downstream stitcher logic needs duration-aware segment indexing.
- Alternative considered: leave parsing to manifest builder later.
- Why not: duplicates logic and weakens conditioned object guarantees.

## Risks / Trade-offs

- [Risk] FFmpeg binary availability/config mismatch on developer machines.
  - Mitigation: Fail with explicit errors and document prerequisites in README.

- [Risk] Encoding mismatch can cause playback discontinuities.
  - Mitigation: Lock critical flags to live-profile values from config and validate command construction in tests.

- [Risk] Partial cache artifacts from interrupted runs.
  - Mitigation: only write `.done` sentinel after all rendition outputs parse successfully.

- [Risk] Large creatives increase temporary disk usage.
  - Mitigation: use temp files and cleanup after conditioning completes or fails.
