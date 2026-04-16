## 1. Beacon Firer Module

- [ ] 1.1 Create `ssai-poc/beacon_firer.py` with async beacon firing orchestration.
- [ ] 1.2 Implement `fire_tracking_event(url, event_type)` async function for single URL firing with timeout (10s).
- [ ] 1.3 Implement `fire_tracking_events(pod: AdPod, event_types: list[str])` to fire multiple events asynchronously.
- [ ] 1.4 Add error handling and logging for beacon failures (4xx/5xx/timeout).
- [ ] 1.5 Implement beacon event recording to `beacon_history` with timestamp, URL, and outcome.

## 2. Session State Updates for Progress Tracking

- [ ] 2.1 Update `AdPod` model to include `segments_served: dict[str, int]` (rendition → count).
- [ ] 2.2 Update `AdPod` model to include `beacon_history: list[BeaconEvent]` for audit trail.
- [ ] 2.3 Add `BeaconEvent` dataclass with `event_type, url, timestamp, outcome` fields.
- [ ] 2.4 Update `Session` model to track `pod_progress_lock: asyncio.Lock` for concurrent access coordination.

## 3. Dynamic Ad Pod Loading

- [ ] 3.1 Update `routes/segment.py` variant serving to call VAST fetch on first ad-injected manifest request.
- [ ] 3.2 Implement soft timeout (5s) on VAST fetch; fall back to live-only manifest if timeout.
- [ ] 3.3 Wire VAST-fetched ad through ad conditioner pipeline to obtain ConditionedAd.
- [ ] 3.4 Load conditioned ad into `session.active_pod` upon successful conditioning.
- [ ] 3.5 Fire impression beacon asynchronously on first pod load for session.

## 4. Beacon Firing Integration into Segment Routes

- [ ] 4.1 Update ad segment serving route (`/session/{sid}/seg/ad/{rendition}/{index}`) to increment `segments_served[rendition]`.
- [ ] 4.2 Calculate progress percentage after each segment fetch and detect quartile threshold crossings.
- [ ] 4.3 Fire quartile beacons (firstQuartile, midpoint, thirdQuartile, complete) when thresholds are crossed.
- [ ] 4.4 Use asyncio.create_task() to fire beacons asynchronously without blocking segment response.
- [ ] 4.5 Add session-scoped lock around progress updates to coordinate multiple concurrent clients.
- [ ] 4.6 Record all beacon events in `session.beacon_history`.

## 5. Mid-Roll Trigger Control Endpoint

- [ ] 5.1 Create `ssai-poc/routes/control.py` with mid-roll trigger endpoint.
- [ ] 5.2 Implement `POST /session/{sid}/trigger-ad-break?duration={seconds}` endpoint with 202 response.
- [ ] 5.3 Validate duration parameter (1–120 seconds) and return 400 if invalid.
- [ ] 5.4 Implement background task for fresh VAST fetch and ad conditioning on trigger.
- [ ] 5.5 Store mid-roll ad pod marker in session state for injection on next variant request.
- [ ] 5.6 Calculate splice point based on duration and inject mid-roll pod in variant manifest.

## 6. App Wiring

- [ ] 6.1 Register beacon_firer module imports in routes/segment.py.
- [ ] 6.2 Register control router in main.py to expose mid-roll trigger endpoint.
- [ ] 6.3 Update session creation to initialize `segments_served`, `beacon_history`, and `pod_progress_lock`.
- [ ] 6.4 Wire ad pod state transitions in variant builder for dynamic loading.

## 7. Tests and Fixtures

- [ ] 7.1 Add unit tests for beacon firing with mock HTTP client (verify firing attempt and outcome logging).
- [ ] 7.2 Add unit tests for progress calculation and quartile threshold detection.
- [ ] 7.3 Add unit tests for dynamic VAST fetch and ad conditioning on first variant request.
- [ ] 7.4 Add endpoint tests for mid-roll trigger (202 response, duration validation, session not found 404).
- [ ] 7.5 Add integration test: full flow (session creation → dynamic pod load + impression → 4 ad segment fetches with quartile beacons).
- [ ] 7.6 Add test for concurrent clients on same pod (verify progress lock coordination).

## 8. Documentation and Validation

- [ ] 8.1 Document Day 5 beacon firing, dynamic pod loading, and mid-roll trigger usage in README.md.
- [ ] 8.2 Document mid-roll trigger endpoint with curl examples.
- [ ] 8.3 Document beacon event audit trail access (via session state inspection).
- [ ] 8.4 Run test suite and confirm all 20+ Day 5 tests pass.
- [ ] 8.5 Document Day 5 limitations (fire-and-forget beacons, no retry policy, mid-roll splice timing estimate).
