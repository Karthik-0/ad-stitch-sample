## Context

The repository currently has technical documentation and sample FFmpeg output artifacts, but no runnable SSAI service implementation. The Day 1 milestone in the technical specification defines the foundational slice needed before ad insertion logic can be developed: project skeleton, core config/models, session manager, and bootstrap endpoints.

Constraints for this slice:
- Keep implementation lightweight and local-first (in-memory state, local paths).
- Align API contracts with the technical spec so downstream days can build incrementally.
- Favor deterministic behavior and debuggability over production hardening.

## Goals / Non-Goals

**Goals:**
- Establish the initial FastAPI service structure and module layout for the SSAI POC.
- Define baseline configuration constants required by later modules.
- Provide initial data models for session and ad state contracts.
- Implement an in-memory session manager with create/get/update primitives.
- Expose `POST /session/new` and `GET /health` endpoints with stable response shapes.

**Non-Goals:**
- VAST/VMAP retrieval and parsing.
- Ad creative conditioning and transcoding.
- Manifest rewriting/splicing and segment proxying.
- Tracking beacon firing and mid-roll trigger orchestration.
- Persistence beyond in-memory process lifetime.

## Decisions

1. Build an app-first skeleton with explicit module boundaries.
- Decision: Create discrete modules (`config`, `models`, `session_manager`, route modules, app entrypoint) from day one.
- Rationale: Reduces refactoring friction as days 2-8 add complex behaviors.
- Alternative considered: Single-file prototype in `main.py`.
- Why not: Fast initial velocity, but quickly becomes brittle once ad lifecycle and manifest logic are added.

2. Use in-memory session storage with per-session locking.
- Decision: Keep a process-local store keyed by `session_id`; include lock-aware update access patterns.
- Rationale: Matches POC scope while preserving a migration path to Redis.
- Alternative considered: Introduce Redis immediately.
- Why not: Adds infrastructure and operational overhead before behavior is validated.

3. Fix Day 1 API contract for session bootstrap.
- Decision: `POST /session/new` always returns `session_id` and `master_url`, with optional preroll flag accepted but not fully executed yet.
- Rationale: Enables test clients to integrate early and keeps backwards compatibility with later ad logic.
- Alternative considered: Delay endpoint until pre-roll is fully implemented.
- Why not: Blocks frontend/player integration and slows iterative delivery.

4. Keep health endpoint minimal.
- Decision: `GET /health` returns lightweight liveness metadata only.
- Rationale: Satisfies orchestration and local verification needs without premature diagnostics complexity.
- Alternative considered: Include deep dependency checks.
- Why not: No external dependencies exist in Day 1 scope.

## Risks / Trade-offs

- [Risk] Session loss on process restart due to in-memory state.
  - Mitigation: Document non-durable behavior and keep session manager interface compatible with future persistent stores.

- [Risk] API may drift from later implementation details.
  - Mitigation: Anchor endpoint shapes and models to the technical spec and enforce through tests in subsequent tasks.

- [Risk] Accepting `preroll` early may imply behavior not yet implemented.
  - Mitigation: Explicitly define Day 1 behavior (session bootstrap only) and defer ad workflow to later tasks.

- [Risk] Local path/config defaults may not match all developer environments.
  - Mitigation: Centralize defaults in config and allow simple override strategy in future iterations.
