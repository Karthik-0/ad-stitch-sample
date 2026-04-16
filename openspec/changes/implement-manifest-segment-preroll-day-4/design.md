## Context

Day 3 introduced conditioned ad assets, but playback clients still consume raw FFmpeg outputs directly and cannot receive stitched ad playback. Day 4 introduces a session-aware manifest/segment layer that rewrites live URIs, injects pre-roll ad segments with discontinuity boundaries, and exposes route handlers for serving live/ad TS files through the application.

This scope is intentionally limited to pre-roll only with hardcoded pod wiring to validate splice behavior before dynamic pod sourcing.

## Goals / Non-Goals

**Goals:**
- Build session-aware master playlist rewriting for variant endpoint routing.
- Build variant playlist generation for:
  - live passthrough rewrite mode
  - pre-roll injected mode (hardcoded ad pod)
- Add segment routes for live and ad TS asset serving with basic validation.
- Update session ad state when pending pre-roll is promoted to active playback.
- Add tests for key rewrite/validation behaviors.

**Non-Goals:**
- Mid-roll trigger orchestration.
- Beacon quartile firing correctness.
- Full ad pod lifecycle history semantics.
- DVR/window management.
- Production-grade CDN/storage abstractions.

## Decisions

1. Keep manifest construction as pure string transformation with bounded parser assumptions.
- Decision: Parse only required HLS tags/URI lines for Day 4 and preserve other lines as-is where possible.
- Rationale: Fast, deterministic implementation suited to current FFmpeg output format.
- Alternative considered: full-featured HLS parser dependency.
- Why not: unnecessary complexity for POC milestone.

2. Treat pre-roll splice as first-manifest promotion from pending to active pod.
- Decision: On first variant build that includes ad, move `pending_pod` to `active_pod` and set ad state active.
- Rationale: Aligns playback timeline with actual client fetch behavior.
- Alternative considered: promote state earlier during session creation.
- Why not: risks state drift when clients never request playback.

3. Validate live segment filenames via strict regex allow-list.
- Decision: Restrict live segment route to expected FFmpeg naming pattern and deny traversal input.
- Rationale: Prevents unsafe file reads while preserving known stream layout.
- Alternative considered: generic path normalization only.
- Why not: easier to bypass with edge cases.

4. Keep Day 4 pre-roll source hardcoded for deterministic verification.
- Decision: Use static conditioned ad reference/pod fixture path for initial splice integration.
- Rationale: Reduces moving parts while validating manifest and segment routing mechanics.
- Alternative considered: fully dynamic pod retrieval from VAST-conditioned pipeline.
- Why not: broadens scope beyond Day 4 acceptance criteria.

## Risks / Trade-offs

- [Risk] Manifest rewrite assumptions may break on variant format changes.
  - Mitigation: Add regression tests using representative playlist fixtures.

- [Risk] Route-level file serving may return stale/missing live segments near edge.
  - Mitigation: Return explicit 404 and rely on player retry behavior.

- [Risk] State transitions around pending/active pods can become inconsistent.
  - Mitigation: centralize promotion logic in variant builder and cover in tests.

- [Risk] Hardcoded pre-roll path may mask integration issues with dynamic ad pipelines.
  - Mitigation: explicitly document this as Day 4 limitation and plan Day 5 integration follow-up.
