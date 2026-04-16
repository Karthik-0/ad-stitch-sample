## 1. Foundation & Structure

- [x] 1.1 Create initial ssai-poc/README.md structure with sections: Setup, API Reference, Testing, Troubleshooting, Architecture, Links
- [x] 1.2 Gather content from TechSpecs § 4 (directory layout), § 9 (local setup), § 10 (requirements.txt), § 11 (validation)
- [x] 1.3 Create a checklist in the README to track setup progress (for operators to mark off steps)

## 2. Setup Section — Prerequisites & OSSRS

- [x] 2.1 Document prerequisites: Python 3.11+, FFmpeg (with libx264), Docker, OBS Studio (optional)
- [x] 2.2 Add OS-specific installation instructions for macOS (brew) and Linux (apt-get)
- [x] 2.3 Document docker-compose.yml for OSSRS and include full file in appendix
- [x] 2.4 Add "Start OSSRS" command: `docker-compose up -d`
- [x] 2.5 Add verification step: curl http://localhost:1985/api/v1/servers to confirm OSSRS is ready
- [x] 2.6 Document OBS Studio RTMP push to rtmp://localhost:1935/live/livestream (with screenshot reference or terminal output)

## 3. Setup Section — FFmpeg Transcoding

- [x] 3.1 Create storage/live directory structure documentation
- [x] 3.2 Document complete FFmpeg command for multi-rendition HLS transcoding (from TechSpecs § 9.3)
- [x] 3.3 Add explanation of FFmpeg parameters: bitrate per rendition, GOP size (48), frame rate (24), audio config (44.1kHz, stereo), codec (libx264)
- [x] 3.4 Add verification step: check that .m3u8 files and .ts segments are being created in storage/live/
- [x] 3.5 Document how to stop FFmpeg (Ctrl+C) and troubleshooting for "Address already in use" RTMP port

## 4. Setup Section — Stitcher Startup

- [x] 4.1 Document creating Python virtual environment or conda environment
- [x] 4.2 Document `pip install -r requirements.txt` with expected packages (fastapi, uvicorn, httpx, pydantic)
- [x] 4.3 Document starting stitcher: `uvicorn main:app --host 0.0.0.0 --port 8080 --reload`
- [x] 4.4 Add verification step: `curl http://localhost:8080/health` should return 200 OK
- [x] 4.5 Document port binding and how to override with `--port 8081` if 8080 is in use

## 5. API Reference — Endpoint Documentation

