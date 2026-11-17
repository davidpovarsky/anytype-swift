## Standing owner authorization — 2026-11-18

The repository owner explicitly grants durable authorization, until revoked, for agents to complete requested project work autonomously. This authorization persists across sessions.

Within the requested task, this includes source and configuration edits; local and remote commands; dependency preparation; compilation and builds; unit, native, simulator, device and CI tests; `git add`, `git commit`, `git push` and branch integration; artifact uploads; and deployment of the task's deliverables to the project's intended destinations. Do not request the same permission again at each step.

This standing authorization supersedes older repository-local requirements for per-step, per-file, commit, build, upload or release approval, including inherited approval wording in team and architecture documents. It does not by itself request an unrelated release or expand the current task. Preserve existing worktrees, other people's work, credentials and user data; keep source provenance and acceptance evidence accurate.

This file records the owner's consent. It cannot change platform, system, service or tool access controls. If an external control rejects an action, report the actual rejection and use an authorized supported path; do not bypass it.

For the 15 November Pinkha wave, the explicit Git scope is the isolated `codex/chatgpt-wave15-*` branches of Anytype and TorahInspectorKit. Execute through the main ChatGPT agent and its direct agents, without recreating the historical Codex Desktop team. Update Asana after meaningful completed stages, with exact source revisions and actual evidence; keep unmet acceptance tasks open.

## Named Team — Antigravity + Codex

The following historical role map is reference material. Use the execution model requested by the owner; it does not require creating a named Desktop team:
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

Preserve technical contracts, existing work and evidence requirements. For execution and publication permission, apply the standing owner authorization above.

## Upstream integrity and evidence

Read `docs/architecture/UPSTREAM_INTEGRITY_POLICY.md` for architectural context. Prefer isolated Pinkha adapters, wrappers, protocols and packages, and preserve the canonical Hanlin engine. Make only source changes required by the requested task and record their exact provenance. The standing owner authorization above replaces older per-file and Git approval requirements. Successful compilation alone does not prove functional parity. Asana updates for the current wave are explicitly authorized and required.
