# V5-R2 genuine original native controls — review packet, not executed

## Status and exact source

This packet prepares 33 new full-entrypoint native observer controls and 12 new strict original protobuf/replay-admission controls. No Go build, test, native call, package install or CI dispatch has run. Only gofmt, Python AST parsing and the separately retained no-Go source-composition proof have been performed. The complete source/fixture/runner still requires root review before execution.

Product source is the unchanged frozen candidate-v5 packet: SOURCE_REVIEW_INDEX.json SHA 3487663a830281fc33bef1f944d68047c784819918f03dc76341bd35413e7581; SOURCE_MANIFEST.json SHA c091fa3696f8b3f2610997aed65c988010529c59caeac3d53a47c1d3e028ac4d. Root's independent V5 receipt verifies all 138 payloads, 113 immutable source inputs, five working product files, frozen V4 and unchanged strict source. V4 and V5 review folders are copied unchanged under reviews.

Both previous controls-v5 and controls-v5-r1 packets remain unchanged. The strict test source stays at V5-R1; R2 changes only execution wiring. V5-R1 changed only the initially insufficient Snappy/nil Fields assertions, preserving the three full runtime files byte for byte. Its exact replacement list, delta and independent review are retained. The corrected strict source SHA is 2cd96e7827eb5a50353a6e3d649aaf2a6f97a1db6dc0e86bfa6ab58e756006d2. There is no executed RED or GREEN claim: the two gaps were found by source review.

## Genuine fixture and limits

The native fixture calls original application.WalletCreate and AccountCreate in LocalOnly mode with local network sync disabled, uses original CreateWorkspace for a regular Space, waits for the actual Space and invokes the actual original creator's additive FixedSchemaObserver. All account/database data lives in task-owned temporary storage. The existing integration helper is not called because it logs its mnemonic. Fixture code does not log wallet secrets, account responses or event bodies; the actual event callback discards events.

Ordinary application/account/Space/schema creation belongs to fixture setup. The observer itself has no new mutation API. Deliberate corruption controls use the actual original any-store database/transactions to modify a disposable row; they are not evidence that the observer writes. This suite does not measure a globally quiescent database or prove absence of all background native writes.

There is no FakeSpace, smarttest fixture, replacement database, alternate graph engine, substituted ACL or caller-supplied signature verifier. Three observation decorators embed actual native interfaces and override only transaction/query tracing. All state, authority, decoders, queries and real transaction operations delegate to the genuine runtime. The two error-propagation controls inject labeled errors only after actual native operations; they prove error joining, not a naturally occurring SQLite failure.

The package's original test files may compile as ordinary Go test dependencies. The runner selects only the two newly named parents and their exact new child cases. An immutable original package-source inventory found no TestMain or init function in those original target test files. No historical passing suite is replayed.

## Actual pooled-reader/ACL interleaving

The pinned Heart anyStoreConfig sets four actual read connections. The fixture holds three real ReadTx leases, starts the full public ObserveFixedSchema call and signals only after that call has frozen native scope and obtained the fourth real reader. A second owned goroutine takes the real original ACL exclusive lock and invokes original RecordsAfter, which needs a database reader. It cannot complete while the actual pool is full.

The fixture then lets the observer perform its genuine snapshot and original Commit. Only after the reader is released may the pending original ACL storage read drain, release its lock and let the observer continue through original verification/replay and return a match. The event assertions preserve only proven ordering; they do not assume scheduling order between an after-Commit notification and the other thread's completion. All leases/goroutines have a finite context deadline and owned cleanup. This case enters the complete observer, not a private helper-only path.

## New cases

### Actual original native runtime (33)

