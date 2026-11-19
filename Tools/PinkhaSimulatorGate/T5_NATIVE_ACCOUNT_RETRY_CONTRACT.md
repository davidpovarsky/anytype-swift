# T5 R07 existing-account error and retry

This lane adds one separately selected native Swift test around the accepted
pagination body. It verifies a real stopped-account RPC error at the production
service boundary, followed by a successful query after restoring that same
existing account. It does not establish a network outage or UI error rendering.

## Exact selection and unchanged baseline

The dispatcher route is `t5-native-account-retry`. It calls the existing native
pagination workflow with `include_account_retry: true`, which passes
`--include-account-retry` to its controller. The default
`t5-native-pagination` route keeps its original method and environment.

The only selected XCTest method is
`TorahT5NativeAccountRetryTests/nativeStoppedAccountErrorAndSameServiceRetry`.
The wrapper directly invokes
`TorahT5NativePaginationTests.nativePaginationCurrentSpaceAndMutationAcceptance`
once, then executes its separate tail. There is one selected XCTest method;
the baseline body invocation is not counted as another independently executed
test. The full original 28,741-byte Swift file remains an exact prefix with
SHA256 `dff9dd58471659cc19d082ea0961f2ccff9666ad86c4aa052c85a3aa4e5d4990`.

Separate suites are necessary because the maintained AnytypeTests configuration
builder reduces selections to their class names. Adding a second test to the
original suite would also run the original fresh-account method separately.
The result validator requires exactly the wrapper method, one pass, zero
failures and zero skips on the actual owned arm64 iPad simulator running OS27.

## Real native sequence

1. Execute the unchanged accepted pagination body, including its ten original
   observations, 36 real search calls, five native data mutations and final
   native account stop/application shutdown. Retain its original receipt bytes
   and private credential file.
2. Check that both original native root and account directories already exist.
   Restore the existing native wallet from its original private account key,
   select the same account and activate its original Space. Missing directories
   or migration-required accounts fail; there is no recreation or migration
   fallback.
3. Construct one production `AnytypeTorahSpaceRelatedDocumentsService` using
   the real association repository and a recorder forwarding to the original
   `SearchMiddleService`. Query with native page size 2 and independent native
   membership/readback observations. The final baseline has seven native
   candidates and eight reachable targets after its deliberate block deletion.
4. Invoke real `AccountStop(removeData: false)` and independently confirm
   `accountIsNotRunning` using `AccountPreloadRemainingSpaces`. Query through
   the same production service. Its first actual native ObjectSearch must throw
   `BAD_INPUT` (numeric code 2), description `account must be started`.
   Returning an empty or cached successful snapshot cannot pass.
5. Recheck the existing directories before wallet recovery and before/after
   account selection, restore that same account and Space, and query through
   the same service/recorder/upstream search instances. Four real native pages
   and current independent native readbacks must produce the expected eight
   targets. Canonical bytes, titles, types and the final baseline block graph
   remain unchanged, including the deliberately deleted block.
6. Stop the native account again without deleting data, confirm it is stopped,
   shut down the native application, and verify original baseline/credential
   bytes and both directory identities once more.

The tail contributes three query observations, eight successful search calls
and one failed search attempt. The wrapper therefore accounts for 45 actual
search calls when both the unchanged baseline and the tail qualify. Those are
expected counts, not evidence of execution until a real original run passes.

## Source, account and result qualification

`t5_native_account_retry_evidence.py` first runs the unchanged pagination
validator over the original baseline receipt. It then verifies the tail's
source/run/attempt/token, native PID, runtime version, original account/Space,
baseline SHA256 and private credential SHA256. Every query retains the same
three distinct production-service, recorder and original-search identities.

All nine Swift root/account directory observations must have identical path
hashes, devices, inodes and creation timestamps. The controller independently
reads those directories after execution. Path/device/inode equality is exact;
its comparison of Python and Foundation creation timestamps permits at most
one microsecond of binary floating-point conversion difference. This does not
permit any change between the nine native Swift observations.

The verifier checks operation ordering, containment within the actual XCTest
start/finish interval, and the existing 900-second test allowance. The separate
Xcode supervisor remains bounded at 1,200 seconds. It independently verifies
the failed request's original source/Space filters, sort, requested keys and
absence of returned objects. Successful queries require the complete actual
page inventory and derive every result's identity, metadata, order and unlink
authority from current native readbacks. `indexedTargetsOnly`,
`indexFreshnessUnverified` and `staleCandidates` remain explicit.

## Evidence and privacy

The tail writes `account-retry-receipt.json` next to the private unchanged
baseline. The controller copies it and adds
`account-retry-controller.json` containing only directory identities, file
digests, run attempt and the actual selected test window. These two files use
the existing allowlist and complete original mnemonic/account-key scan in
UTF-8, UTF-16LE and UTF-16BE before any native proof is published.

The raw native xcresult, account data and credential files remain private.
The artifact name is distinct:
`Pinkha-T5-Native-Account-Retry-Evidence-<run>-<attempt>`.

## Acceptance boundary

This lane consumes the original verified r15 runtime inventory through the
maintained installer. It does not replace either immutable r14/r15 approval,
and it does not qualify the separately corrected attachment runtime or the
old/new runtime compatibility journey. Product lookup remains `OFF`.
Whole-index completeness, a forced network outage, UI error presentation and
physical-device acceptance are not established by this lane.

The Python controls use synthetic receipts and filesystem fixtures to reject
incorrect evidence; Swift grammar parsing does not typecheck UIKit or execute
the native app. Actual Apple build and execution are required before claiming
this R07 service-boundary subcase has passed.
