# Same-owner destination operation — source-only handoff

This isolated change exposes a throwing destination operation through the existing Any presentation owner. It uses that owner's actual client, workspace session and lease. The current App invocation is still pending.

## Changes

- `Modules/PinkhaAnyNative/Sources/PinkhaAnyNative/AnyNativeRootView.swift` adds the public operation, its private model implementation and a completion fence.
- `Modules/PinkhaEngineHost/Sources/PinkhaEngineHost/PinkhaEngineHost.swift` forwards the operation through the existing presentation.
- `Modules/PinkhaEngineHost/Package.swift` adds the direct PinkhaAnyEngine package/product dependency only in the existing unified-runtime branch. The preserved Heart-only branch stays inert.

The existing UI execute, resume, suspend, sign-out, join and workspace-close bodies are byte-identical to the source parent. No App source, original session, Heart/protobuf code, generated protocol, native binary, credential or user data is changed.

## Ownership and delivery

The model checks the explicit destination identifiers, actual current session and presentation lifetime before reserving its existing operation slot. The callback runs inside the unchanged `AnyApplicationSession.perform`, receiving its real `AnyHostLease`. Caller cancellation and presentation suspension reach the same typed worker.

A cancelled tracker continues waiting for a private completion fence. The public operation does not await its tracker. Its final MainActor cancellation, epoch, workspace/session, lifetime and exact UTF-8 account/Space checks follow the last await; its defer then clears the slot and settles the fence synchronously. This keeps suspension from finishing and resuming another presentation before the old operation has returned or refused its result.

Cancellation remains cooperative. The actual callback must await its owned work and must not await its own presentation's full suspension. No forced termination or maximum drain time is claimed.

## Concrete C producer integration

C's first producer registered only the callback inside the destination operation. E's review found that the surrounding session still performed an async lease check after that registration ended. The corrected producer registers the entire destination adapter and checks its source ticket after that await. The original source controller's native cleanup never waits for the producer, which avoids a source-validation/producer drain cycle.

The exact corrected producer API pinned in `CALLER_CONTRACT.json` is a separately owned source dependency. Its code is not installed or applied by this commit. Root's storage and functional review is separate. The retained E peer preserves the rejected predecessor, exact correction and comment-only successor.

The intended call shape is:

```swift
let completion = try await producer.execute(request, inDestination: { body in
    try await presentation.performDestinationOperation(
        expectedAccountID: request.workspace.accountID,
        expectedSpaceID: request.workspace.spaceID,
        body)
})
```

This expression documents the source contract; it is not an implemented App callsite. W3 must arrange the live original Heart capture and the same already-active Any destination before invoking it. The current facade exposes no destination selector or owner getter, and this change does not create one. Producer construction belongs inside the existing capture facade so it retains the actual private source account controller. No raw token handoff is needed.

## Remaining gates

- Swift parsing, type checking, compilation and deterministic cancellation/delivery race tests have not run.
- Current native account/run/ACL support, unified ABI/network binding and dual-runtime behavior remain independently required.
- The actual App selection/invocation, source cancellation, post-return identity/persistence, mount and cold reopen are W3 work.
- A source close failure remains explicit and retryable; successful ownership transfer requires completed cleanup.
- E Native97/Swift23, N24 adoption/cache release and every existing resource gate remain unchanged.

Source review is not native, Apple, migration or App acceptance. All newly proposed runtime behavior remains NOT_RUN.

## Provenance and isolated publication

Source parent: `af1aca9c33c0b38101c20ab24c88b1cfc07d7a17`, tree `4b017155088782ec1b3d31e872e3aaf387707823`. All three beforeimages and four destination dependencies were independently re-read at that immutable current W3 source. Both original source-owner dependencies were also re-read. Their complete Git blobs and bytes equal the earlier daa primaries used by the reviewers.

Seven literal edits across three files reconstruct and reverse the whole source bodies exactly. The three active changes are downstream-owned Pinkha sources; no upstream exception is used. The current upstream/develop metadata observation is retained as provenance, not an integration base or runtime proof.

`SOURCE_MANIFEST.json` binds every declared source/evidence member other than itself. The eventual publication proof records complete blob readbacks, normal branch publication and an exact inverse restoring the parent tree. Only this owned branch is advanced. The final integration branch and App worktree are untouched.

Peer records: Root independently reviewed the E lifetime and all seven inverses; N independently reviewed the owner interface and drain; E independently reviewed C's corrected whole-operation lifetime. Original source proposals and failures remain separately attributed.
