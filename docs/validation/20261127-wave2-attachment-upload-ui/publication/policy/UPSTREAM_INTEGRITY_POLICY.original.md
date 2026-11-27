# Pinkha / Anytype — Clean Upstream Integrity Policy

**MANDATORY owner directive: 2026-10-22.** This policy applies to all Codex, Antigravity, Claude and other coding agents across actively developed Pinkha branches. It supplements (and never relaxes) original Anytype rules, especially CLAUDE.md's **NEVER commit/stage without explicit user request**, no destructive Git operations and the current Heart/protobuf freeze.

## Authority and provenance

- Original project: https://github.com/anyproto/anytype-swift (upstream **develop**, not Maktabah's main). Confirm fresh SHA before any work; do not rely on a stale remote-tracking ref.
- Downstream fork: https://github.com/davidpovarsky/anytype-swift — Pinkha/Torah adaptations and TorahInspectorKit.
- Original Anytype app, design system, Object APIs, block editor, services, Modules, SwiftPM dependencies, middleware and generated code remain **upstream-owned** even if our fork previously changed them or upstream renamed them.
- Imported Heart, protobuf, middleware, CRDT or Go and generated protocol/source are additionally **FROZEN**. No modifications, regeneration, schema adjustment, sync behavior change or migration without explicit separate owner approval and protocol/compatibility review. Existing T2 multi-device sync remains BLOCKED.
- Previously modified upstream files are **LEGACY_UNREVIEWED**, never implied permission for new changes. No ad hoc modifications to upstream classes, content duplication, mass replacement or "just one line" registration changes.

## Mandatory separation — real architecture, not just folders

Downstream behavior must live in isolated Pinkha/TorahInspectorKit packages, service adapters, protocols, wrappers, coordinators, native extension views, repositories or explicitly downstream-owned composition roots. Prefer original Anytype's public block/selection, ObjectShow/ObjectSetDetails, middleware and subscription contracts. Do not insert Torah/persistence/inspector behavior directly into upstream source as a shortcut.

For any unavoidable change to upstream-owned file, STOP and supply: exact path + diff hunk; real upstream SHA; why a downstream-only adapter cannot solve it; expected original behavior; tests/rollback; explicit prior OWNER approval. A developer, integrator or QA agent may not self-authorize exceptions. Track approved exceptions in docs/architecture/UPSTREAM_EXCEPTION_REGISTER.md; no historical approval should be inferred.

**Preferred integration order:** official upstream extension point -> downstream protocol adapter -> downstream host/wrapper/composition -> isolated Swift extension -> specifically owner-approved narrow hook.

**Frozen/preserved Pinkha features:** original Anytype design language; native iPadOS reader hierarchy and trailing inspector; semantic word-selection anchors; Torah associations; Quote/Note blocks; one-device persistence/serial writer; Space isolation; offline/disposable test Spaces. Never alter user Spaces during test runs.

## Pre-edit gate

1. Confirm actual worktree/branch/HEAD, dirty status, upstream/develop HEAD/merge-base and *all* target file origins (including moved files). NEVER automatically switch branch based on upstream CLAUDE's Linear workflow; protect user's existing branch/worktree.
2. Classify every proposed edit: UPSTREAM_OWNED / DOWNSTREAM_OWNED / VENDORED_UPSTREAM / SHARED_INTEGRATION / UNKNOWN. UNKNOWN blocks edits.
3. Record path, SHA, proposed behavior, downstream alternative, owner approval and focused regression tests; obtain explicit owner approval **before touching original source**, not after.
4. Read frozen scope, team policy, DESIGN_LANGUAGE.md and any existing project integration RFCs. An old branch or clean compiler does not establish correctness.
5. No automatic commit, stage, push, workflow dispatch or release. A user request to "update the repo policy in branches" explicitly permits documentation-only commits/pushes scoped to those branches; this is not permission to change application code, protected default develop or production Heart.
6. Validate source lineage and changes using Git before completion; an automated clean-upstream CI gate is NOT yet installed, so do not falsely claim automated enforcement or a green runtime suite.

## Upstream sync protocol

Only on explicit owner request, on an isolated branch/worktree pinned to upstream/develop.
- Inventory actual upstream changes, fork divergences, renamed/removed sources, build targets, localization/codegen and ownership of packages.
- Preserve true ancestry; no blanket `ours`/`theirs`, unreviewed tree-copy, destructive reset, silently reverting upstream bug fixes, or treating an archive as functional verification.
- For each conflict and every non-conflicting behavior crossover, inspect base + ours + theirs + final; document upstream intent, Pinkha intent, resolution, evidence, actual tests and OPEN/VERIFIED state.
- Preserve original Anytype UI and behavior while layering Pinkha integrations. Generated source changes MUST go through verified upstream-approved generator inputs; do not hand-edit generated code.
- Compare file inventories and downstream extensions across parents; check app and middleware version contract, Swift/Go/protobuf boundaries, DB migration, offline sync, shared packages and build configuration.
- DO NOT call integration DONE while device/functional regressions are unverified.

## Regression acceptance matrix — report each as PASS / FAIL / NOT_RUN / BLOCKED

- Original Anytype functionality: Home and object hierarchy, collections/sets, editor, blocks, selection/copy/paste, navigation, search, history, settings, Space switching and local-first behavior.
- Native Pinkha UI: iPad screen hierarchy, sheet detents, rotation, pointer, keyboard, RTL, localization and original visual consistency.
- Torah integrations: inspector open/close, real selected-word anchors, source links, commentaries, persistent notes/quotes and cross-view refresh.
- Data safety: ObjectShow/ObjectSetDetails readback, single-writer mutation serialization, no duplicate writes, no wrong-Space records, undo/replay, migrations and offline relaunch; no mutation of real personal Spaces during tests.
- Heart/protobuf/CRDT: contracts remain frozen; multi-device T2 sync BLOCKED absent specific RFC approval and verified cross-device evidence.
- Performance: 2k+ relationship loads, no MainActor DB stalls, cancellation, thread/actor safety and listener cleanup.
- Upstream sync: original feature parity and every Pinkha-specific behavior after rebase/merge.
- Builds/CI/TestFlight: only with explicit owner request; compile/sign/archive/TestFlight success does not validate user behavior.
- For each scenario record exact SHA, expected/actual, device/OS, tests, screenshots/logs and remaining risks. Physical iPad acceptance is NOT implied by simulator.

## Permissions, responsibility and closure

Eitan: boundary and exception review. Noam: downstream-first code changes + tests. Maya: original Anytype native UI parity. Tomer: lineage, hunk-level sync and rollback. Roni: adversarial functional/device QA and honest open gates. Yael: real upstream reference/SHA. Dana: Heart/protobuf/data/security/Space isolation.

**Asana is read-only unless the owner expressly requests an update/sync.** Role handoff/QA completion does not grant write permissions. No automatic subagents unless explicit TEAM request. Never amend branch default, merge PR, alter signing, publish releases or touch personal Spaces without owner approval.

Every completion report must include branch/SHA, upstream SHA, classified changed files, exact approved exceptions (or none), conflicts and tests actually performed, unverified cases, rollback and explicit owner gate.

**Invariant: Pinkha-specific logic stays outside the original Anytype implementation; future upstream/develop merges must not require reconstructing Pinkha features from mixed upstream source edits.**
