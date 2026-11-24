# Captured definition timestamps and original custom source

Production source `ec6422464feb7ed1b535ab9faf55c155544ed698` adds an explicit source-only provenance classification for native definition `addedDate`. It applies to native Type, Relation and Option rows (528/521/529). Present values must be exact signed integer Unix seconds; absence is distinct from null. The exact original AnyJSON, protobuf and JSON-view bytes remain retained. The target receives separately named source-provenance metadata and never substitutes this value for target `createdAt`.

The native basis is Heart `core/block/editor/smartblock/detailsinject.go`, `injectCreationInfo`: the original-created timestamp and import-added date have different purposes, and AddedDate is written once because later tree timestamps can differ. The native bundle declares AddedDate as a date with time and readonly value. This change preserves that source definition provenance; it does not create a general user-writable substitute for Heart's readonly system fields.

## Actual original custom bundle diagnostic

One new Swift diagnostic passed on the independently retained original custom capture from run 45492064232: 156 snapshots, 20 types, 126 relations, four options and two typed Pages. Context SHA256 `bb03b5a06a77d8b3e85cd46bc9cedc8a497c2bb06bbcd3e47b834e13d83b934a`; manifest SHA256 `cbfb3aa1fd89707138adeccbce7389c40dc0a993f2285f6e517120e4e4239ed4`. The complete declared bundle is read and verified, followed by exact option/member provenance joins.

The diagnostic checks all four original option descriptors, source timestamps, actual persisted positions, exact ordered type recommendations, and the seven custom formats. Empty text, zero, false, date values, empty/selected choices, canonical title ownership and deferred mapped object references retain their distinctions. The actual ordinary Page unique key is retained as `page`; it is not used as its object identity. Two native option positions differ from the originally requested positions; only the captured values are used.

The original native custom method is still labelled FAIL in this immutable fixture because its final test assertion expected an empty public Page unique key. This Swift diagnostic explicitly checks that FAIL label and the absence of source-admission promotion. It does not relabel the original native run, erase its failure, authorize writes, or prove full migration. The independent native fixture correction has its own later acceptance gate.

## Focused verification history

The first focused run at ec642 compiled and recorded one actual-custom diagnostic PASS and one synthetic control FAIL. The synthetic control incorrectly selected the namespace anchor by shared sourceObjectID instead of selecting the intended property operation by its unique prepared sourceKey. Fixture-only commit `78c69638a8b91b066516d503ed6835b0e0fbd53b` corrected that selection; all production hashes remained unchanged.

Only the affected method was rerun. It passed at 2026-11-24 22:21:09 UTC with no failures/skips, checking signed/zero/absent timestamp retention and rejection of null, bool, string, fractional, array/object and unknown semantic alternatives. The original actual-custom diagnostic was not replayed. Thus two distinct methods are qualified across their recorded source versions, not a two-method run at the final head.

The original logs are bound in the companion JSON. This change is separate from the real target-native choice/reopen proof and from the root-owned Page composition and presentation controls. Non-null default behavior, unqualified layouts, source-derived readonly semantics, history and complete Space destination execution remain explicit blockers.
