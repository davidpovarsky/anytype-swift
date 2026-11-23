# Loaded account and native ACL witness  opt-in candidate

Status: source only. No graph query, compilation, or new native method has run.

## Exact scope

This additive candidate uses feature tag `pinkha_loaded_account_witness`.
The four new application controls additionally require
`pinkha_loaded_account_witness_acceptance`. Original interfaces, default
implementation bodies, module files, prior Capture, and structural census remain
unchanged. The any-sync candidate adds one file to exact upstream
5d71ccad5db77997df2d2426011ebae4e7600d98 (v0.13.8). A separate, hash-bound
candidate.mod appends only its exact tracked local replacement; candidate.sum
starts byte-identical to the original Heart go.sum. Module caches are not forks.

## Production boundary and ordering

The actual application Service takes its existing lifecycle TryRLock, then its
session TryLock, in the documented order. It reads current fields directly and
does not re-enter GetApp or walletAccountId. The actual usable directory lease,
current wallet, derived signing identity, canonical existing account directory,
and requested account must agree. The real registered-session table and signing
key must validate a Full token. Every appHashByToken membership is refused,
including an empty association value. Token, mnemonic, and wallet keys are not
retained in the result.

The held App supplies the concrete private Space component. Its cache is read
only with Peek(id,false); missing, loading, or closing entries do not cause Get,
Pick, loading, startup, recovery, or network fallback. The dependency dispatcher
accepts only its concrete private native syncAcl, not an interface forwarder.
The real underlying list TryRLock uses the same lock as ACL writers. It copies
ACL ID, head, LastRecordId, identity and current permissions; mutable state and
keys do not escape. Guest/custom identity, unknown permission, busy,
unsupported, canceled and closed sources refuse.

The order is application lifecycle!’ session!’ native ACL read lock!’ native
per-Space gate!’ fresh same-DB ReadTx. Native read transaction/lease cleanup
finishes before ACL release. Current provider identity is checked before and
after capture. The detached state.a selects exactly one captured heads.h; that
head must equal both the held native ACL head and LastRecordId. Final cache
pointer, component context, account identity and ACL state remain bound. The
application then checks the same App/component/directory lease/wallet and real
token under its held locks.

A value-copied or zero ACL lease cannot inspect or release the genuine
acquisition. A genuine canceled or closed lease always releases its own RLock
once; a Close error prevents a successful capture. broadcastCtx cancellation
covers native Close before its private isClosed publication. Caller cancellation
bounds lock/gate admission and scanning, not the unchanged vendor transaction
cleanup or whole application shutdown.

## What this does and does not establish

The result is a detached locally authorized capture at the stated authorization
point, not a reusable authority token. Native lifetime ownership, actual account
and session binding, local current ACL permission, and stored head equality are
separate explicit claims. No remote freshness, semantic Object/block/Type
reconstruction, file-payload coverage, complete native source admission, global
semantic census, or destination-write permission is granted. The earlier
fixture-only census entry remains fixture-only. Same-process raw aliases,
unsafe reflection and arbitrary callers of lower exported storage primitives
remain outside the claim; this is not a new security perimeter.

## Four new controls, one application binary

1. A real private LocalOnly account, real mnemonic Full session, actual loaded
   native Space and read transaction produce a private witness. A separate held
   ACL read and independent private-frame audit bind the stored head. Success
   currently exercises the actual Owner role only.
2. Wrong account, unregistered or wrong-key token, actual Limited/JsonAPI
   sessions, both app-association map membership values, busy lifecycle/session
   locks, canceled requests, and a missing Space refuse. The actual storage
   inventory remains unchanged by the missing-Space request. Normal
   CloseSession revocation and a newly authenticated Full session are exercised.
   Direct association-map setup is explicitly a private fixture, not proof of
   the app-link mint flow.
3. A real ACL writer causes busy refusal. Zero/copied/canceled leases preserve
   the genuine lock and release. A real native lease holds the capture gate.
   A test-only context forwards the original Done/Err/Deadline/Value unchanged
   and observes only the fixed native lockSpace call stack using CallersFrames.
   It never probes the session mutex during production TryLock entry. Actual
   cancellation returns no witness; normal CloseSession completes, a new real
   session can capture, and actual closed ACL refuses. The callsite observation
   does not claim that the closer had already blocked.
4. A different native provider refuses the current capability without opening
   a database. A deliberate private stored-head mismatch refuses capture; exact
   restoration permits it. Actual AccountStop then removes App and native owner
   eligibility.

Fixture setup alone may create/load disposable data. It never logs mnemonic or
token. Raw native logs, wallet files and framed native rows remain in a private
owned root. Public evidence contains fixed classes, counts and hashes. Private
fixtures are retained; no RemoveData is used. Old Witness, hardening, census and
lifetime methods are never selected.

## Build and capacity contract

Use the existing exact Go 1.26.5 / ARM64 Alpine musl / Tantivy profile, one CPU,
offline readonly module resolution, explicit candidate modfile and both tags.
No dependency download, tool installation, cache deletion or old test replay.
A frozen source-only graph must precede build admission. Absolute build floor
is 2.95 GB, active stop below 2.60 GB, final reserve 2.50 GB. Current conservative
peak planning asks about 3.403.45 GB after source freeze; 2.95 GB alone is not an
estimate of this full application's growth. Preserve every original failure,
binary and per-method outcome; repair only demonstrated failures with separately
frozen source and never replay already qualified methods.

The graph keeps the qualified cache spelling `attempt4/cache` and records its
exact alias. The existing Tantivy archive and extracted static library have
separate identities; only the already verified library directory is mounted
read-only. No archive is extracted or copied. GOWORK is off: an old Page-only
genproto workspace pin is not silently added to this candidate. The actual
offline graph must resolve under the original sums plus the one approved fork.
A Go-generated test-main cache source is identified separately by its exact
package, fixed cache path, generated header, size bound and content-addressed
filename; it is source-enumeration metadata, not a compiled product.

## First source-only dependency query

The separate graph controller is an execution plan, not a completed gate. It
requires its exact committed controller identity, clean Heart 24dc and any-sync
c005 sources, the original module inverse and pinned tool/library bytes before
creating a new owned container. Its sole Go action is offline `go list -deps
-test -json` for `./core/application`; no `-compiled` or `-export` is supplied.
The existing image is pull-never, network-none and read-only, with one CPU. The
module cache, native/fork sources, candidate module files, Go root and Tantivy
library are read-only mounts. Only the qualified build-cache location and fresh
owned attempt are writable. The image's declared data volume is replaced by a
fresh empty read-only bind; no existing container is reused.

The source-only start floor is 2.65 GB, active stop 2.60 GB, final reserve
2.50 GB, and the Go query budget is 120 seconds. Raw output is bounded to 8 MiB
stdout plus 1 MiB stderr; all retained source-query metadata is at most 16 MiB.
Original stdout/stderr, typed first failure, exact Docker identity/configuration,
owned process groups and independent cleanup outcomes survive failure. A live
owned container is stopped before CLI group cleanup; the stopped container is
retained as operational evidence. Source and actual loaded Python bindings are
checked before and after. A successful source graph still authorizes no native
build or test. Source-only enumeration may write Go cache metadata/generated
test-main source; it is not labelled cache-write-free.
