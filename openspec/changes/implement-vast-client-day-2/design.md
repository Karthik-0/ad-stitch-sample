## Context

The Day 1 bootstrap provides a running FastAPI service and session bootstrap endpoint, but ad insertion workflows are still blocked because the system cannot yet ingest VAST/VMAP metadata. Day 2 introduces a dedicated VAST client module that fetches ad descriptors from Google sample tags, resolves wrappers, and exposes normalized parsed output for downstream conditioner and manifest components.

The design must support:
- Async HTTP I/O for low-latency response handling.
- Deterministic parsing and testability using fixture XML files.
- Guardrails against malformed XML and wrapper loops.

## Goals / Non-Goals

**Goals:**
- Implement an async VAST fetch API with correlator support.
- Parse linear ad metadata including progressive MP4 media, duration, impression URLs, and tracking events.
- Resolve wrapper redirects up to a bounded depth.
- Support VMAP ad break extraction for future pod scheduling.
- Add fixture-based tests for parser behavior and edge cases.

**Non-Goals:**
- Downloading ad media files.
- FFmpeg transcoding/conditioning.
- Manifest rewrite/splice behavior.
- Beacon delivery execution.
- Production-scale retry queues or distributed caching.

## Decisions

1. Keep parsing in a dedicated `vast_client.py` module with typed dataclasses.
- Decision: Introduce local parsed output models (`ParsedAd`, `AdBreakInfo`) near the parser implementation.
- Rationale: Keeps external contract explicit and independent from transport details.
- Alternative considered: Return raw XML nodes/dicts.
- Why not: Weak typing increases coupling and makes downstream logic brittle.

2. Use async `httpx` client with bounded wrapper recursion.
- Decision: Fetch through `httpx.AsyncClient` and follow wrappers with a max depth of 5.
- Rationale: Handles expected ad-serving redirect patterns while preventing loops.
- Alternative considered: Unlimited recursion with cycle detection.
- Why not: More complexity for Day 2 without stronger practical benefit.

3. Implement strict media file selection rules.
- Decision: Filter `MediaFile` entries to `delivery=progressive` and `type=video/mp4`, then choose highest bitrate.
- Rationale: Matches technical spec and provides stable creative selection for conditioning.
- Alternative considered: Select first compatible media file.
- Why not: Reduces quality and can produce inconsistent outputs.

4. Replace macros during parse normalization.
- Decision: Apply `[CACHEBUSTING]` replacement during URL normalization in parser output.
- Rationale: Ensures generated tracking/impression URLs are executable without requiring every caller to normalize.
- Alternative considered: Leave macros untouched and normalize at beacon-time.
- Why not: Spreads responsibility and complicates tests.

## Risks / Trade-offs

- [Risk] Network flakiness from ad servers can slow endpoint responses.
  - Mitigation: Keep failures non-fatal for future flows and add timeout/error boundaries in fetch functions.

- [Risk] XML variants may omit expected fields (duration, tracking events).
  - Mitigation: Use tolerant parsing with clear validation errors and defaults where safe.

- [Risk] Wrapper chains may exceed recursion limit for some tags.
  - Mitigation: Return explicit wrapper-depth errors so callers can skip ad gracefully.

- [Risk] VMAP interpretation may vary across providers.
  - Mitigation: Implement minimal standards-compliant extraction (break id/time offset/tag URI) and expand later as needed.