1. OriginalRelationMatch
2. OriginalObjectTypeMatch
3. ExactNativeRootOnly
4. NativeLocalMissingWithoutCreation
5. ActualLocalZeroCounterAccepted
6. NativeComputedRemoteCounterAccepted
7. NonzeroCounterMetadataConflict
8. FractionalCounterCannotDefaultToZero
9. StoredOrderMustMatchNativeTraversal
10. OlderNativeCommonSnapshotAccepted
11. UnrelatedNativeSnapshotCannotBecomeCommon
12. ExplicitLongtextPresenceCannotDefault
13. ArchiveUsesOriginalNativeLinkTree
14. WrongDerivedHeaderUnavailable
15. OriginalPooledReaderAndACLLockOrder
16. FullACLIntermediateRecordRequired
17. FullACLExtraRecordRefused
18. OriginalACLSignatureCIDVerification
19. SecondSnapshotSeesInvisibleEncodedRowChange
20. SecondSnapshotSeesExtraNonHeadChange
21. RealNativeOperationsPropagateInjectedIteratorCloseCommitErrors
22. RealNativeOpenFailurePropagationStillReleasesReadTx
23. MissingOriginalSpaceStateUnavailable
24. PersistedStateACLIdentityMismatchUnavailable
25. PersistedStateSettingsIdentityMismatchUnavailable
26. AnotherRealSpaceHeaderCannotBindCurrentSpace
27. ActualSpaceHeaderSignatureCIDFailureUnavailable
28. SpaceHeaderNativeTypeCannotDefault
29. MissingActualSettingsRootUnavailable
30. ActualSettingsRootSignatureCIDFailureUnavailable
31. SecondSnapshotSeesCompleteStateRowChange
32. SecondSnapshotSeesCompleteSettingsRootRowChange
33. CanceledCallerCannotPublishObservation

The first match case explicitly asserts the actual current V1 header and valid empty ACL-root SpaceId. The metadata cases validate the retained native settings identity, original signed header/settings linkage and both complete encoded row comparisons. Legitimate state-hash changes may conservatively return ChangedWhileReading; that result must not be reported as a stable match.

### Strict original decoder (12)

1. UnknownDataTypeStrictOnlyRefusal
2. OriginalPlainAndSnappyTagsAccepted
3. InvalidNativeSnappyErrorPropagated
4. SnapshotBlockFieldsRefusedBeforeReplay
5. CreatedBlockFieldsRefusedBeforeReplay
6. BlockSetFieldsEventRefusedBeforeReplay
7. NilSnapshotFieldsPreserved
8. NilCreatedFieldsPreserved
9. NilFieldsResetEventPreserved
10. EmptySnapshotIDCannotBeSynthesized
11. EmptyCreatedIDCannotBeSynthesized
12. MissingOriginalEventRefused

The compression negative uses the same genuinely valid original protobuf input for ordinary success and native Snappy DecodedLen failure, then requires errors.Is against the actual native compression cause. Nil reset tests require proto.Equal and direct nil checks for snapshot, create and event paths. These twelve controls exercise original protobuf/Snappy/strict admission directly; they do not independently establish an application account or schema provisioning.

## Reviewed execution route proposed, not invoked

PROPOSED_WORKFLOW.yml is a source proposal only. It has not been installed into .github, pushed or dispatched. The proposed dedicated branch is codex/otzaria-original-schema-native-20261122 in the owned Anytype control repository. Root must compose these exact sibling packets at docs/pinkha/torah-integration/native-fixed-schema-observer-20261122 and review the final source before one trigger push.

The route reuses the existing original xcode-27/macOS ARM64 infrastructure, Python 3.12 and exact Go 1.26.5. The runner refuses another platform/toolchain, a dirty or different original Heart checkout, stale work/evidence directories, changed source packets, changed go.mod/go.sum/native checksum list, or a different execution manifest. It applies original r14 byte for byte, validates its existing inventory, then applies the reviewed observer patch and copies the four exact new test files.

