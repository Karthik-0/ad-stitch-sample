## 1. VAST Client Foundations

- [x] 1.1 Create `ssai-poc/vast_client.py` with typed output models for parsed ad and VMAP break data.
- [x] 1.2 Add async HTTP fetch helpers using `httpx.AsyncClient` with timeout and status/error handling.
- [x] 1.3 Implement correlator generation and URL augmentation for VAST/VMAP tag requests.

## 2. VAST Parsing and Wrapper Resolution

- [x] 2.1 Implement XML parsing helpers for ad nodes, linear creative blocks, and text extraction.
- [x] 2.2 Implement media file selection logic for highest-bitrate `progressive` `video/mp4` candidates.
- [x] 2.3 Implement duration parsing for `HH:MM:SS` and `HH:MM:SS.mmm` formats into seconds.
- [x] 2.4 Implement wrapper resolution through `VASTAdTagURI` with max depth of five.
- [x] 2.5 Implement macro normalization for `[CACHEBUSTING]` in impression/tracking URLs.

## 3. VMAP Parsing Support

- [x] 3.1 Implement VMAP parsing to extract ordered ad breaks and associated VAST tag URIs.
- [x] 3.2 Ignore malformed or missing-URI ad breaks safely without terminating parse flow.

## 4. Public API Wiring

- [x] 4.1 Implement `fetch_vast(tag_url: str)` returning normalized parsed ad objects.
- [x] 4.2 Implement `fetch_vmap(tag_url: str)` returning normalized VMAP break objects.
- [x] 4.3 Ensure wrapper-depth and parsing failures return explicit error outcomes for callers.

## 5. Tests and Fixtures

- [x] 5.1 Add XML fixtures under `ssai-poc/tests/` for inline VAST, wrapper VAST, and VMAP examples.
- [x] 5.2 Add unit tests for media selection, duration conversion, and macro normalization.
- [x] 5.3 Add unit tests for wrapper recursion success and depth-limit failure behavior.
- [x] 5.4 Add unit tests for VMAP ad break extraction and malformed-break handling.

## 6. Documentation and Validation

- [x] 6.1 Document Day 2 VAST client usage and expected return shapes in `ssai-poc/README.md`.
- [x] 6.2 Run test suite and confirm Day 2 parser requirements pass deterministically.
- [x] 6.3 Document known Day 2 limitations and deferred concerns (network retries, advanced VMAP semantics).
