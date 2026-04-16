## ADDED Requirements

### Requirement: README provides step-by-step local setup

The system documentation SHALL provide a complete step-by-step guide for developers to set up the SSAI POC locally, from zero prerequisites to a running stitcher with streaming content.

#### Scenario: First-time setup on macOS
- **WHEN** developer follows the README setup section on macOS
- **THEN** they can install prerequisites, start OSSRS, launch FFmpeg transcoding, and start the stitcher without consulting external resources or running into missing tools

#### Scenario: First-time setup on Linux
- **WHEN** developer follows the README setup section on Linux
- **THEN** they can install prerequisites via apt-get, start OSSRS, launch FFmpeg transcoding, and start the stitcher without consulting external resources

#### Scenario: Verify OSSRS is running
- **WHEN** developer completes OSSRS setup
- **THEN** README includes a verification step (e.g., curl to health endpoint, netstat check, or browser URL) to confirm OSSRS is ready

#### Scenario: Verify FFmpeg transcoding is working
- **WHEN** developer starts FFmpeg transcoding from OBS RTMP stream
- **THEN** README includes verification steps (checking generated .m3u8 files, segment count, file sizes) to confirm transcoding is producing output

#### Scenario: Verify stitcher is running
- **WHEN** developer starts the FastAPI stitcher
- **THEN** README includes a verification curl command to /health endpoint that returns 200 OK

### Requirement: README documents all API endpoints with examples

The system documentation SHALL provide complete reference for all 6 core API endpoints, including method, path, request body (if applicable), and example curl commands with expected response format.

#### Scenario: Endpoint: POST /session/new
- **WHEN** developer reads endpoint reference section
- **THEN** they see exact curl command to create a session with `content_id: "demo"` and `preroll: true` parameters, plus example JSON response with `session_id` and `master_url`

#### Scenario: Endpoint: GET /session/{sid}/master.m3u8
- **WHEN** developer reads endpoint reference
- **THEN** they see curl command to fetch master manifest, with example output showing `#EXT-X-STREAM-INF` variants

#### Scenario: Endpoint: GET /session/{sid}/{rendition}.m3u8
- **WHEN** developer reads endpoint reference
- **THEN** they see curl command and explanation that this returns variant playlist with ad segments (if applicable) and live segments

#### Scenario: Endpoint: GET /session/{sid}/seg/live/{filename}
- **WHEN** developer reads endpoint reference
- **THEN** they see explanation and example showing how segments are served, content-type is video/mp2t, and 404 handling for non-existent segments

#### Scenario: Endpoint: GET /session/{sid}/seg/ad/{pod_id}/{creative_id}/{rendition}/{n}.ts
- **WHEN** developer reads endpoint reference
- **THEN** they see structure of ad segment URI with all parameters documented, and note that serving ad segments triggers beacon firing

#### Scenario: Endpoint: POST /session/{sid}/trigger-ad-break
- **WHEN** developer reads endpoint reference
- **THEN** they see curl command to trigger mid-roll ad break with optional duration parameter, plus expected response including pod_id, ad_count, and duration

### Requirement: README includes end-to-end testing procedures

The system documentation SHALL provide clear test procedures to validate pre-roll, mid-roll, beacon firing, and multi-session independence without requiring manual investigation of logs.

#### Scenario: Test pre-roll ad playback
- **WHEN** developer follows pre-roll test procedure
- **THEN** they create a session with preroll enabled, open master manifest URL in player, and instructions show what to expect (ad plays first, then transitions to live content)

#### Scenario: Test mid-roll trigger
- **WHEN** developer follows mid-roll test procedure
- **THEN** instructions show: start playback, wait 30 seconds, run trigger endpoint, and expect ad to appear within 10 seconds. Includes verification that playback resumes after ad.

#### Scenario: Verify beacon firing
- **WHEN** developer follows beacon verification procedure
- **THEN** instructions show how to check stitcher logs for beacon firing messages at correct quartile points (25%, 50%, 75%, 100%), with example log line to look for

#### Scenario: Test multi-session independence
- **WHEN** developer follows multi-session test procedure
- **THEN** instructions show: create 2 sessions, trigger ad only on first, verify second session playback is unaffected. Instructions explain expected behavior of independent ad_state per session.

