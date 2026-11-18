# Private ObjectExport boundary — account failure and scoped repair

## Observed failure

[Run 44237407166](https://github.com/davidpovarsky/anytype-swift/actions/runs/44237407166), attempt 1, ran exact App source `285bb717eae9d4a031d704da7dee5907c037e418`. Both pinned native binaries built. The first new-client phase advanced through private factory creation, native append/read/idempotent retry, signed-storage checks and the ordinary Page Protobuf export. It then failed because a direct private-root ObjectExport returned top-level `Error.NULL`.

The fixture failed **before** checking or saving the private Result. The original evidence therefore proves neither private content disclosure nor an empty/omitted result. There are **zero complete phase passes**; the remaining three phases did not run. The original artifact and exact digests remain preserved on GitHub and in `verified-failure.json`.

## Source evidence

On pinned Heart `d98420b1113536afd08cde6de9a5816f6d27ffff`, `ExportSingleInMemory` marks success whenever its inner call returns nil error. `writeDoc` converts the directly requested object's state even when collection has omitted that object. The Protobuf/JSON converters serialize the provided type and snapshot; the type conversion is a numeric cast. The private source supplies a hidden structural envelope containing its native root/Space identity and unique key, while its signed operation history stays outside the generic state. There was no explicit private-type guard in this export context. These are source findings, not a claim about unrecorded Result bytes from the failed run.

## Bounded repair

The export context now uses a scoped getter that checks the actual immutable native SmartBlock type before the caller can lock or read state. It rejects the private operation type and forwards ordinary lookups, existing lookup errors and cache-removal operations. The shared service's picker remains unchanged. The two constructor hooks cover ordinary single/list contexts and the independently constructed Collect context, including AnyBlockV2 reached through this service. No T5 anyblock implementation is modified. Direct construction of an AnyBlock exporter outside this service is not claimed to be covered.

Focused native controls cover both getter variants, scoped/copied contexts, ordinary/error/nil lookup behavior, removal delegation, single Protobuf/JSON/Markdown/AnyBlockV2 rejection and list/Collect rejection before state access or output creation. Native execution of this repair is pending when authored.

Seven additional account-fixture diagnostic lines report only format, result length/hash, numeric RPC error and report status/counts. They never emit Result bytes, object IDs, issue text or account secrets. The original nonnil-error, nonzero-error and empty-result assertions remain unchanged.

App capability remains OFF. This repair does not establish successful real-account typed-handler execution, generated RPC, two App clients, old-client lifecycle acceptance or full T2.
