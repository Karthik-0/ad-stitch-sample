## ADDED Requirements

### Requirement: Live segment route SHALL validate filenames before file access
The system SHALL enforce a strict filename validation pattern for live segment requests and reject invalid inputs.

#### Scenario: Invalid filename is rejected
- **WHEN** a live segment request contains traversal or non-conforming filename input
- **THEN** the service responds with a client error and does not read filesystem paths

### Requirement: Live segment route SHALL serve existing TS files with correct content type
The system SHALL stream existing live `.ts` files from configured live storage with `video/mp2t` content type.

#### Scenario: Existing live segment is served successfully
- **WHEN** a valid live segment filename exists in live storage
- **THEN** the service responds with segment bytes and `video/mp2t`

#### Scenario: Missing live segment returns not found
- **WHEN** a valid live segment filename is not present yet
- **THEN** the service responds with HTTP 404

### Requirement: Ad segment route SHALL serve conditioned segment files for active/completed pods
The system SHALL serve ad segment files from conditioned storage only when request context matches a valid session pod state.

#### Scenario: Valid ad segment request returns conditioned segment data
- **WHEN** session pod context and rendition/index identify an existing conditioned segment
- **THEN** the service responds with segment bytes and `video/mp2t`

#### Scenario: Mismatched pod or missing segment is rejected safely
- **WHEN** pod identity does not match active/completed context or file is absent
- **THEN** the service responds with not-found style behavior without leaking filesystem details
