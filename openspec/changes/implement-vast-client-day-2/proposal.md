## Why

Day 1 established the service skeleton, but ad workflows cannot progress without a reliable VAST/VMAP ingestion layer. Implementing the Day 2 VAST client now unlocks real ad metadata retrieval, creative selection, and tracking context needed by downstream conditioning and manifest splice work.

## What Changes

- Add a new VAST client module for fetching and parsing VAST responses from Google sample tags.
- Implement wrapper redirect resolution with recursion limits to prevent loops.
- Parse linear ad metadata including media file URL, duration, impression URLs, tracking URLs, and click-through URLs.
- Apply VAST macro substitution for tracking/impression URLs (for example `[CACHEBUSTING]`).
- Add VMAP parsing support to extract ad break tags for future pod-based insertion.
- Add Day 2 unit tests using saved XML fixtures for parser correctness and edge cases.

## Capabilities

### New Capabilities
- `vast-fetch-and-parse`: Fetches VAST/VMAP documents, resolves wrappers, and returns normalized parsed ad metadata for SSAI workflows.

### Modified Capabilities
- None.

## Impact

- Adds a core integration module in `ssai-poc` for remote ad metadata retrieval.
- Introduces XML parsing and wrapper-following behavior that downstream ad conditioning depends on.
- Adds parser fixture tests to validate ad metadata extraction deterministically.
- Expands internal model usage by producing `ParsedAd`-style outputs consumed by later phases.
