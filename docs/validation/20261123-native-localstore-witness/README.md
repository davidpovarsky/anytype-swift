# Native local-store witness: six new methods passed

## Actual result

At 2026-11-23 05:55 UTC, the six newly selected top-level methods passed.
Their 15 scoped subcases bring the original named start/pass pairs to 21.
There were no failures, skips, or reruns of previously qualified methods.

The real native interleaving used one read transaction whose collection inventory
completed before an independent owned writer committed through an actual native
WriteTx. The first captured witness retained 5 collections / 7 rows and the prior
state and binary payload. A direct native state read observed the committed state.
A later transaction captured 6 collections / 9 rows, the changed state/payload,
the inserted row, and the newly registered collection.

The independent auditor parses the two private length-framed witnesses and their
decoded-value encodings. It verified exact owner/Space continuity, old/new state
fields, unchanged other native rows, binary payload bytes, Unicode spellings,
collection coverage totals, and both full private witness digests.

## Source and evidence

Native source: 74b5f2c844ac3879125888c538d5990af3db3cb8.
Controller/source freeze: e49f9b137a24dfb3507b3d932ed09382ec58e0b2.
Compiled binary SHA-256:
99036b6b74b9914f9fd008d1f97a2d02146e0de55baf2dd4cd8a2b81a07636d2
(25,485,911 bytes; 53 actual dependency modules).

Six explicit native Git inputs and 4,039 resolved source/dependency paths stayed
unchanged before and after compilation/execution (4,040 unique paths).
The original binary, raw logs, 17 owned native databases and two private witnesses
remain on Oracle. Git receives safe counts/hashes, exact safe original metadata,
the event whitelist, source bindings and the independent auditor, not private data.

See qualification.json, original-artifacts.json and original/independent-audit.json.
The API/codec/execution contract remains frozen in
Tools/AnyEngineValidation/native_localstore_witness/PROTOCOL.md.

## Original pre-execution finding retained

Original native source 862e98d16b6ae55207a41b53a036d8b7660a189a was reviewed but
never compiled or executed. Root found an initializer field-name mismatch and
missing explicit InventoryScope. Commit 74b5f2c corrected that one initializer
line before the single actual build/run. Test source was unchanged.
The source preparation/review record remains in pre-execution-originals.json.

The explicitly authorized idle Swift cache reclamation is separately preserved
in capacity-reclaim-original.json. Both older qualified Swift products matched
their original Git-bound hashes before and after removal of only that cache.

## Acceptance boundary

This proves fixture-owned coverage of registered native local collection decoded
rows within one real read transaction. The detached encoding is a validated
re-encoding of values exposed by native Doc.Value, not original SQLite BLOB/page bytes.

The candidate has no production capability issuer. Unknown collections remain
unresolved. nativeSnapshotProofRequired and nativeIdentityCensusRequired remain true;
hasNativeSourceAdmission=false and permitsDestinationWrites=false.
No full semantic object/block/type/property/file census, production authorization,
remote-replica completeness, whole migration, Swift/App or mounted Apple acceptance
is claimed.

## Follow-up authority finding

The original interface's private marker is not, by itself, an unforgeability guarantee: an external Go type can embed that exported interface. The six original actual fixture tests remain valid at74b5 and are not relabelled. A separate concrete capability with a private acquisition closure is being qualified at native102f. No production issuer or destination writes are enabled by either candidate. The root evidence review independently rehashed all4,040 unique source/dependency paths, the binary,19 private native files and21 safe original copies; no original product method was rerun.
