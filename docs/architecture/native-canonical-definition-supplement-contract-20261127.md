# Original canonical definition supplement

## Scope

`AnyNativeImportedDefinitionDirectory` accepts up to nine additional
`AnyDestinationCanonicalPropertyBinding` values. Each binding must validate
against its exact captured protobuf/JSON bytes and the unchanged source
manifest already embedded in the saved migration plan. This addition resolves
definition addresses for ordinary reads; it does not execute another migration
operation, admit a source capture, or grant write access.

The original 182-operation plan and mapping remain unchanged. The original
directory contains 13 qualified entries (one imported Type, seven imported
Properties, four embedded Options and the canonical name Property). The eight
additional bindings produce 21 directory entries and leave 129 source
definitions unresolved. These counts do not establish whole-Space semantics.

## Exact mappings

| Original Heart definition | Native owner | Native Property | Value meaning |
| --- | --- | --- | --- |
| `rel-description` | `any` | `description` | Ordinary property |
| `rel-id` | `any` | `id` | Translated identity |
| `rel-spaceId` | `any` | `spaceId` | Translated identity |
| `rel-type` | `any` | `type` | Translated identity |
| `rel-creator` | `any` | `author` | Destination-derived |
| `rel-createdDate` | `any` | `createdAt` | Destination-derived |
| `rel-lastModifiedDate` | `any` | `modifiedAt` | Destination-derived |
| `rel-lastModifiedBy` | `any` | `modifiedBy` | Destination-derived |

The original definition object ID remains the lookup key. The native property
ID is an address in a different namespace. Source Space/Type references use
their explicit mapping; native creator and clock fields describe destination
events. Original Heart participant identities and timestamps remain original
facts in their captured metadata. This contract never equates them with a
destination signer or newly created native event.

`supplementalCanonicalDefinitions` retains the entire validated source evidence,
including exact protobuf and JSON bytes. `canonicalValueSemantics` reports the
three meanings above. Existing `name` is also ordinary. Noncanonical entries
return no canonical value classification.

## Refusals and read authority

The initializer rejects duplicate source definitions, repeated native property
addresses, a binding that duplicates the plan's existing `name`, caller-chosen
owner/property/contract aliases, changed source bytes, a foreign source Space,
or a substituted canonical target Type. An exact current native descriptor is
still required by `AnyNativeImportedDefinitionStore`; an address alone does
not establish that contract.

The existing store checks the destination account, Space and current host
lease, performs two equal ordinary native reads, and refuses a changed
canonical descriptor. The supplemental bindings do not bypass these checks.

## Qualification

Component receipt:

`/var/lib/pinkha-w1-functional-migration-20261127/canonical-definition-components-attempt3/result.json`

SHA256: `d9bf1c3911219e2227c17db48726a8508030a20f7557f19934504f599b76c69b`.

Exactly one corrected positive method executed and passed in 4.554 seconds.
Two unchanged negative method passes are retained from attempt1. Their complete
method bodies, shared fixture helpers, production source, dependency pins and
original data match byte-for-byte. The retry accepts only the single documented
positive-expectation change. It records **one new + two retained**, with zero
skips; it does not claim three new executions.

Attempt1 remains FAIL: the positive test expected a sparse native declaration
where the established directory projection explicitly retains empty optional
fields. Production was unchanged. Attempt2's incorrectly short Sentinel job
deadline stopped provisioning before any test method; its raw RUNNING snapshot
and external failure receipt are retained. No unsuccessful attempt is promoted.

The native proof passed in
`/var/lib/pinkha-w1-functional-migration-20261127/canonical-definition-native-attempt3/result.json`,
SHA256 `afef209a66b65edf14dd2acff2d53b073e2bb37d1937928592af3f9378d0f3ab`.
One new method ran in two fresh native processes; both invocations passed with
zero skips. Both native processes inherited OS TCP/UDP outbound denial and
closed with exit zero. Every native and test process group was positively
absent afterward. The eight descriptor rows were byte-identical across cold
reopen, SHA256 `36a569578c011a3c5ce3d8825bca75c6ad24a92d21767646ecb07a59874a2118`.
Foreign Space and revoked lease reads were refused. The proof performed zero
prepared operations and zero domain writes, using unchanged qualified Products.

Native attempt1 remains FAIL at the unchanged 2 GiB initial runtime guard:
actual free space was 1,850,232,832 bytes, with no account copy or native/test
process. Attempt2 remains FAIL: a copy-allocation loop shadowed the controller's
HTTP base URL, so readiness failed before any Swift test. Its child exited -15
and its group was positively absent. The only correction was renaming that
loop variable; the lifecycle predicates and all product code stayed unchanged.

The existing 535 MB Swift cache was separately relocated with exact file,
symlink, metadata and dependency custody, retaining its original stable path.
All 6,906 entries and accepted Products were verified before retiring only the
duplicate old bytes. The original failed copy readback is retained: reading
`debug` changed its atime on the destination volume. Continuation corrected
only that access-time side effect and checked its target using the recorded
inode/ctime witness without another `readlink`. Custody receipt SHA256 is
`a049e79aa6e185cd2721cf1b18a61a268474275a3b2d00cb187fe41ef8f8d8e8`.
The native run retained a 2 GiB root emergency floor, measured 128 MiB initial
allowance, and an additional 512 MiB development-cache reserve. No accepted
component methods were rerun after relocation.

This qualifies exact native schema resolution. It does not qualify Apple UI,
current-value migration, original-history reconstruction or whole-Space source
admission. C remains open with 129 explicitly unresolved source definitions.
