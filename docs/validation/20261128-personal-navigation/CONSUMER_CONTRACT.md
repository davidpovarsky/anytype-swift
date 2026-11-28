# Consumer contract: W1 personal navigation

## Ownership

W1 owns these engine and Host APIs. W2 binds them to navigation, panels and actual-open gestures. W3 integrates the accepted Host and native-server revisions and owns release. No companion application or final integration branch is edited by this packet.

This child depends on parent 0b8f03a13d332fc44ed89fc9d6389658d6cfc5e0 and the existing Type25 APIs inherited through e6fedfdbc7390a5a4e934726806c952319ba4238.

## Original source projection

AnyHeartOriginalNavigationBinding and AnyHeartOriginalNavigationStore read captured Workspace, Home, Archive and Widget identities through AnyNativeImportedCatalogDirectory. The directory must come from the saved, completed destination plan and immutable operation mappings. The underlying catalog read rechecks signed creation, unchanged rows and the caller's current lease/READ authority.

The contexts preserve native kinds 518, 32, 48 and 112 respectively. They are not ordinary created Pages. Absent, explicitly empty, built-in, exact object identity and unsupported original values remain separate. These snapshots do not authorize destination writes or prove a current Home selection.

AnyHeartLastOpenedBinding verifies the original captured last-opened definition independently from the current local provider. It exposes source evidence and routes actual-open observations through AnyNativePersonalNavigationStore; no archived clock is replayed.

## Current native run binding

Acquire a binding from AnyHTTPClient.nativeAccountRunBinding(expectedNetworkID:). The closed GET /v1/auth/engine-binding result has exactly contract, accountId, networkId and runId. The contract is pinkha-any-http-engine-binding-v1; runId is a 64-character lower-case hexadecimal nonce. Identifiers compare exact UTF-8 bytes, and diagnostics redact the run binding.

The caller creates one AnyNativePersonalNavigationStore with its current managed client, workspace and captured binding. It uses the existing AnyHostLease from the owning AnyApplicationSession. It must not reacquire a new owner inside a suspended operation to revive an old request.

Only these bound mutations are allowed:

| Operation | Route | Success |
| --- | --- | --- |
| Current Home | PATCH /v1/pinkha/bound/spaces/{spaceId}/settings | 204, no body |
| Actual local open | POST /v1/pinkha/bound/spaces/{spaceId}/properties/{objectId}/set/any | 200, exact local modify result |

The request carries X-Any-Expected-Account-Id and X-Any-Expected-Run-Id. Success requires matching X-Any-Binding-Contract, X-Any-Bound-Account-Id and X-Any-Bound-Run-Id. Missing/mismatched acknowledgment stays uncertain. Never resend through an older unbound route.

## Home and actual-open usage

readHome(lease:) reads GET SpaceInfo and the pinkhaHomeV1 setting. There is no assumed GET-settings endpoint. A nil preparation unsets Home; .empty writes the explicit empty string; .builtIn selects widgets, graph, lastOpened or chat; .object keeps the exact destination object ID. Nonempty structured selections are JSON strings inside the native setting, not nested setting objects.

Use requireHomeDestination(_:lease:) before navigating to a stored selection. Unsupported or stale references remain unavailable. No missing destination is created automatically.

Use prepareActualOpen(objectID:observedAt:lease:) only for a real open observation. The engine field must remain the immutable built-in local datetime pinkhaLastOpenedV1 with contract pinkha-last-opened-local-v1 and seconds precision. The timestamp is bounded, rounded down to a whole Unix second and represented as exact milliseconds. The object must exist under the current account, space, run and READ membership.

The local modify result must name exactly the requested object, provide a nonempty version, have no shared changeId and contain no rejection. A shared-DAG response or partial/foreign result cannot acknowledge this operation.

## Preserve acknowledgment across owner retirement

Both commitHome and commitActualOpen require a synchronous @Sendable onAcknowledged closure. Retain the received operation metadata immediately. The callback runs after the exact successful native response and before any awaited current-state check.

Readback can be verifiedCurrent or nativeAcknowledgedCurrentStateUnverified. In the latter case the snapshot is nil. The original application owner may independently reject delivery with CancellationError after invalidation. Use acknowledgment(for:) to inspect retained operation metadata, without reading a private object through a retired lease or resending the intent.

The actor tracks at most 256 attempted operation IDs for its lifetime. This is bounded in-memory duplicate prevention, not a persisted journal. Product-level crash reconciliation must use a separately qualified durable owner/journal contract.

## Activation gates

The Host tuple is qualified by Navigation26's retained23 plus targeted3. The native engine-binding server, dedicated routes, server-side run pin and local property definition must be integrated and qualified independently. The N24 source successor was prepared separately; these component fixtures do not assert its runtime success.

Source-review context is not destination admission. The application must receive a real completed-migration context through C's owner interface before it can build a catalog directory. W2 should preserve this separation when connecting the actual owner after restart.

The raw failure and successful results remain part of this handoff. Do not count the new three methods twice or promote the earlier failed 26-method process to PASS.
