# Heart authorized-read iOS candidate

This host builds the four retained local Swift modules plus a minimal SwiftPM
test target once. It consumes only `Pinkha-Heart-Authorized-Read-Simulator-v1`
from the separately successful controlled producer run. The producer's complete
framework inventory, generated native bindings and native source closure must
match candidate `69b6b3fc8616b11230cbc45ced0635f60098950a1e611a089ab73baf70550b67`.
It never replaces the App's default or corrected-r15 runtime.

The dispatcher route is `t2-authorized-read-ios`; `source_run_id` is the exact
successful `t2-authorized-read-apple-runtime` producer. The controller creates
one disposable owned iPad simulator and removes only that simulator afterward.

## Fixed selection

| Suite | New methods | Purpose |
|---|---:|---|
| HeartAuthorizedOperationCodecTests | 9 | Exact canonical bytes, identity, full closure, provenance and transport limits |
| HeartAuthorizedOperationSessionTests | 5 | Owned lifetime, cancellation and final publication |
| HeartAuthorizedOperationNativeFixtureTests | 1 | Original generated Go response bytes from native run 44954793488 |
| PinkhaNativeReadLifetimeTests | 9 | Actual frontdoor transition inventory, overlapping completion order and typed response limit |
| HeartAuthorizedOperationLibTests | 1 | Actual generated Lib append/read through the native account/Space owner |

All 25 named methods must actually pass, with no missing, extra, failed or
skipped case, on the one owned iOS 27 ARM64 destination. The actual native
journey attachment is additionally bound to the current run, app source, nonce,
full runtime version and process ID. A printed success receipt alone cannot
qualify a run whose XCTest assertions failed.

The real Lib journey creates one fresh synthetic account and Space, waits only
for read-only native type readiness, creates one document/block, and proves
read-before-history does not create a private root. One actual generated append
is followed by exact UTF-8/non-UTF-8 canonical bytes, signed native provenance,
verified local absence, live-to-unreachable block history, synchronous retirement
before AccountStop returns, denial of stale publication, same-iOS-process native
account reopen without replay, and SpaceDelete retirement. Account keys and
mnemonics stay in memory; the invocation body logger is disabled. Exported
identity/content fields are hashes.

The native account reopen occurs in the same iOS process. A fresh iOS-process
reopen and two simultaneous App clients are explicitly **NOT_RUN**. Existing
native 23-method/71-case and two-process account results remain source-qualified
evidence; they are not executed again. The independently qualified shared/Any
package 14 methods are not selected. Full T2 and App capability remain OFF.

## Fixture boundary

`pinkha_append_fixture.proto` is a test-only namespace projection of the frozen
existing native Append message. It preserves the original wire fields; it does
not add or change a production write API. Its Swift file is produced by the
already pinned SwiftProtobuf generator and official protoc; its exact SHA-256 is
required before the host builds. The fixture byte wrapper is compiled only when
both the read candidate and dedicated fixture flags are set. Ordinary candidate
and default App builds do not compile it.

The native golden bytes in `PinkhaHeartEngine` are the original export from run
44954793488. That native run cold-reopened the live block before deletion; its
fixture does not claim a third process reopened the newly unreachable state.

All package dependencies resolve to four exact reviewed revisions before test
execution, and the original resolution and source hashes are checked again
afterward. Original xcresult, command logs, native receipt, destination and
controller receipts are retained even on failure.
