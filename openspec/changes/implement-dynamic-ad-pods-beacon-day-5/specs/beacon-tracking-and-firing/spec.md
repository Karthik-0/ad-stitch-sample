## ADDED Requirements

### Requirement: Server-side beacon firing for tracking events
The system SHALL fire VAST tracking beacon URLs server-side as ad segments are consumed, without blocking segment responses to the client.

#### Scenario: Impression beacon fires on first ad segment fetch
- **WHEN** the first ad segment is fetched for an active pod
- **THEN** the system fires the impression tracking URL extracted from the ad's ParsedAd metadata asynchronously
- **AND** the segment response is returned immediately without waiting for beacon completion

#### Scenario: Quartile beacons fire at progress thresholds
- **WHEN** client fetches ad segments and progress crosses 25%, 50%, 75%, or 100%
- **THEN** the system fires the corresponding tracking URL (firstQuartile, midpoint, thirdQuartile, complete)
- **AND** beacons are fired asynchronously in the background

#### Scenario: Beacon URLs are extracted from ad metadata
- **WHEN** beacon firing is initiated for an ad pod
- **THEN** the system uses tracking event URLs from the ParsedAd's `tracking_events` list
- **AND** each event type maps to the correct VAST tracking URL

### Requirement: Beacon firing is resilient to network failures
The system SHALL handle beacon URL HTTP failures gracefully without impacting segment serving or state consistency.

#### Scenario: Beacon URL returns error status
- **WHEN** a beacon URL returns 4xx/5xx status
- **THEN** the system logs the failure and continues segment serving normally
- **AND** no retry is attempted in Day 5 scope

#### Scenario: Beacon URL times out
- **WHEN** a beacon URL does not respond within 10 seconds
- **THEN** the system cancels the request and logs the timeout
- **AND** segment serving is not blocked

### Requirement: Beacon firing history is maintained in session state
The system SHALL track beacon events fired for each session and make the history available for audit.

#### Scenario: Beacon event recorded with timestamp
- **WHEN** a beacon is fired
- **THEN** the system records the event type, URL, timestamp, and outcome (success/failure) in session `beacon_history`