#### Scenario: Browser compatibility testing
- **WHEN** developer follows browser testing procedure
- **THEN** instructions show how to test in hls.js (Chrome via demo page) and Safari native HLS player, with expected behavior in each

### Requirement: README includes architecture overview and quick reference

The system documentation SHALL provide a quick reference that helps developers understand the system layout, component responsibilities, and file structure without requiring deep study of TechSpecs.

#### Scenario: Architecture overview
- **WHEN** developer reads the overview section
- **THEN** they see a text or ASCII diagram showing: Player → Stitcher → (OSSRS + FFmpeg + VAST client + Ad Conditioner + Beacon Firer)

#### Scenario: Component responsibilities
- **WHEN** developer wants to understand what each service does
- **THEN** README includes a table or list of: SessionManager, AdConditioner, ManifestBuilder, BeaconFirer, SegmentServer with one-liner responsibilities

#### Scenario: File layout
- **WHEN** developer wants to find where code lives
- **THEN** README includes directory tree showing `ssai-poc/{main.py, models.py, session_manager.py, routes/*, storage/*}` with brief annotations

#### Scenario: Data flow for pre-roll
- **WHEN** developer wants to understand what happens when a session is created
- **THEN** README includes a numbered sequence (1. Player requests session, 2. Stitcher creates session and fetches VAST, 3. Ad is conditioned...) or refers to TechSpecs § 2.2

### Requirement: README includes troubleshooting guide for common issues

The system documentation SHALL provide diagnosis steps for common startup and operational issues without requiring users to dig into TechSpecs.

#### Scenario: FFmpeg command not found
- **WHEN** developer runs FFmpeg transcode and gets "ffmpeg: command not found"
- **THEN** README troubleshooting section explains: check if FFmpeg is installed via `which ffmpeg`, if not install via brew/apt, verify libx264 with `ffmpeg -version | grep libx264`

#### Scenario: Port already in use
- **WHEN** developer tries to start stitcher and gets "Address already in use" on port 8080
- **THEN** README explains: find what's using the port with `lsof -i :8080`, kill process or use different port via `--port` flag

#### Scenario: VAST fetch timeout
- **WHEN** developer creates session and stitcher logs show "VAST fetch timeout"
- **THEN** README explains: check internet connectivity, verify Google VAST tag URL is accessible via curl, check stitcher network config

#### Scenario: No segments generated by FFmpeg
- **WHEN** developer starts FFmpeg but no .ts files appear in storage/live/
- **THEN** README explains: verify RTMP stream is reaching OSSRS (check logs), verify FFmpeg output path is correct, check disk space, look for FFmpeg errors in console

#### Scenario: Player shows black screen / fails to load manifest
- **WHEN** developer opens master manifest URL in player and sees no content
- **THEN** README explains: check stitcher logs for 404 errors, verify master.m3u8 exists, check variant URLs in master manifest are reachable (curl each one), verify CORS if using hls.js

### Requirement: README links to deeper documentation and source code

The system documentation SHALL provide clear pointers to TechSpecs, code, and related resources for developers who need architecture details, implementation specifics, or advanced customization.

#### Scenario: Need architecture details
- **WHEN** developer wants to understand session state machine, ad conditioning pipeline, or manifest splicing
- **THEN** README provides link to TechSpecs § 2 (System Architecture) and § 7 (Component Specifications)

#### Scenario: Need to understand data models
- **WHEN** developer wants to understand Session, AdPod, ConditionedAd structures
- **THEN** README provides link to TechSpecs § 6 (Data Models) and points to models.py source code

#### Scenario: Need to customize VAST tag
- **WHEN** developer wants to use a different VAST source or debug VAST parsing
- **THEN** README provides pointer to vast_client.py, config.py VAST_TAG constant, and TechSpecs § 7.2 (VAST Client)

#### Scenario: Need to understand beacon firing
- **WHEN** developer wants to customize beacon firing, retry logic, or macro handling
- **THEN** README provides pointer to beacon_firer.py, TechSpecs § 7.6 (Beacon Firer), and notes about macro replacement

#### Scenario: Need to understand manifest modification
- **WHEN** developer wants to understand #EXT-X-DISCONTINUITY splicing or when ad_state transitions occur
- **THEN** README provides pointer to manifest_builder.py, TechSpecs § 7.4 (Manifest Builder), and data flow diagrams (TechSpecs § 2.2–2.3)
