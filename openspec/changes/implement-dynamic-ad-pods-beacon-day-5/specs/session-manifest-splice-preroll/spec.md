## MODIFIED Requirements

### Requirement: Session state SHALL promote pending pre-roll to active on first ad-injected manifest
The system SHALL move `pending_pod` to `active_pod` and fire impression beacon when a pre-roll-injected variant playlist is first served to the player.

#### Scenario: Dynamic ad pod loading and promotion on first variant request
- **WHEN** variant manifest is first requested for a session with no active pod
- **THEN** the system fetches VAST tag, conditions creatives, and loads pod into `active_pod`
- **AND** fires impression beacon asynchronously for the loaded pod
- **AND** returns variant playlist with ad segments injected

#### Scenario: Already-loaded pod is not re-loaded on subsequent requests
- **WHEN** variant manifest is requested for a session that already has an `active_pod`
- **THEN** the system uses existing pod and does not re-fetch VAST or re-condition
- **AND** no repeat impression beacon is fired
