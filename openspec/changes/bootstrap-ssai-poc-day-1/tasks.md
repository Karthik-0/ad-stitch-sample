## 1. Project Scaffolding

- [x] 1.1 Create the Day 1 service directory/module skeleton (`main`, `config`, `models`, `session_manager`, and route package).
- [x] 1.2 Add `requirements.txt` with FastAPI/Uvicorn/httpx/pydantic dependencies from the technical spec.
- [x] 1.3 Add startup documentation for running the app locally and expected Day 1 API behavior.

## 2. Foundation Models and Configuration

- [x] 2.1 Implement baseline configuration constants for paths, renditions, stream settings, and public base URL.
- [x] 2.2 Implement core data models (`AdState`, `TrackingEvent`, `ConditionedAd`, `AdPod`, `Session`) with day-1-compatible defaults.
- [x] 2.3 Add unit checks for model construction and enum/default behavior.

## 3. Session Manager Core

- [x] 3.1 Implement in-memory session storage with session creation and lookup operations.
- [x] 3.2 Implement session update support and not-found error mapping suitable for HTTP 404 responses.
- [x] 3.3 Add initial cleanup strategy for expired sessions (task skeleton or background hook).
- [x] 3.4 Add tests for create/get/update behaviors and unknown-session handling.

## 4. Bootstrap API Endpoints

- [x] 4.1 Implement `GET /health` returning HTTP 200 with a machine-readable liveness payload.
- [x] 4.2 Implement `POST /session/new` request model and response model aligned with `session_id` and `master_url` contract.
- [x] 4.3 Wire endpoint handlers to the session manager and configuration base URL logic.
- [x] 4.4 Add endpoint tests verifying response shape, status codes, and unique session IDs across requests.

## 5. Day 1 Verification

- [x] 5.1 Validate local run flow (`uvicorn` startup, health probe, session creation via curl/Postman).
- [x] 5.2 Confirm outputs satisfy Day 1 requirements from the bootstrap foundation spec.
- [x] 5.3 Document known Day 1 limitations and explicit deferral to Day 2+ capabilities.
