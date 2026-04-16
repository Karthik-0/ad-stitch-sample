## Context

Day 4 established manifest splicing with segment serving but used hardcoded pre-roll pod references. End-to-end SSAI playback requires:

1. **Ad Pod Loading**: When a session variant manifest is first built, an active ad pod must be materialized from VAST parsing + conditioning pipeline outputs, not from static configuration.
2. **Beacon Firing**: VAST tracking URLs (impression, quartiles, complete) must fire server-side as ad segments are consumed, keyed to playback progress (0%, 25%, 50%, 75%, 100%).
3. **State Continuity**: Session pod state, beacon history, and segment progress must survive variant/segment requests within a session lifecycle.

Current constraints:
- Session state is in-memory only; no persistence across restarts.
- Beacon URLs are extracted from VAST ParsedAd but not yet fired.
- Ad pod loading is not yet wired to VAST/conditioning outputs.

## Goals / Non-Goals

**Goals:**
- Load dynamic ad pods from POST `/session/new` VAST fetch flow instead of hardcoded placeholders.
- Implement async beacon firing for impression, firstQuartile, midpoint, thirdQuartile, complete events.
- Track segments served per rendition and calculate progress thresholds for quartile firing.
- Fire beacons as segments are fetched by the client, keyed to progress calculations.
- Add mid-roll trigger endpoint for manual ad break insertion (Day 5 enabler; full implementation may extend to Day 6).
- Maintain beacon history and event logs in session state for audit/debugging.

**Non-Goals:**
- Distributed beacon deduplication or retry logic (fire-and-forget only).
- DVR/window management beyond current Day 4 scope.
- SCTE-35 extraction or real-time cue parsing (manual trigger only).
- Beacon firing at exact time boundaries; progress-based firing is acceptable.

## Decisions

1. **Dynamic ad pod sourcing on first manifest build.**
   - Decision: During variant manifest generation, if session has no `active_pod` and no `pending_pod`, fetch fresh VAST, condition, and load ad pod into `pending_pod`. On manifest write, promote pending to active and fire impression beacon.
   - Rationale: Aligns with Day 4 state machine; deterministic pod availability per session lifecycle.
   - Alternative: Pre-fetch all ads on session creation. Why not: slower session creation, wasted conditioning for skipped sessions.

2. **Beacon firing event and progress tracking with in-session counters.**
   - Decision: Track `segments_served[rendition]` counter in `active_pod`. On each ad segment fetch, increment counter, calculate progress = segments_served / total_segments, fire beacons when progress crosses 0.25, 0.5, 0.75, 1.0 thresholds. Fire impression (0%) on first ad segment fetch of session.
   - Rationale: Simple, no external beacon state needed; tolerates client seek/retry.
   - Alternative: Track by wall-clock time or byte position. Why not: client seeks break assumptions; segments served is deterministic.

3. **Async httpx beacon firing without blocking segment responses.**
   - Decision: Fire beacons in background Task via asyncio.create_task(), return segment response immediately.
   - Rationale: Low-latency segment serving; beacon delivery not critical to UX.
   - Alternative: Fire beacons synchronously. Why not: adds 100–200ms per beacon to segment response time.

4. **Mid-roll trigger as HTTP POST with fresh VAST fetch.**
   - Decision: POST `/session/{sid}/trigger-ad-break?duration={seconds}` fetches fresh VAST, conditions creatives, creates new `pending_pod`, sets insertion flag. Next variant request injects at current live media sequence + {duration}.
   - Rationale: Simulates SCTE-35 workflow; enables testing before real cue extraction.
   - Alternative: Queue pre-fetched pods only. Why not: limits testing flexibility; fresh fetch validates VAST pipeline.

5. **Beacon URL list sourced from conditioned ad metadata.**
   - Decision: ParsedAd carries `tracking_events: list[TrackingEvent]` with event type + URL. In beacon_firer, iterate tracking events, fire each URL once per session.
   - Rationale: VAST source of truth for tracking URLs; no external beacon catalog.
   - Alternative: Static beacon list in config. Why not: doesn't reflect ad source diversity.

## Risks / Trade-offs

- [Risk] First manifest request delays if VAST fetch or conditioning is slow.
  - Mitigation: Add soft timeout (5s) on VAST fetch; if it fails, return live-only manifest and allow retry on next request.

- [Risk] Beacon firing races if same session is accessed by multiple overlay clients.
  - Mitigation: Use session-scoped lock (asyncio.Lock) around segment progress updates; accept first-client-wins for beacon firing.

- [Risk] Mid-roll trigger endpoint allows denial-of-service if called repeatedly.
  - Mitigation: Rate limit per session; validate duration is reasonable (1–120s).

- [Risk] Beacon URL firing may timeout or fail silently, masking ad tracking issues.
  - Mitigation: Log all beacon attempts with timestamp, URL, and outcome for debugging.

## Migration Plan

1. Add `beacon_firer.py` module with `fire_beacon_url()` and `fire_tracking_event()` functions.
2. Update `session_manager.py` Ad Pod data model to include `segments_served` dict and `beacon_history` list.
3. Add `routes/control.py` with `/session/{sid}/trigger-ad-break` endpoint.
4. Update `routes/segment.py` variant serving to load dynamic ad pods on first fetch and fire impression beacon.
5. Update `routes/segment.py` segment serving to increment `segments_served`, check thresholds, fire quartile beacons asynchronously.
6. Add unit tests for beacon logic, progress calculations, and dynamic pod loading.
7. Integration test: session creation → variant fetch (impression + pod load) → 4 segment fetches (quartile beacons).

Rollback: Revert to hardcoded pod path in segment route if dynamic loading fails; continue firing beacons asynchronously (safe background tasks).

## Open Questions

- Should beacon firing be retried on 5xx response? (Defer to Day 6: implement retry with exponential backoff)
- Should mid-roll ad pods use the same creative as pre-roll, or fetch independently? (Day 5: independent fetch for variety)
- Should beacon firing be logged to a separate audit file or integrated into app logs? (Day 5: integrated app logs; Day 6: consider structured audit log sink)
