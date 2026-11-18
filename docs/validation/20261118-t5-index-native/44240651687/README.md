# Actual Native T5 index freshness — 44240651687

Run: https://github.com/davidpovarsky/anytype-swift/actions/runs/44240651687

Status: **PASS_ACTUAL_NATIVE_INDEX_FRESHNESS**, on integration `15656bf3faeef0659fb8639a2e7f73727ad443b0`.

The job built two exact Linux ELF test binaries from Heart `d98420b1113536afd08cde6de9a5816f6d27ffff` with the approved r14/r15 inventories in source `947fbde24d5657d0e1229f45bb3993648884a8a1`. It ran the actual native RPC fixture in five distinct processes against one disposable account and Space. The raw phase logs contain five passing invocations of `TestT5AccountCompatibilityPairPhase`, no skipped/failed invocations. Their PIDs are 333, 370, 396, 417 and 441.

The four mandatory compatibility phases preserve the original canonical payloads, unknown fields, public projections and two actual block payloads across old/create, new/reopen, old/edit and new/recover. The ordinary r14 title edit survives. All 24 actual exports (12 JSON, 12 Protobuf) were hash checked again after download. Every phase proves `AccountStop(false)` success and a cleared application before shutdown. This execution did not exercise the optional account migration branch.

The fifth r15 process performed sixteen native freshness observations:

| Scope | Observations |
|---|---|
| Document identities | Reference update, unlink, label alias, provider separation |
| Block and source quote identities | Block reference update, Note block unlink, source quote reference update and unlink |
| Invalid canonical records | Foreign Space, foreign object, malformed payload |
| Object lifecycle | Archive/unarchive, Note/Page type change and restore, object deletion |
| Dangling targets | Block removal and source quote block removal with independent live graph traversal |

Its actual counters are 185 ObjectSearch, 34 ObjectShow, 22 canonical ObjectSetDetails, two archive changes, two type changes, two block deletions and one object deletion. The eleven canonical probes restore the exact original raw payloads. There is no explicit reindex or Swift invalidation RPC and no recreation of the original account, Space, object or block in the later phases.

The native canonical index deliberately still contains candidates whose target block has been removed. Actual live graph nodes show those blocks are no longer reachable. **Production Swift exclusion of those candidates remains NOT_RUN_SWIFT_HOST**; the separate optional Apple fixture must prove it. Coverage remains `indexedTargetsOnly`, Space-wide freshness is NOT_PROVEN, Apple runtime pairing is NOT_RUN, and the product capability remains disabled.

## Preserved evidence

The outer artifact is ID `14399013977`, 294,697 bytes, SHA-256 `1be4feb94abc6771e1350d2b010963a8e8b8dd7a9d8b75ad793f7152794909f6`. All 69 members are preserved byte for byte and enumerated in `archive-member-sha256.json`. The original controller revalidated all five reports and all export hashes; see `verification.json`. The separate 170 MB binary artifact was not downloaded locally; its build and identity evidence remain in the original CI receipts.

No receipt was rewritten to turn an index observation into UI or Swift acceptance. The raw evidence, original outer ZIP, API metadata and this analysis are separate files.
