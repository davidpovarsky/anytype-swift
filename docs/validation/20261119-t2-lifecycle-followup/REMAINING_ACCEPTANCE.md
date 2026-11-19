# T2 acceptance map at the lifecycle correction

Source reviewed: `16b7493fa05bdc3abbae190c6e6c364c81874eea`, based on lifecycle `36757c8389006c6d30bf8f73997fcd928330601d` and guard correction `cab855d95c74f4f45eeacd07a6b1b6334151c138`. This map is a source/requirement inventory, not a new native acceptance receipt. App capability remains OFF.

## Requirement and evidence authority

The active tasks are [native two-client acceptance](https://app.asana.com/0/1219604672449660/1219604672452040), [native architecture](https://app.asana.com/0/1219604672449660/1219604675985609) and [full T2](https://app.asana.com/0/1219604672449660/1219604770636937). Their active November authorization supersedes the preserved historical pause and October lack-of-fixture statements. The original [RFC at 5641eab](https://github.com/davidpovarsky/anytype-swift/blob/5641eab469141bf99133cd42eb9cdea7113f12bc/docs/pinkha/torah-integration/T2_NATIVE_STORAGE_UPSTREAM_RESEARCH_2026-10-18.md), SHA256 `b396dd37dbef700205508e2bf6c81c65c95eb848b74f493a2d1d7d3c5a96541e`, supplies the sixteen adversarial rows below. Existing implementation choices are stated explicitly rather than silently treating every original proposal as already implemented.

The RFC tiers are: A source analysis; B component/native tree tests; C actual middleware persist/close/reopen in a disposable Space; D independent syncing native clients; E actual iOS acceptance. A passing component test does not establish its complete C/D counterpart. Native clients in the present fixture are two devices of the same account, not separate members with independently revoked grants.

Guard-only source `cab855` has independently qualified component/registry and real concurrent-REPLACE evidence at [44567040832](https://github.com/davidpovarsky/anytype-swift/actions/runs/44567040832) and [44567047394](https://github.com/davidpovarsky/anytype-swift/actions/runs/44567047394). Lifecycle `36757` has a qualified component PASS, a registry test compilation failure and a later client-controller failure after the four-process offline/reopen baseline. Those failures remain preserved. At exact corrective source `16b749`, original artifacts now qualify component/registry [44576342081](https://github.com/davidpovarsky/anytype-swift/actions/runs/44576342081), concurrent REPLACE [44576349959](https://github.com/davidpovarsky/anytype-swift/actions/runs/44576349959), dedicated generated RPC [44576585262](https://github.com/davidpovarsky/anytype-swift/actions/runs/44576585262), process crash [44580495418](https://github.com/davidpovarsky/anytype-swift/actions/runs/44580495418) and observed REMOVE/re-ADD [44580502296](https://github.com/davidpovarsky/anytype-swift/actions/runs/44580502296). Exact counts and archive hashes are in `README.md` and the `VERIFIED_*` reports. The following remaining gaps are not removed by those scoped passes.

## Sixteen-row map

| RFC row | Existing evidence or implementation | Remaining requirement and category |
|---|---|---|
| 1. Concurrent A+B, both delivery orders | The native offline baseline creates independent branches, merges original signed changes and retains both unique adds. Component tests cover replay orders. Baseline requalified at `16b749` in all three tail runs. | **Evidence gap:** do not label one controlled reconnect as every forced delivery order. |
| 2. Lost response, identical retry | Native fixture discards the original client-byte reply, observes one signed commit, then forwards identical bytes and verifies unchanged history/response/sequence. | **Existing regression gate:** included in every offline tail. This is lost client reply, not packet loss or power-loss proof. |
| 3. Same ID, different payload | Local typed collision leaves the original intact; independent offline variants remain visible as a conflict with no selected winner. | **Existing regression gate:** included in the offline baseline and component suite; keep ordered local rejection distinct from merged concurrent variants. |
| 4. Remove/add and remove/remove | Offline baseline has concurrent observed removal and unobserved unique adds. The unchanged observed-remove/re-add tail now passes at `16b749` in run 44580502296, with signed 8→9→10→11 and three identical REMOVE requests. | **Evidence gap:** do not equate that fixed sequence with all delivery permutations. |
| 5. Concurrent updates and provenance | Corrective REPLACE run 44576349959 proves two successors, all six exact retries and retained predecessor provenance at `16b749`. The current projection explicitly orders by bytewise OperationID then ClaimID. | **Product/semantic gap:** the RFC's causal display ordering is not implemented/proven; the bytewise fallback is deliberately labelled as such. |
| 6. Invalid versions/canonical bytes/hash | Component envelope validation and generated RPC schema/error/size controls exist; the real account byte helper rejects bad versions/kinds, empty payload and missing targets before root creation. | **Existing regression gates:** component, generated RPC and account baseline at the corrected source. No claim that every malformed remote branch is exercised by two complete accounts. |
| 7. Branch/replay/snapshot/compaction/reopen | Native replay, cold recovery and disconnected reopen exist. Private operation snapshots are rejected by the current format; records/tombstones are retained. | **Product/contract gap:** no snapshot/compaction/GC implementation or safe tombstone horizon is exposed. Disk reopen is proven separately and cannot stand in for compaction proof. |
| 8. Target deletion/movement/create-delete race | Reviewed app → settings → target → private tree → ACL lease; genesis deletion-history checks; component cancellation/cache/state/lease tests. Actual account baseline deletes a block and preserves raw journal history. | **Evidence gap:** real generated-RPC create/delete races and same/cross-Space movement. **Product/API gap:** no public read-by-ID/orphan representation after target deletion; current ReadTarget refuses unavailable targets. |
| 9. Revoked membership/grants/ACL race | Real signed ACL component tests cover reader/guest/writer denial after revocation, head changes, commit guard and release-before-notification. | **Evidence gap:** authenticated multi-member native transport and revocation delivery races through the actual account/RPC boundary. A disconnected replica cannot be claimed to know an undelivered ACL change. |
| 10. Independent offline reconnect | Two original account stores and peer identities run in separate Docker processes/namespaces with actual detach/reconnect, without injecting native history. Baseline is qualified at `16b749` in each tail. | Native Heart evidence does not establish two iOS applications. |
| 11. Crash after commit before response | Run 44580495418 at `16b749` kills the owned process after durable commit and reopens the same store without network before identical-byte retry. Original 9-entry history, full snapshot and local sequence remain unchanged. | The killed process is not a PASS; one recovery PASS is counted separately. Power loss remains outside this proof. |
| 12. Target/source indexed reads, lag/watermarks | Store has exact target, operation-ID and claim-receipt indexes. ReadTarget returns bounded complete results or an explicit limit error. LocalAppliedSeq and verified local heads are exposed. | **Product/API gap:** no reverse-source query/index, cursor pagination, index-progress watermark or bounded watermark reconciliation API. LocalAppliedSeq is not a cross-replica causal/index clock. |
| 13. 1k/10k performance and bounds | Input limits, projection result bounds and reply-size rejection exist. | **Evidence gap:** actual 1,000/10,000 operation timings, memory, cancellation and read behavior. **Product/API gap:** paged/subscription behavior from the RFC is not exposed. A limit constant is not a performance result. |
| 14. Invisibility and exports | Native private type/source/export guards; account baseline verifies ordinary ObjectShow/Search positive controls, private absence, denied private access, and eight ordinary JSON/PB exports. | **Evidence gap:** explicit native backlinks/editor/undo paths and complete template interaction. **Product/contract gap:** ordinary export exclusion does not satisfy the separate backup recovery requirement. |
| 15. Backup/import/account switch isolation | Four sequential account processes exercise close/reopen and post-stop read/append denial. | **Product/contract gap:** no versioned private backup/import stream or explicit backup unsupported-data contract was found. **Evidence gap:** actual account switch with in-flight RPC/subscriptions, stale cursors/decrypted cache and restore. Sequential Stop is not concurrent account switching. |
| 16. Old/new Heart and downgrade | The four-phase fixture runs new-create/new-reopen/legacy-edit/new-recover; legacy rejects private content type, edits ordinary content and preserves original private bytes. | **Evidence gap:** disposable backup/restore downgrade and a broader version matrix. **Release-family gap:** negotiated Swift adapter/wrappers/runtime/iOS packaging and legacy migration ledger remain separate work; old-engine results do not imply new-engine parity. |

## The seven client source files and their actual selections

All seven files are compiled into the source-bound native fixture, but compilation does not execute every scenario. The three tails are intentionally mutually exclusive.

| File in `Tools/TorahNativeOperations/two_clients` | Executed scope |
|---|---|
| `native_client_phase_test.go` | Cold creator/recovered bootstrap; dispatches the offline helper when selected. |
| `native_client_boundary_test.go` | Exact byte boundary and immediate read-error/readiness controls. |
| `native_client_offline_test.go` | Actual partition, independent writes, lost reply, collision, union and reconnect; plus bounded controls. |
| `native_client_reopen_test.go` | Two new processes open the two original stores with network disabled. |
| `native_client_crash_test.go` | Additional crash commit/kill/recovery path only for `t2-native-clients-crash`. |
| `native_client_observed_remove_test.go` | Additional two-role remove/re-add tail only for `t2-native-clients-observed-remove`. |
| `native_client_concurrent_replace_test.go` | Additional two-role concurrent successor tail only for `t2-native-clients-concurrent-replace`. |

All three tail routes have now passed at the same reviewed source `16b749`, with original artifacts independently qualified. Repeating bootstrap or plain offline independently is unnecessary because each tail already requires and verifies them.

## Exact boundary of the generated RPC gates

`rpc/overlay/core/pinkha_torah_rpc_test.go` tests generated protobuf schema/roundtrips, error/receipt conversion, bounds and external authorization scopes. `rpc/overlay/clientlibrary/service/pinkha_torah_rpc_wire_test.go` calls the real generated byte entry with no active account. These seven selected methods form the dedicated `t2-native-rpc` route.

`account_rpc/native_rpc_account_test.go` is compiled into the separate actual account fixture. Its `t2CreateNativeRPCOperation` calls the real generated byte entry and checks that read-only absence, invalid versions/kinds, missing block, empty payload, and valid-shape first REMOVE/REPLACE with an unknown predecessor leave no private root. Those account assertions are included in the four-phase account-wire baseline of each native-client build. Cancelled first-create is covered by the typed native handler fixture; the account byte helper does not claim cancellation or a concurrent deletion race.

## Concrete next coverage before broader implementation

1. **Complete:** qualify the corrective component, registry, generated RPC and concurrent REPLACE runs from their original artifacts, with required names, source pins, exact retries, source-bound original-store identities and cleanup.
2. **Complete:** run and qualify the existing crash and observed-remove tails at the same corrective source. Older successful evidence remains historical scope.
3. **Next bounded candidate, not runtime acceptance:** real generated-byte first ADD paused after preload versus block deletion; existing-root append versus a queued block-deletion target lock; and append versus actual AccountStop's writer lock. A separate local test composition adds signal/wait observations around the original lock and storage calls, forwards original arguments/context/guard and storage call once, and preserves release ordering. It has not been compiled or dispatched. No generated-byte cancellation is claimed because that entry exposes no caller cancellation context. Signed settings deletion, template uninstall and account switching remain separate missing cases. Controlled SmartBlock mocks cannot be labelled whole-account race proof.
4. Keep standalone Space.Close unresolved until its actual existing-closing-cache-entry timeout path is reproduced or native storage fencing is demonstrated. The reviewed application Stop lease does not prove every independently initiated Space-close sequence.
5. Address the query, orphan, ordering, backup and release-family gaps as explicit product/architecture work against the active task prerequisites. Adding tests alone cannot supply an absent API. No new public RPC/canonical format, unsafe compaction, personal-Space experiment or new-engine edit is implied by this inventory.

## Source locations for the product findings

The following files are pinned by the corrective commit and its manifests:

- `Tools/TorahNativeOperations/overlay/core/block/editor/torahops/projection.go`: exact-target bounded fold and explicit bytewise display fallback.
- `Tools/TorahNativeOperations/overlay/core/block/editor/torahops/store.go`: actual indexes, internal ReadOperation and retained receipt/claim representation.
- `Tools/TorahNativeOperations/overlay/core/block/editor/torahops/native_host.go` and `native_commit_guard.go`: current authority, durable boundary, replay and receipt behavior.
- `Tools/TorahNativeOperations/overlay/core/block/editor/torahopsobject/target_lease.go`: live settings/target lock and genesis-history validation.
- `Tools/TorahNativeOperations/overlay/core/pinkha_torah_operations.go`: application/Space scope, absent-root operation restrictions and current target preflight.
- `Tools/TorahNativeOperations/rpc/heart-rpc.patch`: actual Append/ReadTarget schema; no cursor/source-query/orphan API.
- `Tools/TorahNativeOperations/account_lifecycle` and `account_rpc`: actual lifecycle, export, legacy and byte-boundary proof scope.
- `Tools/TorahNativeOperations/run_native_clients.py` plus each tail controller: mutually exclusive source-bound selections, privacy-safe evidence and owned cleanup.
