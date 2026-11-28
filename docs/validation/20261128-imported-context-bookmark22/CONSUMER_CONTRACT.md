# Imported document context — engine and consumer contract

Status: source interface delivered; application wiring and current native execution remain open.

## Factory and lifetime

The exact engine factory is:

```swift
public static func openContent(
    client: AnyHTTPClient,
    session: AnyApplicationSession,
    preservationReference: AnyNativeImportedContextReference,
    preservationJournalDirectory: URL,
    contentReference: AnyNativeImportedContentContextReference,
    archiveSource: AnyNativeImportedContextArchiveSource
) async throws -> AnyNativeImportedContextOwner
```

The archive source is either `retainedFile(URL)` or `nativeDownload(to: URL)`. The caller supplies the original current session and its scoped client. No replacement session or independent native authority is manufactured by this factory.

For a mounted editable document the consumer uses:

```swift
public func withDocument<Value: Sendable>(
    destinationObjectID: String,
    _ operation: @escaping @Sendable (
        AnyNativeImportedDocumentEntry,
        AnyNativeImportedContentContext,
        AnyHostLease
    ) async throws -> Value
) async throws -> Value
```

The entry exposes original source Space/object/Type identity, snapshot and JSON-view digests, exact source key, actual destination object ID, native Type ID and original creation intent. The content context retains the completed plan, ordered mappings, imported definition directory, source-facts directory and Type-reference plan.

Use the supplied live lease for existing definition, property, source-fact and Type-reference APIs. A saved mapping is a routing identity, not proof of current access or schema. Those APIs retain their current checks. The source currently validates READ for opening and reading; this does not authorize a consumer to bypass the existing write-specific permission checks.

The consumer's asynchronous operation is fenced by current account/run/lease checks before and after it. Document callbacks additionally verify current document identity and source facts on both sides. The owner retains cancellable calls and `closeAndDrain()` closes the owner before draining them. Account/Space/session replacement must retire this owner using the existing lifecycle; the consumer must not retain an unscoped callback or use an old lease.

## Information the application still must supply

| Application input | Required identity | Delivered engine handling | Remaining application work |
| --- | --- | --- | --- |
| Saved selection | Exact private journal directory plus preservation and content references | Closed decoding, completed-checkpoint digest and binding checks | Persist and locate the selection within the correct existing account/Space; no App discovery call site is included |
| Original migration context | Store/plan/source archive and checkpoint identity | Restores the completed saved plan and ordered mappings without replay | Select the correct retained completion, not a display-name or catalog search |
| Mounted document | Actual destination document ID | Resolves it to source object, creation intent, immutable facts and current Type | Pass the real successfully opened document ID from the App owner |
| Current authority | Existing AnyApplicationSession, scoped client and lease | Account/network/run/current READ fencing and task drain | Connect the existing App session lifecycle and close on replacement |

A bare checkpoint reference does not solve the four-part application admission request. This package provides the engine factory and document identity checks; it does not claim that the real App has persisted, discovered or opened this owner.

## Ordinary14 boundary

The preservation reference currently binds only the earlier canonical supplement. The separate Ordinary14 plan/namespace and receipt merging are supplied by the C14 carrier. This frozen C22 owner does not automatically expose the extra fourteen ordinary definitions through its content context. Integration requires an explicit admission path joining that namespace to the same account/Space/checkpoint and current definition reads.

The original two captured Pages contain zero values for these fourteen descriptors. Future newly written value fixtures test usability; they must not be described as preservation of original populated values. No fallback from a missing source definition to a guessed display label, canonical alias or unrelated Type is allowed.

## Hanlin, MiniApps and Otsaria consumers

These consumers can adopt the same scoped engine interfaces when their owner integrates the carrier. They must use the existing account/Space client, current application session and supplied lease. Imported source IDs, destination IDs, native Type IDs and catalog-carrier IDs remain distinct. Stored context values do not grant permissions, establish cloud durability or authenticate a new native run.

File and synchronization adapters keep their existing receipt, cancellation, ACL and account isolation checks. This source contract does not qualify a consumer's storage, rendering, file transfer or sync behavior. No Hanlin, MiniApp or Otsaria application source was edited by W1 in this package.

## Acceptance required after source integration

The frozen C22 selection is 22 Swift methods and is not executed. Current native context opening, re-opening after a process crash or engine replacement, revoked authority during a callback, correct App selection persistence and exact consumer behavior require a matching admitted product and owner-controlled execution. Existing preserved migration/network/ACL/P2P proofs remain reusable only for unchanged source and their original scope.
