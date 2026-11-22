# First original native registration result: 12 PASS, 1 FAIL

**Overall native result: FAIL.** Compilation succeeded and all 13 selected children ran exactly once. Twelve passed; `MissingAttachmentUsesOneNativeApply` failed before its repair Apply. No previous passing test parent was replayed.

| Identity | Actual value |
| --- | --- |
| Source | `60b8300c3506e53638c8ca883f82484de073fae8` |
| Source parent | `3be6ecab805b17e2c90fee897fdab45a0b03bfdc` |
| Original Heart base | `d98420b1113536afd08cde6de9a5816f6d27ffff` |
| Run | [45038140322, attempt 1](https://github.com/davidpovarsky/anytype-swift/actions/runs/45038140322) |
| Job | `137256341224`, `new-native-controls` |
| Event | One activation-branch push |
| Artifact | `14760254250`, `Otzaria-Annotation-Schema-Registration-45038140322-1` |
| ZIP | 3,860,363 bytes; SHA256 `50ac79ce2728afa86feeff3c86ead0bdf21f9fec7ace16a743f6a451370c74ee` |
| Exact manifest | SHA256 `f3d2fd65b109fc67602318ff8e0e51c79b4295eae535a2d7ed3153e19ef0c36f` |

The run was created at 15:24:29 UTC and completed with failure at 15:31:14 UTC on 22 November 2026. Original Go 1.26.5/macOS ARM64 compilation took 256.607 seconds; the native test command took 25.58 seconds. The formatter accepted frozen source bytes. The 19 composed product/test inputs appeared in the actual Go closure; the 13 previously composed inputs remained byte-for-byte unchanged. Post-execution source/native dependency checks and owned disposable cleanup succeeded. The binary hash and PID are runner observations; the executable is not in this archive and was not independently rehashed by the verifier.

## Actual case results

| New child | Result |
| --- | --- |
| ActualRegistrationAndStrictReadback | PASS |
| RepeatedRegistrationDoesNotMutate | PASS |
| MissingAttachmentUsesOneNativeApply | **FAIL** |
| VisibleColumnRemainsConflict | PASS |
| RootOnlyStopsAllCreation | PASS |
| DifferentActiveAccountIsRefused | PASS |
| CancelledBeforeAdmissionWritesNothing | PASS |
| NativeRootCollisionDoesNotInitialize | PASS |
| NativePopulatedCollisionDoesNotOverwrite | PASS |
| NativeReaderRoleCannotRegister | PASS |
| QueuedAccountStopDrainsWithCancellation | PASS |
| QueuedAccountSelectDrainsNativeApply | PASS |
| StopCancelsQueuedSelectWithoutDraining | PASS |

The positive registration fixture recorded 18 distinct original native creates and one successful type Apply across four explicit phases. Read-only readiness separated those phases; no fixed object was created twice. The retained native report contains the exact 18 original identities, positive raw index matches, full copied details/block protobufs, actual account/Space/ACL scope, hidden attachments and views. This is historical evidence from the disposable original runtime, not a capability for a future annotation operation.

The three lifecycle controls passed with real original queued writer contention and native create/Apply. They cover ordinary Stop drain and cancellation, queued Select, and Stop's early acknowledgment of a queued Select cancellation followed by deferred close after admission releases. The collision controls used actual native root insertions and preserved both root-only and populated winners. The signed native Reader-role control rejected registration.

## The remaining failure

The failing fixture first registered its schema, then used the original property API to add an unrelated visible property, used native Apply to add a description and a cloned second view/custom width, and used the original property API to remove one annotation metadata attachment.

Its next registration call recorded zero creates and no repair Apply. It returned:

`native annotation schema registration conflicts with persisted state: loaded type differs from complete persisted native state`

The failure occurred at test line 104 during the full loaded-versus-strict-persisted precondition. The later assertion that unrelated properties/views remain unchanged was not reached. The guard preserved the state by refusing the write. The original artifact does not contain the complete paired live/persisted snapshots at that exact comparison, so the precise differing field or block is **not yet established**. No mismatch was normalized away, no success is inferred, and no rerun is included in this evidence.

The next bounded diagnostic is to capture actual loaded and strict persisted copies after the failing fixture's original setup writes, retaining complete protobuf bytes and native heads. Product predicates and the twelve passing child bodies must remain unchanged. Only the unresolved child should be selected for a later reviewed run.

## Evidence verification and observer

`Heart_Annotation_Registration_45038140322.zip` retains the original 44 payloads plus `EVIDENCE_INDEX.json`, including all command streams and the complete native event stream. The ZIP CRC, exact payload membership, every payload hash, declared input coverage, exact native test starts/terminals, source head and manifest were independently checked. `VERIFIED_FIRST_RESULT.json` contains the result and exact failure events. `FAILED_CASE_SELECTED_EVENTS.json` is a small extracted view; the ZIP remains the complete original evidence.

To reproduce the bounded read-only verification from this directory:

```sh
python3 verify_first_registration_artifact.py Heart_Annotation_Registration_45038140322.zip EXECUTION_INPUTS.json
```

The sole finite Sentinel observer, `job_f5b0e1e2d441`, finished successfully at 15:35:23 UTC with exit code 0 and `TERMINAL_ARTIFACT_RETAINED`. It preserved three transient API read timeouts before reading the terminal failure and verifying the artifact. Observer success means that the failed native run was collected correctly; it does not change the native result.

No generated Swift/RPC bridge, iOS SDK acceptance, ordinary annotation create/recovery, native body/map authority, COMMIT or ACK is established by this run. Earlier strict/native/readback results remain bound to their own immutable source and are preserved without replay.
