# Original editor document lifetime boundary — 2026-11-20

## Actual outcome and source

Source commit: 5e936f2afa5f8fd371d1bef8b0521d9b8a3f20b6, based on immutable writer source/evidence 67a23f718548ee80dbb084e57933115a07601ea3. This tranche adds three production files, one original-target unit-test file, and a portable driver/fixture. It changes no existing tracked source, project, original action, rendering method, or prior unit declaration.

SentinelX job job_2e1e4562ced2 completed on 2026-11-20 at 11:01:22 UTC. The Swift 6 strict-concurrency Foundation build exited 0 in 34.406 seconds, with zero warnings/errors. Its executable completed 30/30 controls in 0.141 seconds. Four complete production/test files passed Swift 5 syntax parsing. Raw logs, exact projections, boundary doubles, commands and hashes are retained under raw/ and indexed by RAW_FILES.json. RESULT.json SHA256 is 786a89a5cc82c5a90499ce368a674fc72d75ff6430c997fa8ffc909c8e4880e5.

**Apple typechecking, the eight new Apple unit declarations, original editor rendering, Native UI, and annotation persistence are NOT_RUN.** The independent first-16 Apple workflow 44722898086 uses frozen workflow 11bfb0db / app 67a23f7; its result cannot establish this later ownership source. No CI was dispatched or changed by this tranche.

## Implemented boundary

EditorDocumentWriteOwner retains the actual prepared document and its original EditorPageObject on MainActor. Every admitted mutation rechecks the original prepared-document contract, byte-exact context/object/Space/version, open state, handling mode, and current canEditBlocks permission plus the lock flag. DocumentMode remains the original declaration without an added Sendable conformance.

DocumentOwnedTextService implements the existing TextServiceProtocol, forwarding all seven methods and their original argument/result values to the explicitly supplied service. It adds no native fallback or Factory replacement. DocumentOwnedLocalEventPublisher wraps all five existing local-event methods with the same owner. Read-only presentation toggling remains permitted; text/style/loading/general publication requires editable handling ownership.

Retirement stops new admissions synchronously. It does not cancel, undo or retry an operation already admitted before its await. A service can have applied its write before ownership, cancellation or permissions change. If that service returns successfully afterward, the wrapper reports completedWithoutOwnership with the concrete reason, instead of pretending no side effect occurred. Underlying service errors propagate unchanged.

An already admitted publication can also finish after retirement; its actual delivery remains observable. The owner retains every admitted operation until it returns. onDrained is called once only after retirement and complete drainage, with the callback cleared before invocation. Retirement never calls document.open, update, or close. The consumer must retire the owner explicitly; no consumer is introduced here.

## Actual coverage

The 30 controls execute the complete new owner and wrappers against the original protocol declarations and explicit held service/event probes:

- Seven original text operations, mixed Hebrew/English/emoji payloads, UTF-16 ranges, returned split identity, and lease release.
- Foreign context; changed object, Space, mode, open state, edit permission and lock state; read-only/history mode; byte-exact context and history version.
- Retirement while a service is actually held, refusal of subsequent calls, actual prior service completion, distinct post-completion ownership/cancellation/permission outcomes, and no retry.
- Once-only drainage, duplicate retirement, unchanged underlying error, cancellation before dispatch, and no automatic document lifecycle operations.
- All five original event kinds, foreign/retired publication rejection, permitted read-only toggle, and an actually held admitted publication that drains after retirement.
- Two owners sharing a service without sharing admission or retirement authority.

This is not a baseline-versus-candidate RED claim. These are positive and negative controls of the added boundary. The source-preservation checks separately retain the prior original assembly/action/event inverses; earlier successful controls are not counted again.

## Original target declarations

AnytypeTests/Markdown/EditorDocumentWriteOwnerTests.swift adds eight SwiftTesting declarations in EditorDocumentWriteOwnerTests. The original project already registers Sources and AnytypeTests via PBXFileSystemSynchronizedRootGroup; the new paths are outside its exception list. The existing project is byte-identical. TEST_DECLARATIONS.json lists all prior 16 and new 8 declarations, their exact source hashes, and their execution status. This establishes source membership, not Xcode discovery or execution.

The original MockBaseDocument remains unchanged. The portable fixture uses its own locked mutable document boundary and the original unchecked-Sendable document model convention. Original DocumentMode is compiled unchanged. ObjectPermissions is the complete original struct declaration; its derived initializer and actual live permission propagation are not qualified by the fixture. UIKit/Combine and protobuf dependencies use recorded explicit boundary doubles. The original editor's concrete Apple services, UI, Factory, account and middleware are not exercised.

## Remaining integration

This owner is not yet propagated by the prepared assembly or a real consumer. It checks current permissions, not a historical permission epoch: revoke-then-restore while an operation awaits is not detected by the wrappers alone. The prepared session must retire ownership on actual original permission/source/lifecycle revocation before consumer qualification; the 30 controls do not establish that integration. Remaining original block/table/pasteboard/object/undo/file/property/router services must be bound to the same document lifetime; routed sheets and callbacks require their own original ownership/lifecycle propagation. Existing native callers continue using their original default dependencies.

A future caller must supply the same owner to the actual text wrapper and local-event publisher, retire it explicitly, and retain admitted work through drainage. A late-success error is not safe permission to retry and is not proof of rollback. Full original-editor writer isolation, an importable EditorKit boundary, Maktabah embedding, rich annotation durability, live two-block editing, relaunch, and visibility/performance acceptance remain open. No standalone replacement editor, global Save hook, external account change, or capability enable is added.

Root independently reviewed all three source files at 5e936f2a without finding a blocker in this stated scope, and explicitly identified the permission-history boundary above. That was source review, not another test execution.
