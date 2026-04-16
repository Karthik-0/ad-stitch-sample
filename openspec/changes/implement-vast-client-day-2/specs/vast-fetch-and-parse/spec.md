## ADDED Requirements

### Requirement: VAST fetch API SHALL retrieve ad documents with correlator support
The system SHALL provide an asynchronous fetch API that retrieves VAST documents from configured tag URLs and supports adding a fresh correlator value for each request.

#### Scenario: Correlator is attached to request URL
- **WHEN** a VAST tag is fetched
- **THEN** the request URL includes a newly generated correlator value

#### Scenario: Fetch returns parsable VAST payload
- **WHEN** a valid VAST endpoint returns XML
- **THEN** the client returns parsed ad objects instead of raw XML content

### Requirement: Wrapper handling SHALL resolve redirected VAST tags safely
The system SHALL follow VAST wrapper redirects and stop recursion at a maximum depth of five to avoid loops.

#### Scenario: Wrapper chain resolves to inline ad
- **WHEN** a VAST response contains a valid `Wrapper` with `VASTAdTagURI`
- **THEN** the client follows the redirect and returns the final inline ad metadata

#### Scenario: Wrapper depth exceeds limit
- **WHEN** wrapper recursion goes beyond five redirects
- **THEN** the client fails with an explicit wrapper-depth error outcome

### Requirement: Parser SHALL extract normalized linear ad metadata
The system SHALL parse linear ad data including creative identifier, selected media URL, duration in seconds, impression URLs, and tracking events.

#### Scenario: MediaFile selection uses highest bitrate progressive MP4
- **WHEN** multiple media files are available
- **THEN** the parser selects the highest-bitrate media file where delivery is `progressive` and type is `video/mp4`

#### Scenario: Duration formats are converted to seconds
- **WHEN** VAST duration is represented as `HH:MM:SS` or `HH:MM:SS.mmm`
- **THEN** the parser returns a numeric duration in seconds

### Requirement: Tracking and impression URLs SHALL be macro-normalized
The system SHALL normalize macro placeholders in parsed URLs, including `[CACHEBUSTING]`, before returning parsed metadata.

#### Scenario: Cachebusting macro is replaced
- **WHEN** impression or tracking URL contains `[CACHEBUSTING]`
- **THEN** the parsed URL contains a generated numeric replacement value

### Requirement: VMAP fetch API SHALL expose ad break tag references
The system SHALL provide an asynchronous VMAP parser that extracts ad break entries and associated VAST tag URIs for future pod orchestration.

#### Scenario: VMAP response contains multiple ad breaks
- **WHEN** a VMAP payload includes multiple `AdBreak` entries
- **THEN** the parser returns an ordered list with break identifiers and VAST tag URIs

#### Scenario: VMAP break without VAST URI is ignored safely
- **WHEN** an `AdBreak` has no valid VAST tag URI
- **THEN** the parser omits that entry without crashing the parse flow
