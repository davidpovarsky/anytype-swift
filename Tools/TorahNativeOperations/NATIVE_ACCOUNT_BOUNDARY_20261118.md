# Account-scoped native operation boundary

## Implemented source

The isolated App overlay now contains `Middleware.NativeTorahOperationAppend` and `Middleware.NativeTorahTargetRead`. They are typed native Go handlers, not registered ClientCommands or an enabled App feature. The eventual generated endpoint names are reserved for review as `PinkhaTorahOperationsAppend` and `PinkhaTorahOperationsReadTarget`; no protobuf, generated transport or Swift binding is changed in this commit.

The handler accepts explicit version 1. Unknown versions fail before any account access. Invalid Space/target identifiers, read limits and canceled contexts fail before private history access. Requests cannot provide an author, private root ID, signing key or permission verdict. The running account supplies the signing identity; the receiving Space determines the canonical private root.

The actual native Space ACL is checked for currently known membership before private access or lazy creation. Read-only members retain read access; unknown and locally revoked identities are denied. NativeHost repeats its own current authority checks at the underlying operation. These checks do not claim awareness of revocation updates an offline client has not received.

The existing Page/Template, deleted/uninstalled, live-block and self-target validation is shared by a small refactor of the existing host validator. The account handler uses that same check before any root creation. It passes the required empty InitContext callback when explicitly deriving a root and handles only the exact concurrent ErrTreeExists case by opening the existing canonical history. Ordinary startup does not create a private root.

## Read, retry and account lifecycle contract

A read never creates a root or appends signed history. Locally absent history returns ErrPinkhaTorahHistoryUnavailable rather than an empty synchronized snapshot. Opening existing history may rebuild its derived local projection from verified signed changes. The read limit is explicit; excess is an error, never truncation. Verified native heads are retained, and AppliedSeq remains a local storage watermark rather than a cross-client version or remote-sync barrier.

Append preserves Created, AlreadyExistsSamePayload and CollisionDifferentPayload. An operation-ID collision does not overwrite an existing claim or become a successful retry. If a signed write is already durable but projection commit/recovery fails, the returned receipt and ErrProjectionBehind are preserved together. A transport wrapper must surface the error and must not relabel the result as synchronized acceptance.

Account identity is checked before/after the operation through the actual application getter. It is not called from a NativeHost target callback or while this code holds a tree/ACL lock. The getter takes the application read lock; AccountStop holds its write lock while closing native components. This avoids adding an inverse tree-to-application lock order. An operation already in flight is not rolled back: a durable append can return its receipt plus an account-change/cancellation error. A read snapshot is discarded if the account changed. Target deletion and an operation append remain separate native-tree transactions; orphaned claims are retained.

## Focused evidence and limits

The SDK sibling independently reviewed the handler, authorization helper and shared target validator against Heart d984 and its actual application lifecycle. No blocking source finding was reported. The root reviewed the exact minimal runner/inventory diff before assignment. All five changed overlay hashes match the source-bound inventory; the existing tracked native patch remains byte-identical. The resulting 42 T2 paths have no overlap with either approved r14 (35 paths) or r15 (42 paths).

Four new native controls are selected explicitly: version rejection before account access; running-account requirement; read-shape/cancellation rejection before account access; and a real signed-ACL test covering owner, foreign identity, reader and known removal. The core package has no older TestPinkha/TestPrivate cases at the pinned base, so the focused registry selector adds only the new boundary cases. The controller passed 5/5 Python controls on Linux Scratch and on the connected Windows host. gofmt and diff checks passed. **New Go compilation and native execution are NOT_RUN.**

The existing real-account fixture is unchanged by this handler commit. Its separately published storage assertion correction is 964fb0f6d0ea19b54e259c6bd383954b2bf3902b. A richer account-boundary fixture was prepared and source reviewed locally, but is not part of this minimal integration or an acceptance claim. Real account calls to these handlers, generated protobuf round trips, old-client preservation through that binding and two actual App clients remain required. App capability remains **OFF**.

## Source and execution scope

Only the isolated App worktree was changed. The four new Go files were authored in this session; existing files were edited through exact-context patches. Source inventory/test selection were applied only after the exact path/hash changes received a separate review and assignment. The rejected bulk full-file transfer was not retried, and no Heart worktree, original WIP, user account or data was modified. `evidence/20261118-native-handler-source/validation.json` records the concrete pre-native checks. Native runs must bind their own exact published SHA and retain their raw artifacts separately.
