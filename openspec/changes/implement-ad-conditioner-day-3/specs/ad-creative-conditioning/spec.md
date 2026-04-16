## ADDED Requirements

### Requirement: Conditioner SHALL download creative media before transcoding
The system SHALL download the selected ad media file from the parsed ad metadata URL into temporary local storage before starting FFmpeg transcoding.

#### Scenario: Creative media is downloaded successfully
- **WHEN** conditioning starts for a parsed ad
- **THEN** the media file is stored locally and becomes the FFmpeg input source

### Requirement: Conditioner SHALL transcode renditions using live-compatible settings
The system SHALL run FFmpeg per configured rendition with framerate, GOP, audio, and profile settings aligned to live stream parameters.

#### Scenario: Rendition transcode command includes critical compatibility flags
- **WHEN** the conditioner builds FFmpeg command arguments
- **THEN** command arguments include required values for `-r`, `-g`, `-keyint_min`, `-sc_threshold`, `-ar`, `-ac`, and H.264 profile/level

#### Scenario: Transcodes run for all configured renditions
- **WHEN** conditioning executes for a parsed ad
- **THEN** each configured rendition outputs a `.m3u8` playlist and associated `.ts` segments

### Requirement: Conditioner SHALL parse generated playlists into segment catalogs
The system SHALL parse generated rendition playlists and capture ordered segment filename and duration tuples.

#### Scenario: Parsed rendition playlist returns ordered segment metadata
- **WHEN** a rendition playlist is read after transcode
- **THEN** segment tuples are returned in playback order with `EXTINF` durations

### Requirement: Conditioner SHALL support cache reuse for previously conditioned creatives
The system SHALL skip re-transcoding when a previously completed creative cache entry is present and readable.

#### Scenario: Cache hit bypasses FFmpeg execution
- **WHEN** conditioning is requested for a creative with an existing `.done` marker and valid outputs
- **THEN** the conditioner returns parsed cached outputs without running new FFmpeg transcodes

### Requirement: Conditioner SHALL return a normalized conditioned ad object
The system SHALL return a `ConditionedAd` output that includes creative identity, source duration, per-rendition segment catalogs, and carried tracking/impression metadata.

#### Scenario: Conditioned ad output contains rendition maps and metadata
- **WHEN** conditioning completes successfully
- **THEN** returned object contains `creative_id`, `duration_sec`, rendition segment map, tracking events, and impression URLs
