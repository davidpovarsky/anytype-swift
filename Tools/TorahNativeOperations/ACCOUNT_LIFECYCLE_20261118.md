# Native private-history account lifecycle

This explicit Linux lane builds two actual `clientlibrary/service` test binaries
from Heart `d98420b1113536afd08cde6de9a5816f6d27ffff`. Both contain the approved,
immutable r14 patch `fb96818e…`; only the new binary receives the current exact
T2 registration patch and source overlay. The shared account fixture has its own
protocol, complete source hash and linked runtime identity. This does not reuse
T5's result, fixture identity, or account/export acceptance claim.

## Four real processes, one fresh synthetic account

| Process | Runtime | Actual operations and required evidence |
| --- | --- | --- |
| `new-create` | r14 + T2 | Native WalletCreate, AccountCreate, WorkspaceCreate, ObjectCreate and BlockCreate. Normal startup must not have created the private root. Explicit real Space/cache/factory derivation creates it, then one signed private claim is appended. |
| `new-reopen` | r14 + T2 | WalletRecover and AccountSelect reopen the exact account, Space, document, block and native root. Read the persisted claim before retrying; identical retry cannot append another change. |
| `legacy-edit` | r14 only | The unmodified old type registry must reject the private ChangeType. A normal ObjectSetDetails edit changes the existing Page title. Direct native storage enumeration must preserve both private raw changes and the exact head without decoding or rewriting them. |
| `new-recover` | r14 + T2 | Recover the exact original claim and the old client's ordinary title edit. Native BlockListDelete makes the target unavailable while retaining the signed journal. Native SpaceDelete then invokes existing native-storage/index/CRDT cleanup; both directories and the stale CRDT getter must show deletion. |

Every process performs real ObjectShow, ObjectSearch and JSON/Protobuf ObjectExport
requests. Positive ordinary fulltext and exact-ID controls must find the same
Page. Exact-ID and private-content searches must exclude the private host; normal
ObjectShow and both direct private-host exports must reject it. Eight ordinary
export files must preserve the same original block and contain no private
journal payload, operation ID, claim ID or root ID.

The fixture uses the existing internal `StoreObject` adapter after `GetObject`
returns, outside `Space.Do` and its tree lock. It does not introduce a public
operations RPC, startup creation, second renderer, or App feature enablement.
Genesis has upstream AddSeq zero, so raw-history verification hashes the root
directly and uses `GetAfterAddSeq(0)` only for appended native changes.

`AccountStop(RemoveData:false)` must succeed and clear the running application
before AppShutdown and process exit. AppShutdown alone is insufficient because
the upstream Middleware intentionally logs Stop errors while returning success.
Later phases may invoke AccountMigrate only after the explicit native
ACCOUNT_STORE_NOT_MIGRATED response; they cannot create another account or target.

## Source composition and execution boundaries

The controller requires fresh exact checkouts, verifies r14's patch/inventory and
builder hashes from approved source `947fbde24d5657d0e1229f45bb3993648884a8a1`, and
checks the entire T2 tracked-plus-overlay path set for collisions. All before and
after hashes, unexpected changes, module files, fixture files and native binary
hashes are checked. The T2 initializer is `pinkha_torah_operations.go`; its older
filename collided with r14 and must not be restored.

The compile closure matches the proven registry lane: Go 1.26.5 in the pinned
Alpine image, the exact linux-amd64-musl Tantivy archive, a static qsort_r probe,
and the already reviewed genproto workspace replacement with both module sums.
No native Go module files or source pins are changed. Compilation uses one job.
The reusable workflow is separate from the component/registry proof to avoid
silently adding two middleware builds to every native operations run.

The controller creates a fresh owned work directory and empty `account-root`.
The synthetic key and mnemonic remain in private 0600 work files. Only an
explicit evidence allowlist is copied, after scanning every candidate for those
secrets. Neither account stores nor binaries enter the upload path. A failed
early wallet phase without a valid secret inventory withholds native stdout.
Timeouts and cancellation signal only each controller-created POSIX group,
including a descendant that ignores TERM after its parent exits.

## Acceptance status

The controller's local negative controls are distinct from native acceptance.
They reject stale/wrong source identities, extra account creation, changed raw
history, incomplete exports/cleanup, false App enablement and unsafe evidence;
two POSIX controls execute actual child processes to test flush and owned-group
termination. They do not execute Heart.

The new account fixture is **NOT_RUN** until the exact source is compiled and all
four actual native invocations pass. A successful run establishes one-account
lifecycle and old-client preservation only. Two App clients, the application RPC
contract, global offline revocation, atomic cross-tree target deletion and iOS
acceptance remain separate. App capability stays **OFF**.
