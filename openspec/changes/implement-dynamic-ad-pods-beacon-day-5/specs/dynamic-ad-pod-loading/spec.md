## ADDED Requirements

### Requirement: Dynamic ad pod loading from VAST/conditioning pipeline
The system SHALL load an active ad pod from the VAST fetch + conditioning pipeline outputs when a session variant manifest is first requested, instead of using a hardcoded placeholder reference.

#### Scenario: Fresh session loads ad pod on first variant request
- **WHEN** a variant manifest is requested for a session that has never been served with an ad pod
- **THEN** the system fetches VAST tag, parses ads, conditions creatives, and loads the resulting pod into `active_pod` state
- **AND** the variant playlist includes injected ad segments from the loaded pod

#### Scenario: Already-loaded pod is reused on subsequent variant requests
- **WHEN** a variant manifest is requested for a session that already has an `active_pod` loaded
- **THEN** the system uses the existing pod and does not re-fetch or re-condition

### Requirement: VAST fetch soft timeout for first manifest request
The system SHALL implement a soft timeout on VAST fetch during first variant request, allowing fallback to live-only manifest if VAST fetch exceeds timeout.

#### Scenario: VAST fetch succeeds within timeout
- **WHEN** variant manifest is requested and VAST fetch completes within 5 seconds
- **THEN** ad pod loads normally and pre-roll is injected

#### Scenario: VAST fetch exceeds timeout
- **WHEN** variant manifest is requested and VAST fetch does not complete within 5 seconds
- **THEN** system returns live-only variant without ad pod and logs fetch timeout
- **AND** subsequent variant requests will retry VAST fetch

## MODIFIED Requirements

### Requirement: Session state SHALL promote pending pre-roll to active on first ad-injected manifest
The system SHALL move `pending_pod` to `active_pod` when a pre-roll-injected variant playlist is first served to the player.

#### Scenario: Pending pod promotion occurs during dynamic pod loading
- **WHEN** a variant manifest is generated and a dynamic ad pod is loaded from VAST/conditioning pipeline
- **THEN** session `pending_pod` becomes `active_pod` and ad state reflects active playback
- **AND** impression beacon is fired for the loaded pod
