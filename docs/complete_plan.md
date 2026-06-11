# SENTINEL Complete Execution Plan

## Purpose

This document is the working plan for the SENTINEL hackathon submission. It describes what is already in place, what still needs to be built, the order of execution, and the deliverables required to ship a strong judge-facing demo and six distinct track submissions.

## Current State

The repository already includes the core security and orchestration foundations:

- `agent/model_armor.py` for outbound and inbound safety checks.
- `agent/jsonrpc/client.py` with signed JSON-RPC requests and audit logging.
- `agent/schemas/handshake.py` for shared stage context.
- `agent/orchestrator.py` with the multi-stage healing flow and approval gate logic.
- `tests/test_security.py` covering the security and schema pieces.
- `docs/deployment.md` with Cloud Run and Workload Identity guidance.
- `.github/workflows/ci.yml` for CI.

The next work is about packaging this into a polished product, splitting it into track-specific submissions, and finishing the UI/demo story.

## Target Outcome

Ship a submission set that has these properties:

1. A clear core architecture that is reusable across tracks.
2. Six distinct public submissions, one per hackathon partner track.
3. A polished, judge-friendly UI that shows the self-healing flow in a live, understandable way.
4. A secure audit trail, signed mutating JSON-RPC calls, and shared schema discipline.
5. A demo path that works with mocks first and can be switched to live partner integrations as secrets become available.

## Workstreams

### 1. Core Architecture and Repo Restructure

Goal: turn the current repository into a clean core plus track-specific layout without losing the working code.

Planned structure:

- `core/` for shared orchestration logic, schemas, security, adapters, and utilities.
- `tracks/` for track-specific packaging and README variants.
- `demo/` for mock services and reproducible demo scenarios.
- `ui/` or `ui/cockpit/` for the judge-facing interface.
- `scripts/` for publishing, packaging, and repo export automation.

Tasks:

- Move reusable logic into a stable shared layer.
- Keep MongoDB-specific code easy to identify and preserve it as the hero track.
- Add a publishing script that can generate six clean track repos with distinct branding and README content.
- Keep imports and references consistent after the restructure.

Deliverables:

- Shared core package layout.
- Track folder skeletons.
- Publish script.
- Updated docs that explain the new repo shape.

Acceptance criteria:

- The shared core code runs without depending on a track folder.
- Each track folder has unique documentation and positioning.
- The publish script can produce a clean per-track output without manual edits.

### 2. Security, Trust, and Audit

Goal: keep the orchestration safe and traceable.

Tasks:

- Keep Model Armor as the safety layer for outbound and inbound payload checks.
- Preserve signed JSON-RPC requests for every mutating action.
- Continue writing audit events in a machine-readable format.
- Keep the `Handshake` schema as the only shared context object between stages.
- Make stage approvals explicit for destructive or schema-changing actions.

Deliverables:

- Stable policy checks around request and response handling.
- Audit log format documentation.
- Clear approval flow for Stage 4 or any schema mutation.

Acceptance criteria:

- Mutating actions are signed.
- Audit entries include enough data to reconstruct the action.
- Schema changes require the intended approval gate.

### 3. Live Partner Integrations

Goal: wire the six partner tracks to real services when credentials are available.

Tracks to support:

- MongoDB
- Arize
- Elastic
- Fivetran
- GitLab
- Dynatrace

Tasks:

- Create or finish adapter wrappers for each partner.
- Read secrets from environment variables or Secret Manager.
- Make every adapter work against mock mode first.
- Keep live mode behind a simple configuration switch.
- Add failure handling for missing secrets and disabled APIs.

Deliverables:

- One adapter per partner.
- Mock-compatible interfaces.
- Live integration configuration docs.

Acceptance criteria:

- The app can run in mock mode without cloud credentials.
- When secrets are present, the real partner calls work without code changes.

### 4. SRE Control Cockpit UI

Goal: build a judge-facing interface that makes the self-healing story obvious.

Primary UI concept:

- A central flow visualization showing the six stages.
- A clear status panel for check, ask, and fix decisions.
- A human-in-the-loop approval area for schema or remediation actions.
- A trace panel that shows payloads, audit events, and stage outputs.

Planned UI behavior:

- Show stage health at a glance.
- Animate the flow when a remediation step is running.
- Make failures legible rather than hidden.
- Highlight the current stage and the next action.
- Support a mock demo mode with deterministic data.

Deliverables:

- UI shell.
- Stage timeline or pipeline view.
- Detail panel for one stage at a time.
- Approval controls.
- Demo-ready mock data mode.

Acceptance criteria:

