## Why

The SSAI POC specification defines a Day 1 foundation, but the repository does not yet contain a runnable service skeleton or session bootstrap flow. Implementing this first slice now establishes a stable baseline for all subsequent VAST, manifest stitching, and ad delivery work.

## What Changes

- Create the Python service project skeleton for the SSAI POC aligned with the technical specification.
- Add baseline configuration and data models used by all later components.
- Implement in-memory session creation and lookup primitives for initial request flows.
- Add initial API endpoints: `POST /session/new` and `GET /health`.
- Return a deterministic session bootstrap response with `session_id` and `master_url`.

## Capabilities

### New Capabilities
- `ssai-bootstrap-foundation`: Establishes the initial FastAPI service structure, session bootstrap lifecycle, and health endpoint behavior required to start playback sessions.

### Modified Capabilities
- None.

## Impact

- Adds a new backend service codebase for the SSAI POC.
- Introduces runtime dependencies for FastAPI/Uvicorn and supporting models.
- Defines initial API surface consumed by player/test tooling.
- Creates the base contract for later capabilities (VAST, ad conditioning, manifest building, and segment serving).
