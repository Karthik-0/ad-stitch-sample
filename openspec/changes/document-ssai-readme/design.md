## Context

The SSAI POC has been fully implemented across multiple components (session manager, VAST client, ad conditioner, manifest builder, segment serving, beacon firing, mid-roll triggering). The TechSpecs document contains comprehensive technical design covering architecture, data flows, models, and configuration. However, no operational guide exists for developers to actually run the system locally.

Without clear documentation, new users face significant friction:
- Manual discovery of setup prerequisites
- Unclear command sequences and ordering
- No validation procedures to confirm correct setup
- Ad hoc troubleshooting without reference

## Goals / Non-Goals

**Goals:**
- Provide a complete, linear setup guide from zero to running system
- Include OS-specific instructions (macOS/Linux with brew/apt variations)
- Document all 6 core API endpoints with curl examples
- Provide end-to-end test procedures (pre-roll, mid-roll, beacon verification)
- Include quick reference for architecture, data flows, and file layout
- Enable new developers to onboard within 30 minutes
- Support both experienced and junior engineers with appropriate detail levels

**Non-Goals:**
- Deep technical architectural explanation (covered by TechSpecs)
- Production deployment guidance (beyond POC scope)
- Code-level implementation details (belong in code comments)
- Advanced troubleshooting (covered by TechSpecs § 12)
- Performance tuning or optimization guides

## Decisions

1. **Organization Structure**: Linear narrative from prerequisites → setup → operation → testing
   - Rationale: New users follow a single path without backtracking
   - Alternative considered: Topic-based sections (Setup, API, Testing) — rejected for non-linear discovery

2. **Audience Split**: Two-tier content with "Quick Start" (5 min setup) and "Full Setup" (detailed explanation)
   - Rationale: Experienced users can skip details; new users get full context
   - Alternative: Single depth for all — rejected for readability

3. **Code Examples**: All procedures use `curl` for API calls, shell commands for setup
   - Rationale: No external tool dependencies; portable across environments
   - Alternative: Postman collection — rejected (adds dependency, duplicates curl examples); Python client — rejected (out of scope)

4. **Verification Steps**: After each major section, include success criteria (what output should you see?)
   - Rationale: Developers can self-diagnose setup issues without asking for help
   - Alternative: Single section at end — rejected (feedback too delayed)

5. **File References**: Use exact paths starting from `ssai-poc/` root, with mkdir commands before first use
   - Rationale: Prevents "file not found" errors from missing directories
   - Alternative: Assume directory structure exists — rejected (high friction for first-time users)

6. **Markdown Format**: Use GitHub-flavored Markdown with tables for endpoint reference, code blocks for examples, clear heading hierarchy
   - Rationale: Renders well on GitHub, GitLab, and local viewers; supports all content types
   - Alternative: HTML or PDF — rejected (maintenance burden, less portable)

## Risks / Trade-offs

- **Command Copy-Paste Risk**: If a curl command is malformed in docs, users will copy-paste it and see failures
  - Mitigation: Test all commands before publishing; include inline comments explaining parameters

- **OS-Specific Divergence**: macOS and Linux have different package managers and paths
  - Mitigation: Use conditional sections (e.g., "On macOS: `brew install ...`"; "On Linux: `apt-get install ...`")

- **Screenshot Aging**: Screenshots of player UI or logs may become outdated after code changes
  - Mitigation: Avoid screenshots; use text descriptions instead (more maintainable)

- **Scope Creep**: Documentation could expand to cover edge cases, advanced debugging, deployment
  - Mitigation: Link to existing docs (TechSpecs) for deep dives; restrict README to core operational flow

- **Maintenance Burden**: As code evolves, endpoint paths, response formats, or config defaults may change
  - Mitigation: Mark sections "Last Updated [date]"; include CI check to validate curl examples

## Migration Plan

**Phase 1 (Initial):**
- Create `ssai-poc/README.md` with Quick Start and Full Setup sections
- Include all 6 core endpoint examples with expected outputs
- Add section for pre-roll, mid-roll, and beacon verification

**Phase 2 (Rollout):**
- Link from main project README to `ssai-poc/README.md`
- Gather feedback from first 2–3 new developers
- Refine based on pain points

**Phase 3 (Maintenance):**
- After each code change, update README sections that reference changed paths/APIs
- Every 3 months, run through setup guide end-to-end to catch stale instructions

**Rollback:** No rollback needed (documentation-only change); old version stays available in git history.

## Open Questions

1. **Should README include Docker Compose OSSRS setup, or assume it's pre-running?**
   → Decision: Include full docker-compose.yml in appendix, provide start/stop commands

2. **How deep should the troubleshooting guide be without duplicating TechSpecs?**
   → Decision: Cover common startup issues (FFmpeg not found, port already in use, VAST fetch timeout); link to TechSpecs § 12 for architectural concerns

3. **Should we include sample `.env` or config override instructions?**
   → Decision: Yes — include config.py reference and example of overriding VAST tag via endpoint parameter

4. **Do we need a section on how to connect external VAST sources, or just Google samples?**
   → Decision: Cover only Google samples in main README; provide extensibility note pointing to `vast_client.py` for custom tags