- [x] 5.1 Create section: "API Endpoints" with table showing all 6 endpoints (method, path, purpose)
- [x] 5.2 Document POST /session/new: curl command, request body schema, response example with session_id and master_url
- [x] 5.3 Document GET /session/{sid}/master.m3u8: curl command, response format, example variant URIs
- [x] 5.4 Document GET /session/{sid}/{rendition}.m3u8: curl command, explanation of ad splice format (#EXT-X-DISCONTINUITY)
- [x] 5.5 Document GET /session/{sid}/seg/live/{filename}: curl command, explain validation, 404 handling
- [x] 5.6 Document GET /session/{sid}/seg/ad/{pod_id}/{creative_id}/{rendition}/{n}.ts: curl command, explain beacon triggering
- [x] 5.7 Document POST /session/{sid}/trigger-ad-break: curl command with duration_hint, expected response, mid-roll timing

## 6. Testing — Pre-Roll & Mid-Roll

- [x] 6.1 Create "Testing" section with subsections for each test scenario
- [x] 6.2 Document pre-roll validation test: create session with preroll=true, fetch master.m3u8, open in hls.js, observe ad before live content
- [x] 6.3 Document mid-roll trigger test: start playback, wait 30sec, POST trigger endpoint, verify ad appears within 10sec, observe beacon logs
- [x] 6.4 Document test player setup: create static/test-player.html with hls.js integration (or link to hls.js demo)
- [x] 6.5 Add expected output/behavior for each scenario (what the tester should see)

## 7. Testing — Beacon & Multi-Session

- [x] 7.1 Document beacon verification procedure: enable stitcher debug logging, create session with ad, fetch segments, grep logs for "quartile" or "beacon"
- [x] 7.2 Show example log lines to look for at 25%, 50%, 75%, 100% quartiles
- [x] 7.3 Document multi-session independence test: create 2 sessions, trigger ad on session 1 only, verify session 2 playback unaffected
- [x] 7.4 Explain how to check ad_state for each session via GET /session/{sid}/state endpoint (if available)

## 8. Testing — Browser Compatibility

- [x] 8.1 Document testing in Safari native HLS: open master.m3u8 URL directly in Safari URL bar, observe native playback
- [x] 8.2 Document testing in hls.js: use https://hlsjs.video-dev.org/demo/, paste master.m3u8 URL, observe playback with debug console
- [x] 8.3 Explain how to check browser console for errors vs expected logs
- [x] 8.4 Document expected behavior for discontinuity transitions and rendering across browsers

## 9. Troubleshooting Guide

- [x] 9.1 Create troubleshooting section for: "FFmpeg: command not found" — install via brew/apt, verify libx264
- [x] 9.2 Add troubleshooting for: "Address already in use" — identify process with lsof, kill or change port
- [x] 9.3 Add troubleshooting for: "VAST fetch timeout" — verify network, test VAST URL with curl
- [x] 9.4 Add troubleshooting for: "No .ts files generated" — check RTMP stream, FFmpeg errors, disk space
- [x] 9.5 Add troubleshooting for: "Player shows black screen" — check logs for 404, verify manifest URLs, CORS checks
- [x] 9.6 Link to TechSpecs § 12 (Known Limitations) and § 14 (References) for deeper investigation

## 10. Architecture & Quick Reference

- [x] 10.1 Create "Architecture Overview" section with text description or ASCII diagram of data flow
- [x] 10.2 Create "Component Summary" table: SessionManager, AdConditioner, ManifestBuilder, BeaconFirer, SegmentServer responsibilities
- [x] 10.3 Create "File Layout" section with directory tree of ssai-poc/ with brief annotations
- [x] 10.4 Add "Data Flow: Pre-Roll" numbered sequence (from TechSpecs § 2.2)
- [x] 10.5 Add "Configuration Reference" table listing key config.py constants: RENDITIONS, SEGMENT_DURATION, FRAME_RATE, VAST_TAG_SINGLE_LINEAR
- [x] 10.6 Document how to override config (e.g., custom VAST tag via endpoint parameter)

## 11. Links & References

- [x] 11.1 Add "Further Reading" section with links to: TechSpecs document, models.py, session_manager.py, vast_client.py
- [x] 11.2 Link TechSpecs § 6 for data models, § 7 for component specs, § 2 for architecture
- [x] 11.3 Link HLS spec (RFC 8216), VAST spec (IAB), Google IMA docs for extended learning
- [x] 11.4 Add link to hls.js demo, Apple HLS guide
- [x] 11.5 Document git repo structure: where to find demo source, streaming scripts, Docker configs

## 12. Review & Polish

- [x] 12.1 Test all curl commands end-to-end: create session, fetch manifest, open in player, trigger ad
- [x] 12.2 Review markdown formatting: headers, code blocks, tables, links render correctly
- [x] 12.3 Verify all file paths are correct (ssai-poc/..., storage/..., openspec/...)
- [x] 12.4 Review for clarity: read as if you've never seen the code before, ask "is this clear?"
- [x] 12.5 Check for typos, broken links, missing sections
- [x] 12.6 Ensure tone is consistent (friendly, technical, actionable)
- [x] 12.7 Add "Last Updated" date and version number at top of README
- [ ] 12.8 Commit README.md and docker-compose.yml to git; update main project README with link to ssai-poc/README.md
