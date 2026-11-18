# Native T2 component evidence ? 2026-11-18

## Passing result

Exact source: fad8266c778a1832921a4145ae350ec7c2f6ef88.
Pinned Heart: d98420b1113536afd08cde6de9a5816f6d27ffff.
Go: 1.26.5 windows/amd64, actual StoreState + any-store 1.0.3.

The source-bound runner returned exit 0 and PASS_COMPONENT_ONLY in 13.358 seconds
(including cached compilation). The raw Go event log contains **16 passing
top-level tests and 26 passing subtests**, zero failing tests, and one intentionally
skipped subprocess-only helper. The committed-process-exit parent test invokes
that helper separately, verifies its deliberate exit code after commit, reopens
the real SQLite file and verifies idempotent retry/no overwrite.

The passing source files and raw log were rehashed before copying. The manifest
records every evidence file hash; the receipt includes every Go source hash, an
aggregate overlay hash and upstream go.mod/go.sum hashes. Raw JSON/JSONL bytes
are retained without Git line-ending conversion. No CI run ID is invented:
this was a local Windows native component run.

## Initial failed attempt and correction

Initial source: 8b99aab1b827b47bf1c9448184dab0da14d8e0be.
The package compiled and began executing the actual native tests. The immutable
modify test passed an unquoted string to Builder.Modify, whose string argument
is raw JSON; parsing rejected it before the handler, so the intended validation
assertion failed. Missing failure-path rollback in that test then held the write
transaction during cleanup. The overall 480-second limit ended the attempt with
exit 124. This attempt is NOT acceptance. Its partial raw log/receipt are retained.

The follow-up commit quotes the JSON correctly and registers rollback cleanup
before assertions. It also adds a real local-append validation: every observed
predecessor must exist at the same target in the same write transaction, with
a dedicated native test. The focused rerun uses the complete published runner,
which terminates only its spawned process tree on timeout before recording logs.

## Acceptance boundary

This demonstrates an executable native immutable operation primitive on disk:
replay-order-independent claim sets, explicit collision, atomic local retry and
rejection, observed-remove/add-wins, concurrent successors, retained tombstones,
native provenance records, generic StoreState mutation rejection, transactional
rollback, space namespaces, actual index usage and bounded/canceled reads.

Two independent disk projections receive explicit test replay. They are not two
syncing Heart clients. The process-exit test is not a power-loss durability claim.
There is no hidden native object registration, signed history append, ACL/target
authorization, production RPC/capability or app integration. Middleware, actual
two-client transport, hidden lifecycle and iOS acceptance remain NOT_RUN.
The T2 Asana tasks must remain open.

The original Windows receipt JSON files retain CRLF bytes. Git diff --check
therefore flags their carriage returns as trailing whitespace. Source, tests,
runner, README and manifest checks are clean; raw evidence is not rewritten
to remove that diagnostic. No Git validation setting is changed.
