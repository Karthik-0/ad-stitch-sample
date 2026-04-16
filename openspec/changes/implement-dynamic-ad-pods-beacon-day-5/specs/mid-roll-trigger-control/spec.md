## ADDED Requirements

### Requirement: Mid-roll trigger endpoint accepts manual ad break insertion requests
The system SHALL expose an HTTP endpoint that allows operators to manually trigger ad break insertion for a session, simulating SCTE-35 cue reception.

#### Scenario: Operator triggers mid-roll with duration parameter
- **WHEN** operator calls `POST /session/{sid}/trigger-ad-break?duration=30`
- **THEN** the system accepts the request and returns immediately with HTTP 202 (Accepted)
- **AND** schedules ad fetch and insertion for the next variant manifest request

#### Scenario: Duration parameter is validated
- **WHEN** operator calls trigger endpoint with invalid duration (e.g., 0, >120 seconds)
- **THEN** the system returns HTTP 400 Bad Request with error message

#### Scenario: Session not found returns 404
- **WHEN** operator calls trigger endpoint for non-existent session
- **THEN** the system returns HTTP 404 Not Found

### Requirement: Mid-roll trigger fetches fresh VAST and conditions creatives
The system SHALL perform VAST fetch and ad conditioning on mid-roll trigger, independent of any prior pre-roll ad.

#### Scenario: Mid-roll trigger invokes fresh VAST fetch
- **WHEN** operator calls trigger endpoint
- **THEN** the system fetches VAST tag immediately and begins conditioning
- **AND** uses the same ad conditioning pipeline as pre-roll (parallel rendition transcoding)

#### Scenario: Conditioning failure is handled gracefully
- **WHEN** ad conditioning fails for a mid-roll trigger
- **THEN** the system logs the error and does not insert an ad break
- **AND** returns HTTP 503 Service Unavailable to indicate retry eligibility

### Requirement: Mid-roll ad pod is injected at splice point on next variant request
The system SHALL inject the mid-roll ad pod at a calculated live segment boundary when the next variant manifest is requested.

#### Scenario: Mid-roll pod injects at live media sequence boundary
- **WHEN** variant manifest is requested after mid-roll trigger
- **THEN** the system calculates splice point as current_live_media_sequence + {duration}
- **AND** injects live segments up to that point, then ad segments, then remaining live segments

#### Scenario: Mid-roll respects ad duration parameter
- **WHEN** mid-roll trigger specifies `duration=30` seconds
- **THEN** the system estimates live segments needed for 30 seconds (using segment_duration=6s → ~5 segments)
- **AND** splices at approximately the correct playback time
