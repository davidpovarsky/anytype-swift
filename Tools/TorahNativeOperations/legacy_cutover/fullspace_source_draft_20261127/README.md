# Heart full-Space index readiness — source-only checkpoint

**Status: reviewed source draft, not compiled or executed.** This directory is
an isolated proposed overlay. It is excluded from the qualified cutover core40,
RPC11, crash, signed-host and generated-byte acceptance closure at engine commit
`834a6bced7b922a18f291add1bcc6e82d5bba61f`. No generated Apple product or native
FullSpace acceptance is claimed. Keep the retained 4,893-file source and its
custody manifests immutable.

`source-draft3.json` pins all 37 proposed files. `source-draft3.patch.gz` contains the
complete proposed changes against the exact base files after gzip decompression.
Both embedded patch artifacts retain their exact reviewed uncompressed bytes;
patch-artifact-encoding.json records their hashes and the original publication
check diagnostic. No Go source changed for this storage encoding. Every non-null original
hash was compared with the union of the original 4,868-file source manifest,
the qualified native core40 manifest and the qualified RPC11 manifest. The base
comparison is a source identity check, not a compilation or behavior result.
The original Oracle `gofmt` parsed and formatted the four latest files; the other
33 remain byte-identical to the previous formatted draft. Go type checking and
all tests remain outstanding.

## Proposed native contract

`pinkha-heart-torah-space-index-v1` describes a **current local snapshot** for one
exact account run, loaded Space, canonical relation key and schema version. It
does not claim peer convergence or complete delivery of a bounded search query.

The reader takes an authoritative HeadStorage snapshot H1, reads the original
index's heads and derived projection proofs in one read transaction, then
compares a second authoritative snapshot H2 and the current ACL/run ownership.
Every ordinary object must have a matching current indexed head before it can
be included or excluded. A stale mutable type field cannot hide an unindexed
object. Only roots with an original native protocol classification can be
excluded without ordinary document projection.

The generation binds the Space, schema, current account run/index ownership,
ACL token and deterministic authoritative/index/projection witnesses. A new
process gets a new scope; it cannot inherit an old readiness result. The API
does not load a Space, initiate reindexing, write metadata or start recovery.
The read remains bounded at 10,000 objects and 16 MiB. Overflow, partial data,
unsupported projections, missing heads, iterator failures, cancellation and
owner retirement cannot produce a successful prefix result.

The final delivery fence uses a tiny nonblocking owner check inside the ACL
boundary. It performs no database access, tree wait, generation computation or
row copying while the final owner locks are held. Original close/load lock
ordering was reviewed; targeted lifecycle behavior has not yet been executed.

## Proposed original-indexer extensions

Known non-document metadata roots receive an admission witness only after the
original native root header is validated. The exact indexed heads and witness
are persisted in the same original index transaction. Canonical unsigned
derived roots are validated with the native derived-root rules; they are not
mislabelled as signed roots.

Deletion stores a versioned witness bound to the exact Space/root and terminal
HeadStorage tuple, including heads, common snapshot, derived/parent identity,
sequence and terminal status. An old generic tombstone or an absent projection
cannot stand in for the current deletion. Rollback, stale tombstone, queued
deletion, resurrection/new heads and changed sequence must remain incomplete.
The current draft also advances the original one-time deleted-object reindex
counter. That startup path still uses the original global deleted-object
enumeration; the readiness reader's bound does not imply a new bound on that
startup operation. Its retention and no-fabrication behavior needs real tests.

Each accepted index task receives a buffered one-shot completion. Transaction
acquisition, transaction binding, commit and fulltext queue insertion failures
must settle every affected task exactly once. A canceled caller cannot block
the transaction worker. The latest source correction returns the original
fulltext enqueue error before either transaction commits; it no longer logs
that error and then overwrites it with a later successful commit result.

Metadata callbacks capture the exact account run, Space and index instance.
Queued work cannot resolve a replacement global account or index after an
account switch. Queue admission is not index-commit completion. If a native
signed change committed before its projection callback failed, the original
effect and receipt remain available together with the failure. A caller must
not infer zero effects or automatically append again.

## Proposed evidence, all still unrun

The focused unit and native fixtures cover original index transaction failures,
per-task error isolation, cancellation, final owner retirement and close during
loading; metadata/deletion witness transactions and bounds; original signed and
derived root validation; and native signed effects followed by index failure.
The six transaction fault cases retain the original five controls and add a
real fulltext-queue insertion failure with two accepted tasks, rollback and
completion checks.

The native FullSpace fixture is intended to use a fresh account and a second
cold process to prove ready existing data, a newly signed unindexed object,
actual indexing completion, relevant content/type/archive/delete transitions,
unsupported projection refusal, generation changes and scope retirement. Its
compiler, controller and runtime outcomes remain to be qualified; source review
alone does not establish those behaviors.

The new generated transport fixture closes only the fresh account's separate
index database through the original provider. It keeps the signed CRDT store
open and proposes nine real effects after index failure through both original
gRPC and generated byte dispatch: begin, import, import witnesses, seal and
ordinary association mutations. It checks preserved claim/change identity,
native signed history, no private resolution on error, and exact idempotent
retries without new appends. Six metadata records and four operation claims are
expected; the source fixture is not an execution receipt.

Its stop helper is compiled only under both existing acceptance build tags and
calls the original application `Stop()`. The fixture latches the first stop
attempt before assertions, refuses a second cleanup attempt, and accepts only
the original expected `ErrDBIsClosed` leaves from the deliberate index close.
The original normal shutdown still requires no error. The gRPC server's final
result must be nil or the expected stopped-server result. No arbitrary cleanup
error is reclassified as success.

## Next qualification boundary

Materialize a separate, byte-pinned source union from the qualified core40 and
RPC11 closure, apply this proposed overlay with exact original hash checks, and
create any required additive Go package directories only in that new tree.
Do not change the retained source's topology for `go vet`. Compile and run the
focused unit/native/transport/lifecycle controls under the existing coordinated
resource floors. Preserve the original result and source for every failed
attempt. Publish actual results and a qualified successor manifest only after
the complete intended controls pass without changing their acceptance rules.
