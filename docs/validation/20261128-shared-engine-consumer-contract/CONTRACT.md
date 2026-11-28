# Shared engine and consumer contracts — W1 to W3

This is a bounded source audit of immutable integration commit `daaedc545eac20df260489b8a7579527c057aeac`, tree `fab1e3fa2079b7181f7d099049b1d4abb875a488`. Twelve complete source files, 98,669 bytes, were read and matched by Git blob SHA, SHA256 and path in that commit. A later peer also checked the complete 7,907-byte native `files_status.go` against the original Runtime18 map and the separately proposed native64 maps. The exact source scopes are recorded separately in `SOURCE_READS.json`.

The audit changes no application or engine code. It grants no new runtime, Apple, cloud or release acceptance. W3 owns the actual Hanlin, MiniApps and Otsaria consumer integration.

A later, separately bounded Hanlin factory delta is bound to published integration commit `f0eab88b57da3ef9b3586dc9a40c853948060eb9`, whose sole parent is `ff5777896ced23171522a0d6d735e2b235b11ffc`. Its three complete Swift files and source map were retrieved and joined to all four whole predecessor bodies. `HANLIN_FACTORY_SOURCE_DELTA.json` and `PEER_REVIEW_N_HANLIN_FACTORY.json` record that scope; it does not turn the original twelve-file audit into a complete current-App review.

## Shared ownership and authorization

| Boundary | Concrete source interface | Required behavior and limits |
| --- | --- | --- |
| Embedded Any application | `PinkhaEmbeddedAnyApplication`, `PinkhaEmbeddedAnyPresentation` | The facade forwards to the same underlying Any application actor and original presentation session. Resume/suspend uses that owner. This source does not prove the two engines have been exercised together on a new product. |
| Heart authorized operation read | `HeartAuthorizedOperationSession`, `HeartAuthorizedOperationReader`, shared `TorahOperationReadScope`/`TorahAuthorizedOperationSnapshot` | Account, Space and session generation are bound. Owner invalidates synchronously before replacing native scope. Cancellation and scope checks surround the byte transport/decode; final UI publication uses the same main actor with no intervening await. A saved ID is not native permission. |
| Hanlin Any adapter | `AnyHanlinHost` → `PinkhaHanlinHostRouter`, `AnyHanlinNativeAccess` | Uses the canonical shared Hanlin router and host contracts. The mounted presentation owner supplies account/Space/document/revision/selection. The native read uses the existing application lease and rechecks generation, the exact UTF-8 `engineStartedAt` lease marker, original scope and consent after await. This interface does not itself validate an `AnyNativeAccountRunBinding.runID`. |
| Hanlin close and cancellation | `invalidate()`, `close()`, `drainCancelledInvocation` | Revocation is synchronous before async drain. Original-scope receipt metadata survives cancellation. Close waits for the router; consumer cancellation is not evidence of rollback. |
| MiniApps work lifetime | `PinkhaMiniAppsLifetime` | Each auth/engine-switch caller owns a distinct revocation hold. Revocation changes generation and prevents new submission, then drain waits for existing operations. It does not cancel a native write whose outcome is unknown. Consumers must validate the supplied lease at their own access/dispatch boundaries. |
| MiniApps return navigation | `PinkhaMiniAppsReturnQueue` | While a request UUID is retained, its upstream-authenticated target remains tied to exact UTF-8 engine/account/Space/document identity and repeated URLs cannot replace that target. `didReachEditor` removes the retained target and order entry; this queue has no completed-request replay tombstone and performs no callback authentication. The upstream bridge owns authentication and replay policy. A mounted-editor acknowledgement is navigation completion only; durable results and write acknowledgements remain separate. |

The current Hanlin package uses the existing HanlinAgentSDK, HanlinPlatform, HanlinPresentationSDK and HanlinMiniAppsBridge package paths. The adapter does not create a second Hanlin tool router or a separate arbitrary Markdown client: `AnyHanlinSaveMessageServices` constructs its body adapter from the same supplied HTTP client.

At the original audited revision, the explicit save assembly was DEBUG-only. The later `f0eab88b` source provides these explicit factories in release-visible code:

| Entry | Exact composition and scope |
| --- | --- |
| Heart `PinkhaHanlinReadWriteHost.makeForSavingMessages` | App-internal factory. Builds the original Heart context and invokes the unchanged private constructor with `includeSaveMessage: true`. The native runners, mounted presentation, confirmation, account journal and drain remain the original implementations. |
| `AnyHanlinHost.makeForSavingMessages` | Public low-level factory. Requires the original native session, document store, owner, creation services and explicit Save services. It delegates to the same private initializer; those supplied services include their conversion closure. |
| `AnyHanlinPresentation.presentForSavingMessages` | UIKit-only public presentation entry. Creates Save services with the supplied native HTTP client and the original Markdown converter, then uses the same mounted presentation helper and host factory. |

The DEBUG acceptance factories now delegate to these same entries. The ordinary Heart `make` still passes `includeSaveMessage: false`; ordinary Any initialization still passes `saveServices: nil`; ordinary Any presentation still uses that initializer. The source delta changes neither those ordinary entry points nor their existing authority, consent, journal or cancellation/drain bodies.

