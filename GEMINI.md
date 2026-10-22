# Antigravity Project Instructions

This repository is configured for the persistent named AI team across Antigravity and Codex:
- **איתן (eitan)**: Architecture
- **נועם (noam)**: Engineering
- **מיה (maya)**: Native UX & RTL
- **רוני (roni)**: Independent QA & Evidence
- **תומר (tomer)**: Integration & PRs
- **יעל (yael)**: Research & Schemas
- **דנה (dana)**: Security & Permissions

## Required Context Loading
For all substantive work, review:
- Root `AGENTS.md` and repository-specific guidance
- `docs/ai-team/TEAM.md`
- `docs/ai-team/PROJECT_ASSIGNMENTS.md`
- `docs/ai-team/ASANA_POLICY.md`
- Agent profiles under `.agents/agents/` and roles under `.agents/roles/`

Asana may be read proactively; writing requires an explicit user update/sync request, following `docs/ai-team/ASANA_POLICY.md`. All existing release gates, PR merges to main, and destructive actions require explicit owner approval.

## Mandatory clean-upstream and owner approval gate (2026-10-22)

Read `docs/architecture/UPSTREAM_INTEGRITY_POLICY.md` before implementation, integration or QA. Original Anytype upstream/develop, Heart, protobuf and generated code are read-only for Pinkha custom work unless the owner explicitly approves a specific file/hunk; legacy modifications are not authorization. Prefer isolated Pinkha adapters, wrappers, protocols and packages. Do not claim successful compilation proves functional parity. Asana is read-only unless the user explicitly asks to update/sync. Preserve all stricter original Anytype rules, including CLAUDE.md: no staging/committing without explicit user request.
