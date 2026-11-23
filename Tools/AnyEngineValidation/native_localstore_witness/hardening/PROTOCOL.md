# Concrete local-store capability hardening

Status at source freeze: compilation and both selected methods NOT_RUN.

## Exact source boundary

Native source 102f6243edb17068048869b85bc151f177897a68 follows the qualified
74b5f2c844ac3879125888c538d5990af3db3cb8 source. This follow-up replaces only the
capability admission shape and updates its fixture adapters. The native transaction,
decoded-value codec, iterator detachment, close/error handling, bounds and receipt
gates remain unchanged. The original source, controller, manifest, products and
21-event proof at 74b5/e49/dfc remain immutable in the sibling directories.

The old private marker interface cannot establish unforgeability: safe Go permits
an external type to embed an interface and override its public methods. The original
six passes remain results at their original source and are not relabelled as proof
of this concrete API or a production authority boundary.

## Concrete capability and delegation

Capture now requires *Capability. Capability is a concrete struct with one unexported
acquire function. Nil and zero values reject before acquisition. There is no exported
constructor, production issuer, arbitrary path/store parameter or marker-based
admission. The fixture creates the private function from its own Acquire bound
method, retaining the exact original issuer pointer, owner and generation.

An external embedding type cannot become the concrete carrier or replace its private
function through a public Acquire method. Forwarding an issued pointer or copying the
issued value is ordinary delegation of the same private closure. It does not mint a
new owner or generation. Current-generation and retired-lease checks remain in the
original issuer/lease and Capture path. This is a safe-Go API boundary; it does not
claim protection against unsafe memory access or modified trusted package sources.

Lease still has a private marker for implementation scoping. The marker itself is
not an unforgeability claim. Capture accepts leases only returned by the trusted
private acquisition function.

The new exported fixture helper exists only in export_test.go under the explicit
pinkha_localstore_witness build tag and Go's test compilation. It is absent from the
product package and cannot issue production authority.

## Only the approved two methods

1. TestLocalStoreWitnessConcreteCapabilityRejectsExternalEmbeddingAndZero is new.
   It attempts nil/zero/foreign embedding and public acquisition override, then
   forwards an actual fixture-issued capability and checks retirement of its
   original generation. The override is never called.
2. TestLocalStoreWitnessOwnershipAndCancellation is the directly affected existing
   method. Only fixture setup now obtains a concrete capability from the same
   original issuer. Its six subcases remain retired-before, retired-after-inventory,
   wrong-space, unsupported-authority, cancel-after-inventory and lease-close.

Expected actual scope: two top-level methods and eight named starts/passes.
Exactly one new method and one directly affected existing method execute. The five
other original top-level methods are retained at 74b5 and must not be executed here.
The new binary may compile their unchanged source; that is not a test rerun.

No new native concurrency proof is claimed. The real interleaved ReadTx/WriteTx proof
remains the original receipt 3ca194d76d66dd1035dae6d077231e81e13c16fac524b05f11a226facb8f313b.

## Controller and private evidence

The separate controller is adapted from the unchanged original run.py whose SHA256
is 1ce12a2b4560d00a4b27e67ecf6ee35b52dace524f19fa72f5fd4ec91d0f4c7a.
Its source root accounts for this extra directory. It selects the exact two names
in both manifest admission and the anchored binary selector; expected child names
are included only for selected parents. It records current run counts separately
from retained original proof and does not require/recreate the old interleaving.

Build and execute retain native Git inputs, full resolved dependency input hashes,
actual commands/toolchain, source equality and original private output. Only safe
Time/Action/Package/Test/Elapsed metadata and private artifact hashes may be public.
Actual fresh fixture databases remain under a private 0700 root. No private row,
native identity or key is printed or copied into public artifacts.

Use the same warm pinned Go 1.27.4/linux-arm64/glibc profile, GOMAXPROCS=1, -p1,
CGO_ENABLED=1, GOPROXY=off, count=1. Keep 2.5 GB reserved capacity; no new build starts
below the unchanged 2.95 GB guard. No old cache or evidence may be reclaimed by this
controller. Each build/execute stage has its own immutable original receipt.

## Exclusions remain closed

nativeSnapshotProofRequired=true
nativeIdentityCensusRequired=true
hasNativeSourceAdmission=false
permitsDestinationWrites=false
productionCapabilityIssuer=false
productionAccountAuthorization=NOT_IMPLEMENTED
semanticIdentityCensus=NOT_IMPLEMENTED
filePayloadCensus=NOT_RUN
fullHeartSemanticMigration=NOT_RUN
AppleOrMountedAcceptance=NOT_RUN

This follow-up changes no Heart154 input, old staged Any/SDK candidate, shared writer,
App fixture, mounted admission source, original product or Asana record.
