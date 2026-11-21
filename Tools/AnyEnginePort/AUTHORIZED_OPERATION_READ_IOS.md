# Authorized operation read: isolated iOS qualification

This profile qualifies one additive read contract across the actual Any C library, its managed loopback gateway, a disposable native account and Space, the real application owner, and the common `TorahAuthorizedOperationReading` interface.

## Selection and evidence boundary

The reviewed profile is `candidate-runtime-read`. It uses only:

- Source manifest: `Tools/AnyEngineValidation/evidence/native-authorized-operation-read-v10-candidate-source.json`.
- Scheme: `PinkhaAnyRuntime`.
- Named method: `PinkhaAnyRuntimeTests/AnyAuthorizedOperationReadRuntimeTests/testManagedNativeAuthorizedReadPreservesBytesAcrossBlockDeletionAndColdReopen`.
- Environment: `PINKHA_ANY_NATIVE_ARTIFACT=verified-v1` and `PINKHA_ANY_AUTHORIZED_READ_ACCEPTANCE=candidate-v10`.

The second selector adds only the acceptance target's Host/Integration/Kit dependencies and test definition. The ordinary runtime target and the retained three runtime methods keep their existing dependency and selection behavior. This profile must not execute those three methods, Hanlin, application, UIKit, or UI suites.

Both arm64 device and simulator library slices must be built and installed through the existing strict source/archive controller. The default manifest remains v9. The frozen v10 component/HTTP evidence keeps its original tree identity. The separate candidate differs only by four advertised read capabilities and a qualification comment; its manifest says that real iOS qualification has not yet executed. The legacy manifest field `testedEffectiveTree` supplies the existing artifact controller's exact build identity, not a new test-pass claim.

## What the one journey must prove

The fixture creates its own account, Space, document, block and opaque canonical operation. A pre-install read returns typed history-unavailable and leaves the protected bundle absent. After explicit installation, an absent operation is reported only within a verified local snapshot.

The fixture appends through the real native repository, reads the exact canonical bytes and native creator/change/ACL provenance through the real Host owner, deletes the block and retains the same operation as `unreachableBlock`. It drains that owner, stops the actual C runtime, reopens the same store, restores the same disposable account, and reads the unchanged operation under a fresh owner generation. The old owner must fail. Deleting the entire document then returns typed target-state-unavailable without a partial result.

The fixture never emits recovery phrases, managed tokens, auth-response bytes or raw store contents. Cleanup is restricted to its own disposable Space and UUID-named directory.

`AnyHostAuthorizedTorahOperationReader` delegates decoding/mapping to the existing common adapter. Its private stream lifetime uses the actual owner's generation, and every read runs inside `AnyApplicationSession.perform`, which verifies the account/native boot before and after acquisition and refuses delivery after revocation. UI callers must still compare the returned scope against their current owner on the publishing actor immediately before installing presentation state.

## Receipt gate

After `xcresulttool` exports the summary and named test tree, invoke:

```sh
python3 Tools/AnyEnginePort/verify_authorized_operation_read_execution.py \
  --summary candidate-runtime-summary.json \
  --tests candidate-runtime-tests.json \
  --udid "$PINKHA_SIMULATOR_UDID" \
  --output candidate-runtime-read-receipt.json
```

The gate requires exactly one named passed method, zero failed/skipped methods, and this run's actual iOS 27+ arm64 simulator. Extra previously accepted methods cause rejection. It verifies the exact candidate source manifest, both installed binary-slice inventories, the current build/consumer binding and unchanged tracked test/adapter sources. An earlier v9/v10 artifact cannot satisfy candidate qualification. If a Swift-only correction is needed, this same candidate binary can be reused only through the existing explicit producer binding, ancestry check and complete native source-identity gate; test results are always from the current selected method.

Controller checks live in `test_authorized_operation_read_execution.py`; they exercise zero/skipped/wrong-destination receipts, a substituted method, accidental extra execution, and changed/missing/extra installed native members.

This is not a two-client convergence, source-page/watermark, backup/import, causal-ordering or full T2 acceptance claim. Those rows remain open until separately proved. Default capability activation stays off.
