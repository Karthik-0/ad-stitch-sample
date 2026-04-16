## 1. Manifest Builder Foundation

- [x] 1.1 Create `ssai-poc/manifest_builder.py` with `build_master` and `build_variant` entry points.
- [x] 1.2 Implement master playlist parsing and variant URI rewriting to `/session/{sid}/{rendition}.m3u8`.
- [x] 1.3 Implement live-only variant rewrite path that maps segment filenames to `/session/{sid}/seg/live/{filename}`.

## 2. Pre-Roll Splice Assembly

- [x] 2.1 Implement pre-roll injected variant assembly with discontinuity and cue markers.
- [x] 2.2 Build ad segment URI mapping for hardcoded pre-roll pod references in Day 4 scope.
- [x] 2.3 Append resumed live segment entries after ad block insertion.
- [x] 2.4 Promote `pending_pod` to `active_pod` and set active ad state when injected manifest is first served.

## 3. Segment Route Implementation

- [x] 3.1 Create `ssai-poc/routes/segment.py` with live and ad segment endpoints.
- [x] 3.2 Implement strict live filename validation (`^video-[a-z0-9]+\d+\.ts$`) and reject invalid inputs.
- [x] 3.3 Stream valid live TS files from configured live storage with `video/mp2t`.
- [x] 3.4 Implement conditioned ad segment serving for valid session pod context and file presence.
- [x] 3.5 Return safe not-found behavior for missing/mismatched ad segment requests.

## 4. App Wiring and Session Integration

- [x] 4.1 Register new manifest and segment routes in app routing configuration.
- [x] 4.2 Wire manifest endpoints to session manager and builder outputs.
- [x] 4.3 Ensure Day 4 pre-roll hardcoded behavior is isolated and documented for later dynamic replacement.

## 5. Tests and Fixtures

- [x] 5.1 Add playlist fixture inputs for master and variant rewrite tests.
- [x] 5.2 Add unit tests for master/variant rewrite behavior in live-only mode.
- [x] 5.3 Add unit tests for pre-roll injection structure and pending-to-active state promotion.
- [x] 5.4 Add endpoint tests for live filename validation, successful live/ad segment serving, and 404 behavior.

## 6. Documentation and Validation

- [x] 6.1 Document Day 4 manifest/segment route usage and endpoint behavior in `ssai-poc/README.md`.
- [x] 6.2 Run test suite and confirm Day 4 pre-roll manifest/segment requirements pass.
- [x] 6.3 Document known Day 4 limitations and deferred concerns (hardcoded pre-roll source, beacon integration, mid-roll support).
