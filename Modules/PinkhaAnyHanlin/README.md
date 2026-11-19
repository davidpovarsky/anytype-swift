# Hanlin on the Any engine

This package keeps the existing Hanlin host policy in one shared implementation and supplies an Any-specific native I/O binding. It consumes the canonical Hanlin SDK archive prepared by Tools/Hanlin/prepare_sdk.py at 116cc6be0654a5d11bc56ba00e0310031107ee36. It does not implement a second SDK dispatcher, grant store, model provider, or conversation format.

## Products and application boundary

- PinkhaHanlinCore contains the original consent, revocation, invocation identity, routing, navigation ledger, creation plan, durable journal, shared creation worker, and account owner.
- PinkhaHanlinUI contains the original canonical Hanlin chat/composer, connection setup, consent presentation and shared model lifecycle. Its Apple UI uses the SDK's presentation components and the original localized resources. The retained Heart application injects its existing styling and native I/O wrapper; the Any presentation factory uses the same implementation.
- PinkhaAnyHanlin binds those components to AnyApplicationSession, AnyEditorDocumentStore, AnyNativeObjectCreator, and current native membership/type queries.
- PinkhaAnyHanlinProbe exercises real native HTTP plus canonical Hanlin read routing on a newly created synthetic page. Its presentation owner is explicitly a test fixture. It cannot acknowledge a real UI mount and is not proof that an iOS permission sheet was displayed.

The app must provide a real AnyHanlinPresentationOwner that validates the foreground scene, original account/Space, actual mounted editor, selection, source revision and presentation identity. Its invalidation callback is mandatory on those transitions. Writes additionally require AnyHanlinCreationPresentationOwner, an installed SDK presentation, the shared account owner, and both protected journals. Construction of a scope value grants no authority.

`AnyHanlinPresentation.present(from:native:documents:sourceOwner:conversationID:locale:creation:)` installs the shared SDK UI from a real native editor. The source owner validates the mounted editor and registers invalidation; the SDK presentation binds to the single shared account owner after the controller actually appears. Rebinding to a different presentation, stale source, foreign session or revoked owner fails closed. `PinkhaHanlinChatController.revoke()` immediately closes that authority and `drain()` awaits the shared close work. The application also drains `AnyApplicationSession` before stopping or switching the runtime.

The main application's native runtime and retained Heart target remain separate integration boundaries. Adding this package alone does not migrate existing user spaces or prove either complete application has launched.

## Shared source extraction

The following former app sources now have a single implementation under Sources/PinkhaHanlinCore. Existing Heart UI/services import that product.

| Former app source under Anytype/Sources/Pinkha/AI | Shared source |
| --- | --- |
| PinkhaHanlinHostAdapter.swift | PinkhaHanlinHostAdapter.swift |
| PinkhaHanlinReadRace.swift | PinkhaHanlinReadRace.swift |
| PinkhaHanlinNavigationLedger.swift | PinkhaHanlinNavigationLedger.swift |
| PinkhaHanlinReadConsentDecision.swift | PinkhaHanlinReadConsentDecision.swift |
| PinkhaHanlinRevocationFence.swift | PinkhaHanlinRevocationFence.swift |
| PinkhaHanlinInvocationEnvelope.swift | PinkhaHanlinInvocationEnvelope.swift |
| PinkhaHanlinAccountOwner.swift | PinkhaHanlinAccountOwner.swift |
| Write/PinkhaHanlinCreatePagePlan.swift | PinkhaHanlinCreatePagePlan.swift |
| Write/PinkhaHanlinWriteJournal.swift | PinkhaHanlinWriteJournal.swift |
| Write/PinkhaHanlinWritePreflight.swift | PinkhaHanlinWritePreflight.swift |

The portable bodies of Write/PinkhaHanlinReadWriteHost.swift are in PinkhaHanlinHostRouter.swift; its app file remains a UIKit composition wrapper. The reservation/timeout/cancellation/late-receipt worker from Write/PinkhaHanlinCreatePageRunner.swift is in PinkhaHanlinCreateRunner.swift; its app file remains the Heart native-create wrapper. Both hosts use PinkhaHanlinCreatePageTool for the same SDK descriptor. The shared account registry replaces only the concrete presentation type with PinkhaHanlinOwnedPresentation; its namespace, opening, logout retention and explicit remove-data behavior remain the original implementation.

The original chat presentation/view and consent controller are likewise shared under `Sources/PinkhaHanlinUI`; retained app files are thin aliases or composition wrappers. `PinkhaHanlin.xcstrings` moved byte-for-byte into that product's resources (SHA-256 `f5542c89c7862d84a0b965b839b690e51398b20c2afae1ed995291ce806eb519`).

Public visibility, public value constructors, portable Crypto import, typed native I/O seams, and application imports are the mechanical extraction changes. The additive known-object recovery sidecar described below is an intentional behavior change to the common journal, with the original v1 Entry/Effect bytes preserved. The parent capability-retention check records exact original and refactored blobs. A successful component build does not replace the existing application and SDK consumer tests.

## Native read contract

The original read tool still returns bounded plain text for the current document or selected text blocks. It accepts no arbitrary object target.