Only the pinned original build_custom_heart.py fetch_tantivy function is imported; its original checksum and safe extraction remain unchanged. The helper's main, old regression-package list, gomobile and iOS framework build are not invoked. Only the real darwin-arm64 Tantivy v1.0.6 archive is needed. No toolchain downgrade, module replacement or fake dependency is permitted. R2 calls only that unchanged original function through prepare_original_tantivy.py in a separately owned finite child. Both its 600-second stage maximum and the aggregate absolute deadline apply; a per-socket setting is not treated as a whole-stage timeout. The exact extracted native library file set, sizes and hashes plus the native archive hash are retained before and after linking/execution.

The runner records the actual Go binary hash/path/version, Xcode/compiler/SDK version output, actual declared Go package/test/embed/native source hashes, native binary hashes/build information, exact command streams and strict test2json case results. The declared closure must be nonempty, include both exact original selected packages and cover all five candidate plus four test source files by their reviewed hashes. Each test executable hash is durably recorded before execution and compared with its hash after execution. These are runner observations: executable bytes are excluded from the uploaded evidence, so independent root rehash of those bytes is not claimed. Declared inputs do not claim to enumerate all generated cgo products or every Apple SDK header. Product/module/declared-input bytes are rechecked after the selected new controls.

The process environment retains actual system HOME/PATH and selected compiler settings but does not forward CI credentials or arbitrary API keys into the disposable runtime. TMPDIR is a freshly created child of the owned work path; it is removed in finally and cleanup failure fails the result. No existing user account path is touched. Artifacts include only execution receipts, declared inputs and command streams; compiled binaries and account/wallet directories are outside the artifact path. Wallet/account data directories are excluded from the artifact; command streams remain explicit original-runtime evidence and the fixture never deliberately emits a mnemonic or private account response.

## R2 process ownership and aggregate budget

Every command writes atomic STARTING intent before spawn and RUNNING with its exact owned PID/process group before awaiting. Timeout, signal request/result, parent reap, process-group drain and terminal outcomes are recorded incrementally. A timed-out command always has a failing effective exit code even if its parent responds to TERM with actual exit code zero; actual and effective codes remain separately visible.

The cleanup checks the newly created process group even after its parent exits, escalates only that owned group if descendants remain, and refuses to remove the owned disposable TMPDIR if drain cannot be established. A command that unexpectedly leaves descendants also fails. No global process discovery/kill or existing account cleanup is used.

The first workflow step sets an absolute deadline 6,900 seconds after the first workflow step. All child waits use its remaining budget with a monotonic clock, reserving 180 seconds inside that deadline for cleanup/evidence and a further 300 seconds before the 7,200-second outer job timeout for upload. Individual maxima cannot accumulate beyond this global bound; expired budgets refuse to spawn another child. Checkout/toolchain setup time consumes the same wall-clock budget. The real cleanup/status receipt, not a test-only return code, determines success.

## Actual source-composition proof, no Go execution

The single owned source job job_f2d920e21a43 completed PASS_SOURCE_COMPOSITION_ONLY at 09:23:44 UTC in 7.02 seconds. It materialized 21 original immutable Git blobs for the affected paths, checked/applied exact r14 and validated all 35 inventory outputs, then checked/applied V5 and validated all five product outputs, then copied the four exact new test files. Module/native checksum bytes and the nine actual owned worktree product/test files remained unchanged. It never ran Go, a build, a test or a native runtime.

The full original blob identities, commands, streams, submitted/actual script and composed affected source files are retained under source-composition. This is a partial affected-source materialization rather than a full compiled repository. RESULT SHA ca0079ab0011603e2e707fcf3d1638749f9e19dd2b118445db409cb92893f7f5. The original V5 working tree was not patched by this proof.

## Remaining gates

No native acceptance, production fixed-schema registration/repair, original annotation object materialization, selected-Space create permission, opaque identity/body receipt, durable identity writer, StageB–F completion or delivery ACK is established by this unexecuted packet. Existing product/CI gates remain open. The proposed repair/crash/reopen controls remain pending because the current observer has no repair API.
