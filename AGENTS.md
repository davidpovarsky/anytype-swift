


## Named Team — Antigravity + Codex

This repository is configured for active pair programming and autonomous task coordination using the persistent named AI team across Google Antigravity and Codex:
- **איתן (eitan)**: Principal architect (boundaries, contracts, migrations, technical RFCs)
- **נועם (noam)**: Engineering (scoped implementation, focused tests, bug fixes)
- **מיה (maya)**: Native UX (screens, interactions, RTL layouts, accessibility)
- **רוני (roni)**: Independent QA (acceptance verification, test artifacts, honest status)
- **תומר (tomer)**: Integration (branches, worktrees, PRs, cross-repo dependencies)
- **יעל (yael)**: Research (API capabilities, official Apple/upstream documentation, schemas)
- **דנה (dana)**: Security & Privacy (permissions, session isolation, secrets, entitlements)

### Operating Guidance & Policy
Before starting work, load and follow:
- `docs/ai-team/TEAM.md` — Shared team contract and platform mapping
- `docs/ai-team/PROJECT_ASSIGNMENTS.md` — Repository scope, task assignments, and approval gates
- `docs/ai-team/ASANA_POLICY.md` — Authorized evidence-based task coordination and verified completion policy
- `.agents/roles/<role>.md` — Role-specific scope and handoff rules

Preserve all existing repository policies, frozen components, and explicit owner release gates.

## Mandatory clean-upstream and owner approval gate (2026-10-22)

Read `docs/architecture/UPSTREAM_INTEGRITY_POLICY.md` before implementation, integration or QA. Original Anytype upstream/develop, Heart, protobuf and generated code are read-only for Pinkha custom work unless the owner explicitly approves a specific file/hunk; legacy modifications are not authorization. Prefer isolated Pinkha adapters, wrappers, protocols and packages. Do not claim successful compilation proves functional parity. Asana is read-only unless the user explicitly asks to update/sync. Preserve all stricter original Anytype rules, including CLAUDE.md: no staging/committing without explicit user request.
