## Why

The SSAI POC system is fully implemented but lacks clear documentation on how to run it and use it. Developers and testers need step-by-step setup instructions, local development guidance, endpoint reference, and testing procedures to onboard quickly and validate the system. This documentation is critical for reproducibility, debugging, and handoff to production teams.

## What Changes

- **New README.md**: Complete setup and operational guide including:
  - Prerequisites and environment setup
  - Step-by-step local deployment (OSSRS, FFmpeg transcoding, stitcher startup)
  - How to stream live content from OBS
  - API endpoint reference with examples
  - Creating and managing sessions
  - Triggering pre-roll and mid-roll ads
  - Verifying beacon firing
  - Browser testing (hls.js & Safari)
  - Architecture overview diagram
  - Troubleshooting guide
  - Links to TechSpecs for deeper design details

## Capabilities

### New Capabilities
- `ssai-operational-guide`: Documentation covering deployment, operation, testing, and troubleshooting of the SSAI POC system

### Modified Capabilities
<!-- No existing capabilities are being modified -->

## Impact

- **Users**: Developers can now quickly spin up local environment without manual trial-and-error
- **Docs**: Centralizes operational knowledge currently scattered across TechSpecs
- **Testing**: Testers have clear procedures to validate pre-roll, mid-roll, beacons, and multi-session independence
- **Onboarding**: New team members can follow step-by-step guide to understand and operate the system