- A judge can understand what the system is doing in under a minute.
- The UI works on desktop without requiring a cloud backend.
- The demo path looks complete even when powered by mocks.

### 5. Demo and Storytelling

Goal: make the submission easy to understand and easy to present.

Tasks:

- Create a repeatable demo script.
- Provide a one-command local demo.
- Make the hero path obvious: detect, inspect, validate, patch, quarantine, report.
- Keep track-specific versions distinct enough to satisfy submission rules.

Deliverables:

- Demo runner.
- Scenario scripts.
- Clean README per track.
- Short presentation notes.

Acceptance criteria:

- The demo can be run from a fresh checkout with minimal setup.
- The storyline is visually and narratively strong.

### 6. Deployment and Operations

Goal: make the project credible as a production-ready system.

Tasks:

- Keep Cloud Run deployment steps documented.
- Use Workload Identity and Secret Manager instead of hardcoded secrets.
- Preserve CI checks for every important change.
- Add any needed runtime config for the UI and orchestrator.

Deliverables:

- Deployment guide.
- CI workflow.
- Environment variable reference.
- Secret handling guidance.

Acceptance criteria:

- The deployment path is documented and reproducible.
- No secrets are committed to the repository.

## Phase Plan

### Phase A: Restructure and Package the Core

Output:

- Shared core layout.
- Track scaffolding.
- Publishing script skeleton.

Definition of done:

- The shared code is organized cleanly enough to be copied into track-specific outputs.

### Phase B: Build the SRE Control Cockpit

Output:

- UI shell.
- Stage flow visualization.
- Approval and trace panels.

Definition of done:

- The UI can demonstrate the system flow without depending on live partner services.

### Phase C: Wire Live Partners One by One

Output:

- Partner secrets and adapters connected.
- Fallback to mocks remains available.

Definition of done:

- Each partner can be enabled independently without breaking the demo.

### Phase D: Publish Track Variants

Output:

- Six separately packaged submissions.
- Unique README and positioning per track.

Definition of done:

- Each track repo looks intentional and not like a copy-paste of the others.

### Phase E: Final Hardening

Output:

- Final CI pass.
- Documentation cleanup.
- Demo rehearsal.

Definition of done:

- The final repo set is ready to hand to judges.

## Track-Specific Submission Strategy

Each submission should share the same core engine but present a different story and top-level emphasis.

### MongoDB Hero Track

Focus:

- Schema continuity.
- Safe validation changes.
- Quarantine and report flow.

Primary message:

- SENTINEL protects live MongoDB writes without stopping traffic.

### Arize Track

Focus:

- Cognitive assessment.
- Trace scoring.
- Guardrail tuning.

Primary message:

- SENTINEL monitors AI behavior and learns from remediation traces.

### Elastic Track

Focus:

- Log triage.
- Stack trace extraction.
- Root-cause synthesis.

Primary message:

- SENTINEL turns log noise into structured incident intelligence.

### Fivetran Track

Focus:

- Downstream pipeline alignment.
- Connector recovery.
- Schema drift tolerance.

Primary message:

- SENTINEL keeps data pipelines healthy after schema changes.

### GitLab Track

Focus:

- Branch creation.
- MR generation.
- Automated remediation evidence.

Primary message:

- SENTINEL connects incident response to code change workflows.

### Dynatrace Track

Focus:

- Alert ingestion.
- Service isolation.
- Signal-to-action routing.

Primary message:

- SENTINEL reacts immediately to live service incidents and drives the recovery workflow.

## Recommended Execution Order

1. Lock the core package boundaries and the publish strategy.
2. Finish the UI shell and demo mode.
3. Keep the mock path fully working.
4. Add live integrations one partner at a time.
5. Generate the six track variants.
6. Rehearse the demo and verify the final packaging.

## Risks and Dependencies

- Live partner wiring depends on secrets being present in Secret Manager.
- A polished UI depends on stable mock data and stage outputs.
- Publishing six repos depends on the shared core being separated cleanly first.
- Any new schema or audit format should be versioned to avoid breaking tests or docs.

## Definition of Done

The project is complete when all of the following are true:

- The core architecture is organized and documented.
- The UI can show the full self-healing flow clearly.
- The demo runs in mock mode end-to-end.
- Live partner integrations can be enabled without rewriting the app.
- Six separate track submissions can be published from the same source.
- CI passes and deployment guidance is present.

## Notes for Future Updates

- Keep this file in sync with the actual repo structure as the project evolves.
- Add implementation checkboxes under each phase when work starts.
- If the judges request a narrower story, trim the track-specific sections without changing the shared core.