## Why

Day 4 established manifest rewriting and segment serving with a hardcoded pre-roll placeholder. Dynamic ad pod loading and server-side beacon firing are needed to complete the end-to-end SSAI flow: content playback must receive ads sourced from VAST parsing and conditioning, and beacon URLs must fire at correct quartile points to enable GAM to track impressions and viewability.

## What Changes

- Replace hardcoded pre-roll pod reference with dynamic ad pod loading from VAST/conditioning pipeline per session.
- Implement beacon firing module for async server-side impression, quartile, and completion tracking URLs.
- Track ad pod progress (segments served) per rendition and fire quartile beacons at 25%, 50%, 75%, 100% thresholds.
- Update session state machine to maintain `segments_served` counters and beacon event history.
- Wire beacon firing into manifest and segment serving flows so beacons fire as segments are fetched.
- Add control endpoint for manual mid-roll trigger (simulating SCTE-35).

## Capabilities

### New Capabilities
- `dynamic-ad-pod-loading`: Load active ad pods from VAST-fetched and conditioned ad sources, per session state.
- `beacon-tracking-and-firing`: Server-side beacon URL firing at quartile progress (0%, 25%, 50%, 75%, 100%) with async HTTP.
- `ad-pod-segment-progress`: Track segments served per rendition and calculate quartile thresholds for beacon firing.
- `mid-roll-trigger-control`: HTTP endpoint for manual ad break insertion with fresh VAST fetch and conditioning.

### Modified Capabilities
- `session-manifest-splice-preroll`: Now accepts dynamic ad pods loaded from VAST/conditioning pipeline instead of hardcoded pre-roll placeholder.

## Impact

- Adds `beacon_firer.py` for async beacon URL firing orchestration.
- Updates `session_manager.py` to track segment progress and beacon history per session.
- Updates [manifest_builder.py](manifest_builder.py) integration to load dynamic ad pods instead of hardcoded references.
- Adds `routes/control.py` for mid-roll trigger endpoint.
- Modifies segment serving logic to fire beacons and update progress on each segment fetch.
- Session API expands with beacon/tracking event history visibility.
