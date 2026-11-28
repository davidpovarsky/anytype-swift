# Shared engine and consumer contracts — W1 to W3

This is a bounded source audit of immutable integration commit `daaedc545eac20df260489b8a7579527c057aeac`, tree `fab1e3fa2079b7181f7d099049b1d4abb875a488`. Twelve complete source files, 98,669 bytes, were read and matched by Git blob SHA, SHA256 and path in that commit. The exact list is in `SOURCE_READS.json`.

The audit changes no application or engine code. It grants no new runtime, Apple, cloud or release acceptance. W3 owns the actual Hanlin, MiniApps and Otsaria consumer integration.

## Shared ownership and authorization

| Boundary | Concrete source interface | Required behavior and limits |
| --- | --- | --- |
| Embedded Any application | `PinkhaEmbeddedAnyApplication`, `PinkhaEmbeddedAnyPresentation` | The facade forwards to the same underlying Any application actor and original presentation session. Resume/suspend uses that owner. This source does not prove the two engines have been exercised together on a new product. |
| Heart authorized operation read | `HeartAuthorizedOperationSession`, `HeartAuthorizedOperationReader`, shared `TorahOperationReadScope`/`TorahAuthorizedOperationSnapshot` | Account, Space and session generation are bound. Owner invalidates synchronously before replacing native scope. Cancellation and scope checks surround the byte transport/decode; final UI publication uses the same main actor with no intervening await. A saved ID is not native permission. |
| Hanlin Any adapter | `AnyHanlinHost` → `PinkhaHanlinHostRouter`, `AnyHanlinNativeAccess` | Uses the canonical shared Hanlin router and host contracts. The mounted presentation owner supplies account/Space/document/revision/selection. The native read uses the existing application lease and rechecks generation, run, original scope and consent after await. |
| Hanlin close and cancellation | `invalidate()`, `close()`, `drainCancelledInvocation` | Revocation is synchronous before async drain. Original-scope receipt metadata survives cancellation. Close waits for the router; consumer cancellation is not evidence of rollback. |
| MiniApps work lifetime | `PinkhaMiniAppsLifetime` | Each auth/engine-switch caller owns a distinct revocation hold. Revocation changes generation and prevents new submission, then drain waits for existing operations. It does not cancel a native write whose outcome is unknown. Consumers must validate the supplied lease at their own access/dispatch boundaries. |
| MiniApps return navigation | `PinkhaMiniAppsReturnQueue` | The authenticated request UUID remains tied to exact UTF-8 engine/account/Space/document identity. Repeated URLs cannot replace that target. A mounted-editor acknowledgement is navigation completion only; the bridge remains the owner of durable results and write acknowledgements. |

The current Hanlin package uses the existing HanlinAgentSDK, HanlinPlatform, HanlinPresentationSDK and HanlinMiniAppsBridge package paths. The adapter does not create a second Hanlin tool router or a separate arbitrary Markdown client: `AnyHanlinSaveMessageServices` constructs its body adapter from the same supplied HTTP client.

The ordinary `AnyHanlinHost` initializer currently supplies no full-message save services. The separate `makeForSaveMessageAcceptance` assembly is DEBUG-only and explicitly awaits body/authority qualification. This source boundary must not be reported as an already enabled production save-message capability.

## Files: storage, acknowledgement and durability

| API or state | Meaning | Consumer obligation |
| --- | --- | --- |
| `AnyNativeFileUploader.fingerprint` | Bounded digest/size observation of a selected source file | Keep the source's security-scoped access alive and preserve the exact intended bytes. |
| `attach(... validateScope:authorizeDispatch:retainReceipt:)` | At most one original native POST for that invocation | The host journal serializes the action. Entering the one-shot dispatch callback establishes the uncertainty boundary; do not retry automatically afterward. |
| Validated upload201 | Known native file identity and metadata | Persist the receipt in its original scope before any cancellation/account/consumer postflight check. It is not plaintext digest readback or cloud-transfer proof. |
| `AnyNativeFileUploadUncertain` | A post-dispatch or reservation failure with possible native effects | Retain the original typed underlying error and any identity-only known receipt. Reconcile the original action; do not infer rollback or issue a replacement upload. |
| `info` | Current metadata of one exact known file | Pair it with content digest/readback and another metadata observation when verifying bytes. Account/Space fields are request scope because the original FileInfo does not itself advertise them. |
| Status `durable` | Native-verified custody, or an inline file | It does not by itself distinguish network storage from inline storage. Keep `inline`, `cached` and custody evidence distinct. |
| Status `inflight` | Native background work remains outstanding | Do not report completed cloud durability. |
| Status `limited` | Actual native storage-limit refusal | Local availability is independent. Preserve the job and local bytes. The broker cancellation fix grants no quota. |
| Retry204 | Native retry request acknowledged | It is not new quota, completed transfer, uploaded bytes or a durable receipt. Read current status again. |

The response transport refuses redirects, HTTP authentication replay and replacement upload streams; it bounds acknowledgement bytes and owns one task/session. Completion waits for both task completion and session invalidation before returning and releasing staged-file ownership. This is a source property; the current platform cancellation/drain behavior still needs its matching compiled qualification.

The upload API's configured limit is 512 MiB. The retained original largest file proof is 8 MiB; the configured upper bound is not an empirical 512 MiB acceptance result. Native MIME/name refinement is allowed, while exact content digest, file/object identity and source scope remain explicit.

The generic HTTP client performs account checks before/after ordinary requests and preserves mutation uncertainty when postflight admission fails. Its managed control header is applied when supplied. New native account/network/run-bound operations use their explicit binding APIs and the matching N24 server contract; pre/post account checks alone must not be relabelled as a newly proven atomic account-switch protocol.

## Reuse and pending qualifications

N's published Files acceptance matrix distinguishes actual retained P2P/range/crash/cold-offline evidence, the smaller-file cloud proof, and one offload/cloud-refetch proof. Actual cloud durability and retrieval of the original49,363-byte PNG and8MiB large file, fresh-vs-cached quota, cloud-specific interruption/resume and new-source/ABI consumer qualification remain open. The two small cloud files do not qualify the larger ones.

The historical SDK06 accepted23methods/32cases, ACK7 and original Hanlin UI22 remain at their original source/product scope. The newer SDKd6b drain source and current Any/N24/lifecycle/broker overlays need their explicitly matched qualification. No old unchanged cohort is scheduled for replay by this document.

The current source delivery for imported documents is C22 `bcd4518793abda5f4183c81ddd150ae94abdb20e`, with its engine factory/document identity contract. At the audited integration commit, C14 is already applied; preserve executor37a, journalf084 and directoryf870 when adopting C22. The application still owns exact checkpoint selection persistence, actual mounted document identity and session lifetime. A separate Ordinary14 cold-context extension is owner work and is not silently included here.

## Otsaria and actual consumer acceptance

Otsaria's external implementation was not part of this finite twelve-file W1 read. It must consume the same scoped host/permission/receipt contracts through W3's pinned SDK and adapters. W1 has not edited or qualified that application's storage, synchronization, navigation or UI.

W3's final consumer gate must bind the exact application source, Hanlin SDK, shared Kit and native product; check account/Space and engine replacement, consent revocation during suspended work, retained acknowledgement after cancellation, no duplicate mutation on uncertain outcomes, and actual warm/cold reopen. Apple and device execution remain distinct from this source audit.
