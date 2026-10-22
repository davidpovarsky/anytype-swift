# Pinkha / Anytype — Branch Integration Manifest

**Historical T2-L Base:** `pinkha/torah-functional-ui-single-device-2026-10-18`. Current active worktrees include `pinkha/torah-associations-native-ux-persistence-localization-2026-10-20` and `pinkha/torah-inspector-full-ipad-trial-2026-10-20`. Always verify current Git HEAD and remote SHA before acting.  
**Setup & Coordination Branch:** `agent/team-orchestration-20261018` (PR #1)

## Active Work Branches (Targeted for Propagation)
- `pinkha/torah-functional-ui-single-device-2026-10-18` (Current development base)
- `agent/team-orchestration-20261018` (Draft setup PR)
- `pinkha/upstream-u10-validation-2026-10-18`
- `pinkha/torah-integration-t1-hardening`
- `pinkha/torah-integration-t2-unblock`

## Default Branch
- `develop` — Receives additive team documentation only without merging feature code.

## Audited Exceptions (Skipped Archival / Snapshot Branches)
- `pinkha/foundation-v1`
- `pinkha/hierarchy-home-v1`
- `pinkha/upstream-sync-2026-10-18` (Old snapshot)

## Future Branch Inheritance
Only branches actually descended from a commit containing these documents inherit them; independent branches need explicit propagation. Never assume policy presence. Older branches can be checked with `tools/ai-team/ensure-team.ps1 -Check`.

## Mandatory clean-upstream and owner approval gate (2026-10-22)

Read `docs/architecture/UPSTREAM_INTEGRITY_POLICY.md` before implementation, integration or QA. Original Anytype upstream/develop, Heart, protobuf and generated code are read-only for Pinkha custom work unless the owner explicitly approves a specific file/hunk; legacy modifications are not authorization. Prefer isolated Pinkha adapters, wrappers, protocols and packages. Do not claim successful compilation proves functional parity. Asana is read-only unless the user explicitly asks to update/sync. Preserve all stricter original Anytype rules, including CLAUDE.md: no staging/committing without explicit user request.