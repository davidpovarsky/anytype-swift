# First native failure correction — V6 / R1

This packet is a source candidate for independent review. No Go build, native call, test, CI dispatch or second run has occurred for this correction.

## Actual baseline and retained scope

The actual original Heart run [45008694456](https://github.com/davidpovarsky/anytype-swift/actions/runs/45008694456), attempt 1, used control commit `382e5ac62575d4df533d5ad38286ca5a09049b45`. Both original packages compiled with Go 1.26.5 on macOS ARM64/Xcode 27 and the pinned native Tantivy dependency.

The native suite reported 17 raw PASS and 16 FAIL. The strict decoder suite reported 12 PASS and no failure or skip. Four of the 17 raw native passes are semantically unproven because a generic unavailable assertion accepted the earlier archive decryption failure before reaching the intended schema error. The raw events and counts remain unchanged.

`PASS_FIRST_FAILURE_MAP.json` maps all 17 to the actual source order. For 13 cases, the asserted injected/cancellation cause or the necessarily earlier original snapshot/state/ACL validation is independent of the corrected decryption path. Generic unavailable cases did not log their errors; the map explicitly identifies that source-constrained limit and does not invent a runtime trace. These 13 and the unchanged strict12 are excluded from the next selection.

## Minimal product correction

Only `fixed_schema_replay.go` changes. The first run failed fourteen observer cases at the archive content decryption boundary. The observer incorrectly used the Space ACL read key directly. The pinned original `objecttree.readKeysFromAclState` derives a key for the actual tree ID.

The correction uses the same original `crypto.NewKeyDeriver(fmt.Sprintf(crypto.AnysyncTreePath, rootID))`, the retained original read key's `Raw()`, and `DeriveKey` before native `DecryptReuse`. Every original error propagates. No key bytes are logged, no codec or storage implementation is added, and no observer mutation/init/repair or fallback is enabled.

The actual strict decoder, snapshot/ACL/Space validation, original graph and common-snapshot semantics, immutable adapters, and two-snapshot comparison are byte-identical to V5.

## Native LocalOnly ACL fixture

The two ACL controls failed in setup at the original `AclClient.AddRecord -> nodeClient.AclAddRecord`, which requires a network acceptor unavailable to this disposable LocalOnly runtime.

The fixture now requires both actual original app `Config.IsLocalOnlyMode()` and empty actual original `nodeconf.Service.Configuration().NetworkId`. Pinned `spaceService.buildRecordVerifier` explicitly selects its native LocalOnly verifier in that configuration; the actual Heart regular-Space load does not override its private verifier dependency.

The fixture retains the already-running actual ACL and its original lock, builds an author-signed native `BuildSpaceOptionsChange`, uses the existing test-only `listtest.WrapAclRecord` to encode that record and derive its actual CID, and invokes that same native `syncAcl.AddRawRecord`. The helper checks actual one-record advancement and original persisted bytes. It does not construct or replace an ACL/verifier/store, fabricate an acceptor signature, call a fake Space, or assert network consensus acceptance. This is disposable test setup through genuine original components, not a new production local ACL API.

The LocalOnly verifier still validates original author signature/CID/content. Its absence of a network acceptor is an explicit original configuration limit. No result from these controls can establish consensus-acceptor signatures.

## Exact control changes and selection

The four masked negatives now require the original `ErrFixedSchemaStorage` plus their precise target cause:
- native snapshot reference/counter;
- stored order differs from original traversal;
- persisted common snapshot is not an allowed native ancestor;
- original derived header mismatch.

The two previously failed ACL controls now require the exact complete-chain cause or native `list.ErrInvalidSignature`. The latter changes only the actual author signature inside the original decoded record and re-encodes it using the original protobuf API; the stored CID remains unchanged.

The next proposed execution selects 20 original named cases: 14 prior observer failures, the 4 masked negatives, and the 2 failed ACL setups. The other 13 native and all 12 strict cases are excluded. All 33 original native bodies remain in the source file for exact ancestry; 27 bodies are byte-identical. Only the selected 20 may produce run events.

The inherited R2 runner retains its actual process-group ownership, incremental command receipts, irreversible timeout failure, absolute workflow deadline and owned cleanup, finite original Tantivy setup child, native-library file-set hashes, and before/after binary hashes. The source composition is original d984 + unchanged r14 + frozen V5 patch + the separately sealed one-file V6 patch. Declared dependency coverage requires all 5 product and 3 native test files in the actual selected original package closure. Sourceimpl compiles transitively but its passed strict suite is not selected or run.

## Evidence boundaries

The frozen V5, R2, run382 artifact and all prior reviews remain unchanged. The original 16 extra source inputs are retained with commit/blob/SHA identities; the any-sync bytes came from the already retained exact-commit archive, not a new download. Existing independent fixed-commit tree evidence can verify these added identities.

The runner records its observed toolchain path/version/hash and executed binary hashes. Executable bytes are excluded from the uploaded artifact; independent root binary rehash is not claimed. Disposable runtime files/wallets remain excluded. CGO generated outputs and a complete independent Apple SDK header closure are not claimed.

No annotation creation/ensure, full Space authority, opaque identity/body receipt, import/mapping writer, body ACK, StageB or release qualification is supplied by this observer correction.