Any editor text is inline Markdown. AnyHanlinPlainText uses the pinned official swift-markdown parser (25cb61d3482054b09ae76ca4f281b1bfe7fe5a43) and explicitly renders visible text, links' labels, image alternative text, code contents and line breaks. Its generic plainText implementation is intentionally not used: that implementation retains code delimiters and raw HTML. Raw HTML/custom unsupported nodes fail visibly; code blocks preserve literal native text.

The native read is bound to one engine run/account/Space lease, the exact mounted object and revision, the complete reachable block tree, and the original selection. Unknown/orphaned blocks and byte/count overflows fail the read. A queued navigation request remains queued until the actual UI owner proves the exact visible target; the command-line probe intentionally cannot supply that proof.

Read consent begins denied. Revocation is one-way; late Allow callbacks cannot revive the presentation. The shared read race bounds foreground completion without treating an unfinished native read as a second available worker.

## Native creation and original-scope receipts

The canonical tool creates one titled standard Page in the original Space after a fresh exact native confirmation. Title bytes remain unchanged and exist in memory only; metadata journals store digests and opaque identifiers.

Any's built-in plain Page has id/xKey page, builtIn true, and intentionally hidden true. The new authority uses that immutable built-in identity plus the current active owner/admin/writer membership. Applying Heart's hidden-false eligibility rule would incorrectly disable normal pages. Creation also requires the exact native `currentWriterObjectCreate=1` capability. Type/member fingerprints are checked again after the approval await and before native dispatch; the dedicated native create route supplies the final current-writer storage fence. A stock engine without that contract cannot activate the write tool. The intent has empty collections and no template/body/existing-object edits.

There are two metadata responsibilities:

1. The shared Hanlin journal reserves the canonical SDK invocation in its original namespace and retains notDispatched/uncertain/committed receipts. Its original v1 Entry/Effect wire representation is unchanged.
2. The native creation journal reserves a deterministic 32-hex mutation identity and retains the authoritative native object ID. The stock native API does not offer idempotent object creation; an ambiguous dispatch cannot be retried under a new ID.

The shared worker does not cancel a native operation after dispatch. Foreground cancellation/timeout returns promptly with retained original-scope metadata. Native completion calls onNativeConfirmed inside the still-owned application lease, after the native ID is durable and before stale delivery checks; that callback refines the original Hanlin journal. Account/session revocation can suppress UI delivery without discarding the native outcome.

If the native route reports an incomplete creation with a validated known object ID, `AnyHanlinCreateBinding` records that ID in an append-only `.known-object` sidecar inside the original application lease before propagating failure. It does not invoke the success callback or manufacture a committed receipt. A matching reservation is mandatory; mismatched namespaces, unknown serialized fields, a different object ID, or a notDispatched receipt cannot acquire recovery authority. The original reserved/uncertain entry bytes are not rewritten. Reopen retains the known ID for explicit recovery, and a later verified success may refine the same invocation to committed. The native mutation journal remains the independent guard against automatic redispatch.

Ordinary chat dismissal/logout retains metadata. Explicit account removal poisons matching journal owners and waits for in-flight journal openings before deletion. Unsupported production protected-storage platforms fail closed; these packages do not replace iOS protection with a permissive desktop test directory. Actual iOS filesystem and lifecycle proof must run on Apple.

## Verification and remaining integration gates

Recent source-bound evidence:

| Receipt | Verified scope |
| --- | --- |
| `Evidence/windows-hanlin-components-v3.json` | 19 portable Hanlin tests against the canonical SDK and the captured dependency graph. |
| `Evidence/native-hanlin-read-v1.json` | 11 actual native HTTP/read-routing checks with a synthetic presentation owner. This predates the new guarded creation capability gate and is not creation or UIKit proof. |
| `Evidence/owner-recovery-components-v1.json` | 9 focused portable tests: four single mounted-owner cases, four strict known-ID recovery metadata cases, and the exact guarded-creation capability gate. Zero failures/skips; source graph stable. |

Three iOS-only protected recovery-store tests cover durable reopening, preservation of old journal bytes and contradictory outcomes. They require the Apple simulator lane and are not included in the portable nine-test receipt. The shared UIKit product and both actual app consumers also require Apple compilation and mounted UI acceptance; a Windows build excludes UIKit.

The first Windows compile consumed the canonical SDK and shared sources successfully. The initial run passed 14 component tests (eight parser cases, six shared policy/scope cases). That run overlapped Host source development and is integration feedback, not a source-stable end-to-end receipt.

Tools/run_local_validation.py hashes Sources, Tests, Package.swift and Package.resolved for this package and its four local dependencies before and after sequential Hanlin/Host tests. Receipts record exact test names/counts, zero-skip requirements, log hashes and executable hashes. Subsequent receipts in Evidence supersede the initial compile feedback only for their stated scope.

The native probe requires explicit --allow-disposable-writes and a disposable account/Space. It creates its own synthetic page and never infers a target from existing user content. It tests actual native readback, plain Hebrew through the shared SDK router, consent denial/allow routing, metadata-only receipts, duplicate refusal, queued navigation and denied fake mount acknowledgment. It is separate from actual app UI, protected-journal durability, cross-device convergence, and full editor migration proof.
