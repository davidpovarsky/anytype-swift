# Original native schema: source audit and limits

Root inspected immutable Anytype Heart commit d98420b1113536afd08cde6de9a5816f6d27ffff through Git objects, without reading or changing the dirty Heart worktree. SOURCE_PROVENANCE records six exact blobs and SHA256 values. The complete small relation/type/helper/unique-key files, relevant original create entrypoints and runIndexer method were read. This is source analysis, not native execution, registration or UI evidence.

## Fixed schema identity

Original core/domain/uniquekey.go maps ObjectType to ot and Relation to rel. UnmarshalUniqueKey splits on every hyphen, rejects more than two parts and rejects an empty internal key. A canonical hyphenated UUID therefore cannot be inserted verbatim as the internal component. The original type helper accepts a supplied UnmarshalUniqueKey without checking its smartblock type against the requested type, so the future adapter must require its exact fixed ot-prefixed key, not any parseable key. Original relation creation uses NewUniqueKey(Relation, relationKey) and NewDocWithUniqueKey. Both routes use original derived-state creation; ordinary ObjectCreate does not expose that internal UniqueKey.

Display names and apiObjectKey are not native identity: their uniqueness helper errors are logged. Exact schema admission must validate native type/relation ID, Space, uniqueKey/relationKey, relation format, active state and protocol metadata through original readback. No names, index count or copied DTO may satisfy that boundary. Dedicated annotation classification remains outside the existing chiddush/article/research document registrations. No fixed schema names or migration behavior are installed by this audit.

## Creation uncertainty and visibility

Original core/create.go forwards ordinary details, internal flags, template and object-type key. Its WithChat error check occurs after CreateObjectUsingObjectUniqueTypeKey; the future annotation adapter must keep unsupported WithChat false and conservatively preserve any dispatched uncertainty. Original smartBlock.runIndexer logs index errors without rolling the native object back. A zero-result index query after uncertain creation therefore cannot authorize a second create.

A type value alone does not prove exclusion from original search, recents, object lists or creation menus. Those visibility surfaces need their actual original filter paths and UI readback. The current original deployment also needs genuine device products and account/runtime configuration; the Debug Simulator qualification factory is not production authentication.

## Authority and local commit

The original SpacePermissions predicate is participant.canEdit AND (not legacy stream OR owner). A moderator-only channel capability does not prove this. Participant-role and actual SpaceView restrictions need separate original lifetime captures, synchronous invalidation before publication and fencing of stale start/stop callbacks. The separately reviewed participant-only candidate remains unwired and has a newly identified start/stop reentrancy gap under repair; this audit does not qualify that candidate.

Raw ObjectDetails returned after original exclusiveRead release remain observations. A future opaque identity receipt and single consumption must remain inside the held original barrier, acquire actual SQLite serialization, obtain nested original synchronous read admission, recheck exact pending/source/scope/attempt and finish a true outerCOMMIT without await. Identity recovery remains distinct from body application and ACK. Existing standalone-six and held-read-two evidence are bounded fixtures, not original native identity evidence.

## Inspection recovery

The first source-print attempt stopped at a cp1252 Unicode encoding error. A second read found the supplied pkg/lib/domain path absent; immutable tree discovery identified core/domain/uniquekey.go. Exact snapshots were reused and the completed UTF8 audit retained both facts. No engine operation or test was run.
