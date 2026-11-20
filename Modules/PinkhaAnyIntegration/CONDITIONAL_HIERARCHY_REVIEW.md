# Conditional hierarchy write review — 2026-11-19

## Observed failure and scope

The unchanged hierarchy acceptance probe on native v7 completed 13 of 20 checks and then failed `guarded_bin_exact_retry_preserves_native_version`. It finished in 16.56 seconds. The diagnostic watchdog armed, but never activated; neither control client sent a request. This run therefore supplies no new explanation or fix for the earlier intermittent Windows HTTP timeouts.

The original result is retained in the [v7 watchdog archive](../../Tools/AnyEngineValidation/evidence/guarded-hierarchy-native-v7-watchdog-v1/checkpoint.json). The probe did not record the historical before/after version maps. The specific changed leaves cannot be reconstructed from its metadata-only trace.

The pre-fix Swift `AnyGuardedHTTPHierarchyRecordStore.setArchived` always sent a nonempty `collections` set, even when the ordered membership array is already correct. Native CRDT `gatedSet` writes the supplied value and its newer version without testing value equality. The object GET path returns the stored record, including `_ver`, without synthesizing a new version. This is a concrete source explanation for the failed retry assertion. The corrected v8 rerun below passed all twenty original assertions.

## No-history retry contract

A client-only early return would skip current authority and target validation. The agreed native contract instead uses the dedicated conditional property route with an empty patch, advertised as `conditionalPropertiesNoop=1`.

The no-op must run after the same target-tree lock, actual tree-readiness check, captured row-sequence comparison, current Type and Collection definition locks, owner-attachment check, descriptor callback, and local prevalidation as a real conditional write. A local-only `NativeConditionalNoop` flag is needed because an empty operation list otherwise does not request all current membership definitions or exercise field-based owner attachment.

Only one existing object record with no operations and no upsert qualifies. The final `CheckCurrentWrite` check provides the authority linearization point while the object and definition locks remain held. It returns record identity without invoking `AddContent`, appending a CRDT change, or advancing history/application sequence. Stock routes and ordinary nonempty operations retain their existing behavior.

The Swift adapter must preserve exact membership order and all unrelated memberships, send an empty patch only for identical arrays with the explicit capability, retain all run/account/authorization checks, and fail closed if that capability is absent. It must not substitute a normal set or an unguarded route.

## Separate stale-snapshot issue

Source review found a separate limit in the v7 HTTP precondition. It compares the client's full `_ver` with the current row, then reads a fresh server `_applySeq` and passes that fresh value to the locked SDK write.

The following combined witness was first derived from source and was then reproduced by the actual properties controller, system handler, and native application-sequence allocator:

1. A collection array is set at version v1.
2. An unrelated property is set at v3, advancing `modifiedAt` and `modifiedBy` to v3.
3. A client captures the complete version map and memberships.
4. A valid concurrent collection `$addToSet` at v2 arrives late.

The collection operation passes its field gate because v2 is newer than that field's v1 set. Commutative add/pull operations deliberately do not update the field's `_ver`. Their derived modification stamps lose the LWW comparison against v3. Membership content can therefore change while the complete version map stays equal; the application sequence advances.

`TestAddToSet_DoesNotUpdateOrder` and `TestSystemPropertiesHandler_ModifiedAtOutOfOrderConverges` independently cover these two behaviors. The HTTP handler's freshly substituted sequence cannot detect the client's older snapshot.

The strict v8 contract requires an explicit `conditionalPropertiesApplySeq=1` capability and mandatory caller-captured `ifApplySeq`, bound to the original `ifStartedAt` and full `ifVersion`. The same captured sequence must reach the final locked comparison, with no refresh-and-retry. This fence is independent of the no-history optimization.

## Implemented client behavior and completed evidence

Integration now uses the shared immutable `AnyConditionalPropertyFence` for every native conditional rename, placement, archive, and restore request. Its decoder validates required version, positive exact integer sequence, and bounded original run. The native adapter requires the sequence capability before dispatch. Exact archive/restore retries require the no-op capability and still dispatch an empty native patch through all authorization checks.

