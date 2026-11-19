# Hanlin on the Any engine

This package keeps the existing Hanlin host policy in one shared implementation and supplies an Any-specific native I/O binding. It consumes the canonical Hanlin SDK archive prepared by Tools/Hanlin/prepare_sdk.py at 116cc6be0654a5d11bc56ba00e0310031107ee36. It does not implement a second SDK dispatcher, grant store, model provider, or conversation format.

## Products and application boundary

- PinkhaHanlinCore contains the original consent, revocation, invocation identity, routing, navigation ledger, creation plan, durable journal, shared creation worker, and account owner.
- PinkhaAnyHanlin binds those components to AnyApplicationSession, AnyEditorDocumentStore, AnyNativeObjectCreator, and current native membership/type queries.
- PinkhaAnyHanlinProbe exercises real native HTTP plus canonical Hanlin read routing on a newly created synthetic page. Its presentation owner is explicitly a test fixture. It cannot acknowledge a real UI mount and is not proof that an iOS permission sheet was displayed.

The app must provide a real AnyHanlinPresentationOwner that validates the foreground scene, original account/Space, actual mounted editor, selection, source revision and presentation identity. Its invalidation callback is mandatory on those transitions. Writes additionally require AnyHanlinCreationPresentationOwner, an installed SDK presentation, the shared account owner, and both protected journals. Construction of a scope value grants no authority.

The existing application backend has not been switched merely by adding these packages. The main application owner must install this native presentation and revoke/drain its AnyApplicationSession before stopping or switching the runtime.

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

Public visibility, public value constructors, portable Crypto import, the narrowly typed native I/O seams, and application imports are the intended extraction changes. The parent capability-retention check records exact original and refactored blobs. A successful component build does not replace the existing application and SDK consumer tests.

## Native read contract

The original read tool still returns bounded plain text for the current document or selected text blocks. It accepts no arbitrary object target.

Any editor text is inline Markdown. AnyHanlinPlainText uses the pinned official swift-markdown parser (25cb61d3482054b09ae76ca4f281b1bfe7fe5a43) and explicitly renders visible text, links' labels, image alternative text, code contents and line breaks. Its generic plainText implementation is intentionally not used: that implementation retains code delimiters and raw HTML. Raw HTML/custom unsupported nodes fail visibly; code blocks preserve literal native text.

The native read is bound to one engine run/account/Space lease, the exact mounted object and revision, the complete reachable block tree, and the original selection. Unknown/orphaned blocks and byte/count overflows fail the read. A queued navigation request remains queued until the actual UI owner proves the exact visible target; the command-line probe intentionally cannot supply that proof.

Read consent begins denied. Revocation is one-way; late Allow callbacks cannot revive the presentation. The shared read race bounds foreground completion without treating an unfinished native read as a second available worker.

## Native creation and original-scope receipts

The canonical tool creates one titled standard Page in the original Space after a fresh exact native confirmation. Title bytes remain unchanged and exist in memory only; metadata journals store digests and opaque identifiers.

Any's built-in plain Page has id/xKey page, builtIn true, and intentionally hidden true. The new authority uses that immutable built-in identity plus the current active owner/admin/writer membership. Applying Heart's hidden-false eligibility rule would incorrectly disable normal pages. Type/member fingerprints are checked again after the approval await and before native dispatch. The intent has empty collections and no template/body/existing-object edits.

There are two metadata responsibilities:

1. The unchanged Hanlin journal reserves the canonical SDK invocation in its original namespace and retains notDispatched/uncertain/committed receipts.
2. The native creation journal reserves a deterministic 32-hex mutation identity and retains the authoritative native object ID. The stock native API does not offer idempotent object creation; an ambiguous dispatch cannot be retried under a new ID.

The shared worker does not cancel a native operation after dispatch. Foreground cancellation/timeout returns promptly with retained original-scope metadata. Native completion calls onNativeConfirmed inside the still-owned application lease, after the native ID is durable and before stale delivery checks; that callback refines the original Hanlin journal. Account/session revocation can suppress UI delivery without discarding the native outcome.

Ordinary chat dismissal/logout retains metadata. Explicit account removal poisons matching journal owners and waits for in-flight journal openings before deletion. Unsupported production protected-storage platforms fail closed; these packages do not replace iOS protection with a permissive desktop test directory. Actual iOS filesystem and lifecycle proof must run on Apple.

## Verification and remaining integration gates

The first Windows compile consumed the canonical SDK and shared sources successfully. The initial run passed 14 component tests (eight parser cases, six shared policy/scope cases). That run overlapped Host source development and is integration feedback, not a source-stable end-to-end receipt.

Tools/run_local_validation.py hashes Sources, Tests, Package.swift and Package.resolved for this package and its four local dependencies before and after sequential Hanlin/Host tests. Receipts record exact test names/counts, zero-skip requirements, log hashes and executable hashes. Subsequent receipts in Evidence supersede the initial compile feedback only for their stated scope.

The native probe requires explicit --allow-disposable-writes and a disposable account/Space. It creates its own synthetic page and never infers a target from existing user content. It tests actual native readback, plain Hebrew through the shared SDK router, consent denial/allow routing, metadata-only receipts, duplicate refusal, queued navigation and denied fake mount acknowledgment. It is separate from actual app UI, protected-journal durability, cross-device convergence, and full editor migration proof.
