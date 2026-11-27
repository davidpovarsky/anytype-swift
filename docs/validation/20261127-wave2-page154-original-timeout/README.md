# Page154 — original linked-native enumeration timeout

The previously missing original timeout records were read directly from their
retained Mac directory on 27 November 2026. The seven files in this evidence
directory are exact copies of the original command, stage and binding records;
their 6,914 bytes were verified against the SHA-256 values observed on the Mac.
No compiler, native call, simulator operation, test or process probe was run.

## What the original records establish

The original App source is `379ca3568f247d2fc218ed63df24796d461713c0`, with native
manifest `8ac407e75a4bfb42c359a2f72b3822c44990caedf2351d00d78315de5c96a04b`.
The continuation controller is `ee39f1b1fa21576cabc87a60f4cae1d8c1f27f1e359d57afa8c5607b1bfb7a4f`.
The original files remain at:

`/Users/m1/development/anytype-e-active-20261125/main15/linked-three-continuation1`

| Original record | SHA-256 | Actual scope |
| --- | --- | --- |
| `evidence/execution.json` | `6cd7287d7c2c49e7880bc03cc81a1c26a2b81af9c09ff0320331127dcc96773e` | Overall continuation failed; zero methods invoked |
| `evidence/linked-native/result.json` | `bcfa06bea94cc0ce89541dc3e165160d6574ce1c9f551c56857102a24d00a5e0` | Linked-native stage failed during enumeration; `testInvoked: false` |
| `commands/linked-native-enumerate/result.json` | `5cc4b2168ac3211ff4fe913d1b8a957cf581e45315a91fbbd5e41671a827311b` | Original 180-second timeout, exit -15, owned group absent |
| `commands/linked-native-enumerate/original.log` | `7e1a4431fb2342fc9bb69d40abaf5f07f3b34dc173af6cd19f4c87fb04afffcf` | Original 757-byte stdout/stderr log |
| `evidence/retention-completion.json` | `3ba4ebd609c09946278413d6b7204e58d9ace3ed977ed6ea69bf9055436a6681` | Original private-account retention, without full E acceptance |

The command selected exactly
`AnytypeTests/SemanticAnchorPage154MountedPreparationTests/testReadBackExistingSemanticSourceAfterActualUIEditAndColdReopen`
with `test-without-building`, `-enumerate-tests`, flat JSON enumeration, and the
original owned simulator destination. It began at **26 November 09:07:32.401094
UTC** and exited at **09:10:32.601224 UTC**. The controller recorded
`OWNED_TIMEOUT`, sent SIGTERM to its then-owned live group, reaped the child, and
recorded `ABSENT_ESRCH`. These are historical records: no old PID or process
group was probed again.

The log contains only the invocation followed by `BUILD INTERRUPTED`. It does
not identify why enumeration failed to complete. Neither the original
enumeration output nor an XCTest result bundle exists in the linked-native
stage directory. The original stage result records `testInvoked: false`, and
the overall continuation records zero invoked methods. This is not a failed
assertion inside the native test and provides no new runtime acceptance.

The original descriptor binding retained thirteen environment-key names,
`exactInverse: true`, and `testingEnvironmentUnchanged: true`. Its values and
the private account were not copied into this public evidence directory. The
stage's original product-integrity record reports 6,308 verified entries and
one extra bound descriptor. The underlying products were not requalified or
rebuilt by this read-only audit.

## Relationship to earlier evidence

The three original preparation, mounted and linked-UI successes remain tied
to their original App15 run. They were reused by the continuation and were not
reexecuted. The earlier overall PNG-collector failure
`f69519144707d12d6577d7300ae05caeaca514204c295a3652a16b17bdb993f7`
also remains failed.

This audit clarifies one earlier metadata label: **`bcfa06be…` identifies the
linked-native stage result, not the overall execution JSON.** The earlier
continuation audit is preserved unchanged; its `executionSHA256` field under
`priorFailures.linkedNativeEnumeration` must be read with this correction. The
overall continuation execution hash is `6cd7287d…`, as shown above.

The original fixture's expiry is **26 November 10:32:50.211263 UTC**. The
enumeration timeout occurred before that expiry. Expiry therefore does not
explain the original timeout, but it prevents a valid continuation from the
same fixture today. No deadline, retry, fixture timestamp, admission guard or
test assertion was changed.

## Remaining acceptance

A real, qualified future shared App/UI product and a newly created fixture are
still required. Preserve the original six-stage order: preparation, mounted,
linked-UI, linked-native, unlinked-UI, unlinked-native. The fresh preparation and
first two UI stages establish the required state for the three missing stages;
they do not overwrite the historical three successes. The existing typed PNG
collector and the separately published closed intake preparation remain the
applicable sources. Native unlink/readback, full visual coverage and physical
device acceptance remain open.

`original-copy-manifest.json` binds the seven exact safe original files.
`mac-readonly-observation.json` records the actual bounded read and its limits.
The full private account and complete original execution/retention records
remain at the original Mac location.