A persisted `AnyHierarchyPlacementPlan` retains its original fence. Older plans may decode for review, but a native repository refuses a missing fence or another engine run before reconciliation or mutation. It also refuses conversion of a native plan to generic writes. Generic stores and their existing retry behavior remain covered.

| Evidence | Result and limit |
|---|---|
| [Actual commutative witness](../../Tools/AnyEngineValidation/evidence/native-v8-commutative-witness-v2/result.json) | `TestNativeConditionalMembershipLateOperationLeavesFullVersionUnchanged`: **1 passed, 0 skipped**, source stable. Actual controller/handler/allocator proof; not the corrected HTTP route or hierarchy acceptance. |
| [Integration component receipt](../../docs/any-engine-port/evidence/20261119/conditional-property-components-v1/result.json) | **35 tests in 2 suites passed**, with all 20 current Integration production source files compiled. Source, cached objects/modules, and dependency source pins remained unchanged. |
| [Integration compiler producer](../../docs/any-engine-port/evidence/20261119/conditional-property-components-v1/integration-producer.json) | Fresh isolated module, object, and module wrapper for downstream Host validation; no shared cache replacement. |

The witness receipt SHA-256 is `9724da743e93613b5e79ee20930985eca22fc9d996eec9619cc6a849a1865739`. Its [archive](../../Tools/AnyEngineValidation/evidence/native-v8-commutative-witness-v2/archive.json) retains the initial toolchain/cache setup failure with **zero tests executed** as well as the successful bounded run.

The Integration receipt SHA-256 is `f994f762773963218a4dcd246b416a32db1e8749119b4b7e3912ececd0b71776`; its executable SHA-256 is `b7e528d2a474ce8065c0b48ab6c2733c95ae0cc969a0d8b203e2803ddb7ad38b`. The 35 tests cover 23 hierarchy cases and 12 fence/request-contract cases, including legacy/run refusal, equal-version sequence changes before and during dispatch, generic-store preservation, exact empty requests, capability refusal, malformed metadata, and membership ordering.

## Corrected native acceptance ? 2026-11-20

The unchanged twenty-check hierarchy probe passed **20/20** on a newly created disposable Space using the exact v8 native binary and the plain production Engine transport. The executable itself finished in 1.421 seconds; the complete external runner, including process identity, source/pin checks and Space setup, finished in 9.49 seconds. The runner observed the same native PID, account, engine run, executable hash and source-manifest hash before and after. No watchdog, control-response substitution, retry, timeout increase, or production URLSession change was used.

| Evidence | Executed result |
|---|---|
| [Native SDK contract tests](../../Tools/AnyEngineValidation/evidence/native-conditional-properties-v8-sdk-tests/result.json) | **17 top-level tests / 29 cases passed**, zero failures or skips; no-op history and current signer, owner/definition locks, original sequence, deleted targets, and the actual commutative witness. |
| [Native HTTP contract tests](../../Tools/AnyEngineValidation/evidence/native-conditional-properties-v8-server-tests/result.json) | **19 top-level tests / 47 cases passed**, zero failures or skips; strict numeric guards, original run, no-op preservation, owner/collection authority, metadata, and dynamic document policy. |
| [Host property component tests](../../docs/any-engine-port/evidence/20261119/host-property-fence-components-v1/result.json) | **23 tests passed**, including captured-fence propagation and exact acknowledged readback/Undo. |
| [Complete Probe build](../../Tools/AnyEngineValidation/evidence/guarded-hierarchy-v8-components-v1/result.json) | All four current Probe source files compiled and linked against the tested Integration module and unchanged plain Engine/Kit/Crypto object closure; source and retained inputs remained stable. |
| [Actual native hierarchy acceptance](../../Tools/AnyEngineValidation/evidence/guarded-hierarchy-native-v8-v1/result.json) | **20/20 passed**, exit zero, no timeout; exact archive retry, four competing writers, stale/ABA/cycle/run/fallback refusal, live hierarchy observation, restore/body identity, safe folder removal and a fresh reader. |
| [Original assertion comparison](../../docs/any-engine-port/evidence/20261119/guarded-hierarchy-v8-probe-source/result.json) | All twenty original assertion expressions are byte-identical after newline normalization. Only six original record/run captures and the reported v8 scope changed. |

