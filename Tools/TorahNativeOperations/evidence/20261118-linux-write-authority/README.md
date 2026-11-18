# Linux native writer authority proof ? 2026-11-18

Run: https://github.com/davidpovarsky/anytype-swift/actions/runs/44218461051 (attempt 1).
Exact application source: `13efa130ca547f69b4550205295f795790ae6c88`.
Pinned Heart: `d98420b1113536afd08cde6de9a5816f6d27ffff`; Go 1.26.5 linux/amd64.
The run completed successfully at 01:48:23 UTC. The downloaded artifact is
`14389815915`, archive SHA-256 `bdf099b292b74cdcb8a0e23da69a67fbce791c5198a9515ade160a32515b203e`.

The actual JSON test events contain **20 top-level tests and 41 subtests passed,
0 failed**. The two process helper tests are skipped in the parent process and
executed as subprocess helpers by their owning tests.

Both current-writer regressions passed: a locally removed real writer cannot
append or retry an acknowledged operation; signed native preparation rejects a
writer removed after the host preflight. This proves current locally received
ACL authority, not knowledge of a revocation absent from an offline client and
not atomic locking of ACL authority through native storage persistence.

The archive hash matched GitHub artifact metadata. The log digest matched the
receipt. All nine compiled Go input hashes matched the exact Git blobs at the
source commit. `verified-manifest.json` records those checks and test identities.
The raw log and receipt remain byte-preserved by the local attributes file.

Scope: actual StoreState/any-store disk behavior, signed/encrypted native trees,
real two-process loopback TreeSync/DRPC, and local ACL read/write guards.
Application RPC, private registry adapter, mixed-version preservation, complete
hidden lifecycle, production coordinator/peer authentication, iOS and full T2
acceptance are **not accepted by this run**. The next registry source is separate
from this immutable proof. All full-T2 Asana tasks remain open.
