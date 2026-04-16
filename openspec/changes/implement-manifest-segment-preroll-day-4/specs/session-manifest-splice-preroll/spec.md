## ADDED Requirements

### Requirement: Master playlist builder SHALL rewrite variant URIs to session endpoints
The system SHALL parse the live master playlist and rewrite variant URIs so clients request session-scoped variant playlists from the stitcher service.

#### Scenario: Variant URIs are rewritten for a session
- **WHEN** a client requests `/session/{sid}/master.m3u8`
- **THEN** each variant URI points to `/session/{sid}/{rendition}.m3u8`

### Requirement: Variant builder SHALL support live passthrough rewrite mode
The system SHALL return variant playlists that rewrite live segment filenames to stitcher live-segment routes when no pre-roll pod is pending/active.

#### Scenario: Live-only variant returns rewritten segment routes
- **WHEN** a session has no pending pre-roll pod
- **THEN** each segment URI resolves to `/session/{sid}/seg/live/{filename}`

### Requirement: Variant builder SHALL inject pre-roll with discontinuities
The system SHALL inject pre-roll ad segments with discontinuity boundaries and cue markers when a pending pre-roll pod exists.

#### Scenario: Pending pre-roll is inserted ahead of live playback
- **WHEN** variant playlist is generated while `pending_pod` exists
- **THEN** playlist contains ad segment URIs, cue-out/in markers, and discontinuity tags before resuming live segment URIs

### Requirement: Session state SHALL promote pending pre-roll to active on first ad-injected manifest
The system SHALL move `pending_pod` to `active_pod` when a pre-roll-injected variant playlist is first served to the player.

#### Scenario: Pending pod promotion occurs during variant generation
- **WHEN** a variant manifest is built with pre-roll content
- **THEN** session `pending_pod` becomes `active_pod` and ad state reflects active playback