The new factory names expose a source API. They do not prove Release compilation, native Markdown body persistence/readback, Allow/Cancel behavior, Stop after a native root mutation, or ordinary editor adoption. W3 owns those actual consumer gates. The source map changes only `changes[32].replacementBlob`; its retained statement about the earlier candidate having no production Save factory is historical text, not the current explicit API contract.

## Files: storage, acknowledgement and durability

| API or state | Meaning | Consumer obligation |
| --- | --- | --- |
| `AnyNativeFileUploader.fingerprint` | Bounded digest/size observation of a selected source file | Keep the source's security-scoped access alive and preserve the exact intended bytes. |
| `attach(... validateScope:authorizeDispatch:retainReceipt:)` | At most one original native POST for that invocation | The host journal serializes the action. Entering the one-shot dispatch callback establishes the uncertainty boundary; do not retry automatically afterward. |
| Validated upload201 | Known native file identity and metadata | Persist the receipt in its original scope before any cancellation/account/consumer postflight check. It is not plaintext digest readback or cloud-transfer proof. |
| `AnyNativeFileUploadUncertain` | A post-dispatch or reservation failure with possible native effects | Retain the original typed underlying error and any identity-only known receipt. Reconcile the original action; do not infer rollback or issue a replacement upload. |
| `info` | Current metadata of one exact known file | Pair it with content digest/readback and another metadata observation when verifying bytes. Account/Space fields are request scope because the original FileInfo does not itself advertise them. |
| Status `durable` | Native-verified custody, or an inline file | It does not by itself distinguish network storage from inline storage. Keep `inline`, `cached` and custody evidence distinct. |
| Status `inflight` | A non-inline file has no durable network signature in the observed native row | Do not infer an active or queued transfer, progress, or completed cloud durability. The native status remains `inflight` even when the queue is absent, the job is absent, or queue lookup fails. |
| Status `limited` | Actual native storage-limit refusal | Local availability is independent. Preserve the job and local bytes. The broker cancellation fix grants no quota. |
| Retry204 | Native retry request acknowledged | It is not new quota, completed transfer, uploaded bytes or a durable receipt. Read current status again. |

`AnyNativeFileUploadResponse`, used by the attach/info response path, refuses redirects, HTTP authentication replay and replacement upload streams; it bounds acknowledgement bytes and owns one task/session. Its completion waits for both task completion and session invalidation, followed by the serial delegate barrier, before returning and releasing any staged-file ownership. This two-callback barrier belongs to that response transport. The generic `AnyHTTPClient` and `AnyHTTPBoundedFileRead` do not inherit that same barrier. The current platform cancellation/drain behavior still needs its matching compiled qualification.

The upload API's configured limit is 512 MiB. The retained original largest file proof is 8 MiB; the configured upper bound is not an empirical 512 MiB acceptance result. Native MIME/name refinement is allowed, while exact content digest, file/object identity and source scope remain explicit.

The generic HTTP client performs account checks before/after ordinary requests and preserves mutation uncertainty when postflight admission fails. Its managed control header is applied when supplied. New native account/network/run-bound operations use their explicit binding APIs and the matching N24 server contract; pre/post account checks alone must not be relabelled as a newly proven atomic account-switch protocol.

## Reuse and pending qualifications

N's published Files acceptance matrix distinguishes actual retained P2P/range/crash/cold-offline evidence, the smaller-file cloud proof, and one offload/cloud-refetch proof. Actual cloud durability and retrieval of the original49,363-byte PNG and8MiB large file, fresh-vs-cached quota, cloud-specific interruption/resume and new-source/ABI consumer qualification remain open. The two small cloud files do not qualify the larger ones.

The historical SDK06 accepted23methods/32cases, ACK7 and original Hanlin UI22 remain at their original source/product scope. The original audit did not qualify the newer SDKd6b drain source or Any/N24/lifecycle/broker overlays. Later results remain in their own exact evidence records; this factory-source delta neither replaces nor extends those runtime results. No old unchanged cohort is scheduled for replay by this document.

The imported-document source delivery considered by the original audit is C22 `bcd4518793abda5f4183c81ddd150ae94abdb20e`, with its engine factory/document identity contract. At the audited integration commit, C14 is already applied; preserve executor37a, journalf084 and directoryf870 when adopting C22. The application still owns exact checkpoint selection persistence, actual mounted document identity and session lifetime. The later Ordinary14 cold-context integration and current-capture producer foundation have separate source contracts. The published C foundation `32a174219cca9b916c4fa5738d0e1891f6dbc349` returns the genuine preservation/content completion and two locators; its strict Ordinary14 execution and third locator remain an explicit C-owned follow-on. This documentation does not add either engine implementation.

## Otsaria and actual consumer acceptance

Otsaria's external implementation was not part of this finite twelve-file W1 read. It must consume the same scoped host/permission/receipt contracts through W3's pinned SDK and adapters. W1 has not edited or qualified that application's storage, synchronization, navigation or UI.

W3's final consumer gate must bind the exact application source, Hanlin SDK, shared Kit and native product; check account/Space and engine replacement, consent revocation during suspended work, retained acknowledgement after cancellation, no duplicate mutation on uncertain outcomes, and actual warm/cold reopen. Apple and device execution remain distinct from this source audit.
