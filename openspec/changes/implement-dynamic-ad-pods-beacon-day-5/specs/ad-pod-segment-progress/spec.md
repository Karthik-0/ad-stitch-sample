## ADDED Requirements

### Requirement: Segment progress tracking per rendition and pod
The system SHALL track the number of ad segments served for each rendition within an active pod and calculate progress percentages for quartile thresholds.

#### Scenario: Progress counter increments on each segment fetch
- **WHEN** an ad segment is fetched for an active pod
- **THEN** the system increments `active_pod.segments_served[rendition]` counter
- **AND** calculates progress = segments_served / total_segments in that rendition

#### Scenario: Progress thresholds trigger quartile events
- **WHEN** progress calculation shows the first segment fetch of a new quartile threshold
- **THEN** the system identifies the threshold crossings (0%, 25%, 50%, 75%, 100%)
- **AND** marks those thresholds as reached for beacon firing

#### Scenario: Counters are maintained across rendition differences
- **WHEN** player switches renditions mid-ad (e.g., 240p → 480p) and continues fetching segments
- **THEN** the system tracks segments served per rendition separately
- **AND** quartile thresholds are calculated per rendition

### Requirement: Multiple clients on same session share pod progress
The system SHALL maintain single pod progress state across multiple simultaneous rendition requests for the same session.

#### Scenario: Two clients on different renditions see shared pod progress
- **WHEN** two clients request ad segments from the same session pod but different renditions simultaneously
- **THEN** the system coordinates progress tracking with a session-scoped lock
- **AND** the first client to fetch a segment updates progress and fires beacons; the second client uses the updated state

### Requirement: Segment progress persists across manifest requests
The system SHALL maintain continuous segment progress tracking even if the client re-requests the variant manifest mid-ad.

#### Scenario: Manifest re-request does not reset progress
- **WHEN** client fetches variant manifest after already fetching some ad segments
- **THEN** system does not reset `segments_served` counters
- **AND** progress calculations remain continuous from prior segment fetches
