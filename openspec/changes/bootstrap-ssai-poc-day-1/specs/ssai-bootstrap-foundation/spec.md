## ADDED Requirements

### Requirement: Service skeleton SHALL expose bootstrap endpoints
The system SHALL provide an HTTP service with endpoint handlers for `POST /session/new` and `GET /health` as part of the initial SSAI POC foundation.

#### Scenario: Health endpoint returns service liveness
- **WHEN** a client requests `GET /health`
- **THEN** the service responds with HTTP 200 and a machine-readable liveness payload

#### Scenario: Session bootstrap endpoint is reachable
- **WHEN** a client sends `POST /session/new` with a valid JSON body
- **THEN** the service responds successfully without requiring ad-stitching components from later milestones

### Requirement: Session creation SHALL return stable bootstrap metadata
The system SHALL create a new session identifier for each `POST /session/new` request and return both `session_id` and `master_url` in the response.

#### Scenario: Session response includes required fields
- **WHEN** a client creates a new session
- **THEN** the response includes non-empty `session_id` and `master_url` fields

#### Scenario: Multiple session requests produce independent identifiers
- **WHEN** two session creation requests are made
- **THEN** each response contains a different `session_id`

### Requirement: Baseline configuration and models SHALL be defined
The system SHALL define foundational configuration constants and typed data models required for session lifecycle and future ad-state expansion.

#### Scenario: Configuration constants are available to bootstrap flow
- **WHEN** session bootstrap logic is executed
- **THEN** required configuration values are imported from a centralized configuration module

#### Scenario: Session model supports day-1 and future ad state fields
- **WHEN** a session object is instantiated during bootstrap
- **THEN** it includes required day-1 identity/timestamp fields and ad-state placeholders specified by the technical spec

### Requirement: Session manager SHALL provide in-memory lifecycle primitives
The system SHALL provide in-memory session manager operations to create, retrieve, and update session state.

#### Scenario: Session can be retrieved after creation
- **WHEN** a session is created through the session manager
- **THEN** a subsequent lookup by `session_id` returns the same session

#### Scenario: Unknown session lookup fails predictably
- **WHEN** a lookup is performed for a non-existent session ID
- **THEN** the operation returns a not-found outcome suitable for HTTP 404 mapping
