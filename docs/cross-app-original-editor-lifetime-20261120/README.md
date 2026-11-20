# Prepared original editor: document and host lifetime — 2026-11-20

## Actual result and source

Source commit: f395d053b1554109325af8fda422259e28477aef, parent 1c8058112d95cb1278f5746cc0ad3ae4565d0ddb. The isolated branch is codex/otzaria-original-editor-lifetime-20261120.

The actual Windows Swift 6 strict-concurrency fixture passed **43/43** controls on 20 November at 11:46:54 UTC (job_ae346e077c31). Compilation exited 0 in 28.641 seconds; execution exited 0 in 0.156 seconds. Nine complete production/test files passed Swift 5 syntax parsing. One fixture WeakMutability diagnostic is retained; it is printed twice in the compiler's annotated output. The original ownership fixture then passed **30/30** in job_0b2679e862c1 at 11:47:48 UTC, with compile/runtime exit 0 and five source parses. That original fixture is byte-identical to the parent.

**Apple typechecking, all 32 current original-target unit declarations, original SwiftUI/UIKit lifecycle, Native input and annotation persistence are NOT_RUN for this source.** The independent Apple16 run44722898086 is frozen to workflow11bfb0db/app67a23f7. Its outcome cannot qualify these later ownership/lifetime changes. No workflow, binary, signing, native runtime, project or fixture selection is changed here.

RESULT.json SHA256: c034538ae811ce1e786d283c0d41d9529dff9df952c608166f014551ce7cc072. ATTEMPTS.json and RAW_FILES.json bind every attempt, exact compiled projection, snapshot, command and log to raw-byte SHA256 and deterministic gzip SHA256. SOURCE_COMMIT.json and raw/source.patch.gz bind the actual source delta.

## Confirmed failure and repair

The first source draft invalidated a document generation before awaiting its original close RPC. This correctly retired an existing owner, but still made a new valid generation available while the original document continued reporting isOpened=true. A fresh prepared session could therefore dispatch another write during the close.

An independent source review identified this precise gap. Actual RED attempt2 compiled successfully and executed all 35 original controls: 34 passed, and only fresh_prepared_session_cannot_dispatch_while_original_close_is_awaiting failed. The target service actually received the disallowed new operation in that version. Attempt1 is preserved separately: it reached the intentional fixture failure, but stdout did not flush a usable JSON report, so it has zero verified counts. Attempt2 changes only durable report output, preserving the product and all 35 assertions.

EditorDocumentWriteLifetime now separates a valid generation from permission to admit a new owner. The actual BaseDocument starts unavailable. Its original close guard is unchanged; after that guard, beginClosing synchronously invalidates captured tokens and marks the source unavailable before the existing RPC awaits. One-use close leases keep even a new owner unavailable while any admitted close is pending. Lease completion, including failure, removes only that lease and never restores authority. A duplicate release cannot consume another close.

Only the original setupView completion can confirm an opened view, after its unchanged model update, subscription setup, isOpened assignment and triggerSync. Confirmation while a close is pending remains unavailable and is not replayed when the close later finishes. A later genuine setupView is required. The original close event also marks the source unavailable. At the original permission-loss assignment, the lifetime invalidates before replacing canEditBlocks. This makes observed permission revoke-then-restore permanently stale for a retained owner.

The original close service, error propagation, conditional guard and isOpened=false order remain unchanged. A failed close still propagates its actual error and leaves the original document state as before; the new prepared authority safely stays unavailable until a subsequent authoritative open confirmation. It does not retry or infer successful recovery.

Eight new controls extend the preserved 35 to 43: unavailable initialization, overlapping closes, one-use release, confirmation after complete drainage, actual setupView during a pending close, rejection of replayed earlier open confirmation, fresh admission after a later setupView, and failure without authority renewal or RPC retry.

## Exact document, assembly and host