The native executable SHA-256 is `4856c7214f56dded249095624ea63e3f99b4b340483e8e6f2785163d16a98089`; its source-manifest SHA-256 is `484d377a89b3e53ccab28bbf8defe223441e85db398c40ee5626d71ddc521289`. The plain Probe executable SHA-256 is `5f5d96df90b93ae23d4aa68aed6fd150db8cc4e7c88396275aa09094bb5629b6`.

The [runtime archive](../../Tools/AnyEngineValidation/evidence/guarded-hierarchy-native-v8-v1/archive.json) binds the exact runner, original-assertion diff, executed source, logs, fixture and native manifest. Its result SHA-256 is `fd6f6986c14ce2166ff3a3a29376dad74a2873ca74df42c487e655cf076897fe`; archive SHA-256 is `8d6a56c2bc23735937dd8c77071dbc0eeee65d2150c89c23470dacf5ddfd0555`. The separate [build archive](../../Tools/AnyEngineValidation/evidence/guarded-hierarchy-v8-components-v1/archive.json) retains 45 source, command, log and receipt files without duplicating executables or object caches.

The prior interruption occurred before any v8 runtime acceptance was launched; the completed executable was reused without rebuilding. The launcher Space remained untouched, and the newly allocated synthetic Space is retained. Cross-object folder removal remains a recoverable ordered sequence, not an atomic transaction. Earlier intermittent Windows transport failures remain unresolved and preserved; this successful plain run does not establish their cause or replace the separate Apple application acceptance gates.

## Covered focused verification

- Identical archive and restore requests execute native authorization but preserve version, application sequence, history, and unrelated memberships.
- Missing or incorrectly typed capabilities cannot dispatch an empty or unconditional fallback.
- Stale captured sequence, changed run, revoked signer, deleted target, detached owner, or changed/deleted definition refuses without append.
- The combined late-commutative witness changes membership while preserving full `_ver`; the new caller-captured sequence rejects the stale write.
- Nonempty archive and restore preserve ordered unknown memberships.
- The original twenty hierarchy assertions remain unchanged.

## Reviewed source fingerprints

Paths below are relative to the native Any checkout, with SDK paths beneath `.runtime-artifacts/sdk-source`. These fingerprints describe the inspected pre-fix source, not an executed new native binary.

| Source | SHA-256 |
|---|---|
| `internal/server/pinkha_property_condition.go` | `e0fe6099f8082403850bf192b5b887bcc200857a03e99c9f8c0117d96f4c029e` |
| `internal/server/handlers_properties.go` | `b1279dbd52ec09c65e4e8ddb1653f938c955f25dca7f834c16ec7c7d012f74ad` |
| SDK `internal/crdt/apply.go` | `7384c1ae73e0016b01b4e74e430f7092a30b4a07249edb97f873e39c885363f3` |
| SDK `internal/crdt/apply_test.go` | `d221fac704732b01505b4bd38b34b8421ebd7cae70c6d7b31645f832056eb2fe` |
| SDK `internal/properties/system.go` | `215c340a8a8e6444a2549a416d87d91747f71ff0a1b13e48fc85c1b8a143d570` |
| SDK `internal/properties/system_test.go` | `0c28e2828e9fed0120bc5e39cf1205b483a928485e92e96f1d4efa56f5892a98` |
| SDK `internal/object/current_writer.go` | `22fb16a6e1a0d8754fba1b60af8875c8f85f930594e64debedbd3771584865cf` |
| SDK `internal/commitguard/guard.go` | `68f71327b9e08ff6dd325b5b2954496874fe25ed05b9174a7df5234f81f90767` |
