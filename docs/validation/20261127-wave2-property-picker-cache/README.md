# G05 — native descriptor lookup invalidation and per-call diagnostics

## Source status

This is a narrow successor to the published read-only picker change
`1cc7f696cfa01790c90c6d29273147d07da71b65`. It changes the downstream native
property catalog, the production picker loader, and appends focused tests to the
existing hosted test file. It does not change the picker View/VM, the read-only
manifest policy, initialization/provisioning services, Native contracts, stored
properties, or the three existing writing document Types.

Swift compilation, XCTest, native calls, simulator UI, visual review and physical
device execution are **NOT_RUN** for this successor. The original source inverse
and source-retention gate are source checks only. No product/admission gate is
opened by this change.

## Concrete failure and correction

The original catalog has cache-wide and per-Space generations for Type relation
reads, but native descriptor and diagnostic writes were unconditional. A native
query begun before `invalidate(spaceId:)` or `invalidate()` could finish after a
successful retry, replace its descriptor cache, or publish an older error. The
picker also read global `lastLookupDiagnostics` after awaiting the descriptor
array, so rows and diagnostics were not necessarily from the same call.

Native reads now capture the existing cache/Space revision with their cached
snapshot. Their descriptor and diagnostic publication is one locked operation
that admits only that revision. Conditional retirement of an invalid cache entry
cannot erase a newer revision. An invalidated asynchronous read propagates
`CancellationError`, including when its provider completes normally and the
calling Task has not been cancelled. It cannot complete the picker as an empty
or failed search or proceed to a legacy provisioning retry.

The read-only picker consumes one `TorahNativePropertyLookup` containing its own
verified descriptors and failure reasons. The existing array-returning and
nonthrowing catalog entry points remain wrappers with their prior provisioning
defaults. The public diagnostic accessor remains available to legacy consumers.

Two other writers use the same revision fence: the synchronous storage fallback
and the descriptor portion of `refreshAfterBootstrap`. Their existing behavior
is retained for a current revision. A nil cache or diagnostic argument preserves
that field as before; incomplete lookup results are not newly installed as a
complete cache. Existing Type relation generations and writes are unchanged.

This is an invalidation fence, not a Native freshness or ACL generation contract.
Two reads admitted within one unchanged revision may complete in either order;
each caller nevertheless receives its own descriptors and diagnostics. The
legacy global IdentityStore race remains outside this picker-specific change.

## Focused hosted regression inventory

All original `PropertyCreationSearchTests` and `PropertyPickerReadOnlyLookupTests`
source remains the exact 19,495-byte prefix (SHA-256
`6f17a932410b59369eaade81bfbabf08362a22593358c2c90201ecfe8c65166a`). The
unchanged nine original search methods and three read-only methods remain 12
methods / 16 cases. The separate six selection methods are untouched.

The appended suite is `PropertyPickerNativeLookupRevisionTests`, with three
methods / six cases:

| Exact method | Cases | Actual production boundary exercised |
| --- | --- | --- |
| `invalidatedNativeReadCannotCompleteTheProductionLoader(mode:)` | `space-success`, `space-failure`, `all-success`, `all-failure` | Suspend the old real SearchMiddleService read, invalidate Space/all, finish a fresh production loader lookup, then complete the uncancelled old provider. Require cancellation of the obsolete loader, retained fresh descriptor IDs and empty current diagnostics, and zero bootstrap calls. |
| `invalidatedBootstrapRefreshCannotReplaceTheRetry()` | 1 | Hold the original post-bootstrap descriptor refresh, invalidate and complete a fresh read, then release the old native descriptors. Require the fresh cache/diagnostics and no unexpected Type read or provisioning. |
| `invalidatedSynchronousStorageReadCannotRepopulateCache()` | 1 | Trigger Space invalidation at the original synchronous storage read boundary before returning old verified descriptors. Require their rejection, then a fresh storage read and cache hit. |

The provider fixture uses the real `ObjectDetails`, native definition keys,
format 11, read-only value and sourceObject checks. It does not inject a finished
VM result. Its ten-second wait is only a future failure deadline; progression is
driven by the actual provider continuation. No test was executed while preparing
this source.

Exact future selectors use the `AnytypeTests` target and the suite/method names
above, qualified by actual compiled enumeration on the matching shared product.
The read-only predecessor's new three methods / seven cases and its affected
original cancellation methods remain separately pending. Existing hosted
Properties/Core plans do not automatically select the new suites; a separately
reviewed exact-source consumer update is required. No old selector or historical
result is relabelled as this regression's acceptance.

## Provenance and integration

`candidate-manifest.json` binds all three original and changed Swift hashes.
`source-inverse.json` records an actual full reverse patch to the three exact
published preimages. The dependency source receipts bind `PropertyDetails`
Sendable conformance, `ObjectDetails`, `SearchRequest`, and the native descriptor
definitions to the same published commit.

The source map keeps all 130 rows. Only the catalog/loader/test shared or
replacement blobs in rows 121, 122, 123, 124 and 129 change, with an append-only
validation note. All other row content and top-level metadata are preserved.
No additional upstream VM seam or exception-register edit is introduced.

Independent reviews and the original source-retention gate are retained beside
this document when published. Wave3 remains the owner of final-source
integration, the single shared Apple build, admission and actual test dispatch.