The new PreparedEditorPageSession requires an actual BaseDocumentProtocol & EditorDocumentWriteLifetimeProviding. It cannot silently fall back to current-state-only validation. It captures the original object/Space/mode and exact lifetime source, adds a private host lifetime, and assembles the original TextServiceHandler with DocumentOwnedTextService and DocumentOwnedLocalEventPublisher sharing the same owner. Other explicitly supplied service instances remain the same references; their existing contracts are not represented as qualified writer isolation.

The prepared assembly overload calls the existing prepared-document/dependency overload with those exact instances. It retains the original EditorPageViewState and EditorPageController. A single session can claim one assembly, bind one controller and attach one host. Binding remains one-use after the weak controller disappears. Foreign-controller dismantle cannot revoke another owner. The original UIViewControllerRepresentable now has an optional prepared coordinator; its original make/update bodies and default callers remain unchanged. Matching actual dismantle, lease release or prepared-session deallocation invalidate the host lifetime; no document open, update or close is initiated.

The owner reads generation identity synchronously on admission and return. The observer's MainActor task only delivers retirement/drain notification; refusal does not depend on scheduling it. Atomic registration cannot miss invalidation between token capture and subscription. Replacing the document's lifetime source also fails closed.

The prior admitted-operation contract remains unchanged. A write or publication admitted before retirement may already have produced its real side effect and may finish afterward. A successful write then returns completedWithoutOwnership with the real reason. It does not mean rollback, cancellation, safe retry or no write. Already-admitted publication delivery remains recorded. The once-only drain callback waits for all admitted operations. Two prepared hosts sharing a document retain separate host authority.

## Source preservation and real limits

Five complete original source files match the parent after the recorded exact additive inverses: BaseDocument, EditorPageModuleAssembly, EditorPageView, EditorPageViewState and EditorSwiftUIViewContainer. Five prior owner methods are byte-identical. Earlier original assembly/action/event preservation guards also pass. Original controller, BaseDocumentProtocol, DocumentMode, project/workspace and Modules objects remain unchanged where recorded in PRESERVED_INPUTS.json. Fresh upstream develop was read via git ls-remote at d857b23ea540be33d6faab4f7a7a1a260ab578c1; the existing fork baseline is a05088b98844bba30f90b794effb8cf579e2ef08. The approved original-file exceptions are appended to UPSTREAM_EXCEPTION_REGISTER.md.

The portable driver compiles complete new lifetime, owner, text/event wrappers and prepared session. It executes exact original close, permission-update, close-event and setupView bodies using recorded Foundation boundary doubles. The actual original ObjectPermissions struct and initializer, original mode/document/text protocols and forwarding code are included. UIKit controller/state, model setter/subscriptions, Combine storage, payload details and nonexecuted service interfaces are explicit doubles. The original whole UIKit assembly and concrete live event stream are not portable proof.

The fixture calls the exact setupView body to model an authoritative open completion. It does **not** prove that original open() reopens the same document instance: the original source retains openTask and this tranche does not reset it or alter its RPC semantics. A consumer must use a genuinely opened original document; a stale state cannot be repaired by manufacturing a token. No raw unconsumed middleware transition or Apple callback order is inferred from the local controls.

The eight new Swift Testing declarations are in PreparedEditorLifetimeTests at canonical AnytypeTests/Markdown/PreparedEditorLifetimeTests.swift. The prior 24 declaration files are byte-identical. TEST_DECLARATIONS.json records all 32 names and hashes. The existing synchronized target includes this path without a project edit; declaration membership is not Xcode discovery/execution.

## Remaining concrete integration

Other original block, table, pasteboard, object, file, property, undo and router writers still need document-owned admission, exact source binding and actual routed-callback lifecycle. No full writer isolation, public/importable EditorKit, Maktabah expanded editor, structured annotation storage, account/Space isolation or live save hook is enabled by this tranche. Original rendering and action semantics remain the integration target. Actual two-block editing, same annotation identity/classification, native input, relaunch, visibility, physical-device and performance acceptance remain open.

The independent reviewer found no further source blocker in the fresh-close correction. Root will review the full source and original-file inverses before freezing a later Apple gate. This evidence is scoped to the exact source above, and does not close CROSS-APP task1220545194715722.
