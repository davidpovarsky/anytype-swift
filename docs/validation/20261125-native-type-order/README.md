# Captured Heart type order in the shared native catalog

Product: `5fb71c1849c86bf14b54325d5ffdc439bf8b1c29`.

The source catalog now parses a type's original `orderId` as an optional string. An absent field and an explicit empty string remain distinct in the typed model, prepared native metadata and retained original definition JSON. All imported types carry a display-only order contract scoped to the exact definition-catalog digest.

The shared native property catalog applies explicit UTF-8 ranks only within the existing slots belonging to that same imported source catalog. Empty and absent values sort after nonempty ranks; equal or unranked rows preserve the incoming native catalog's relative fallback order. Native built-in and unrelated types keep their slots. Collection order, raw type records, current native document eligibility and mutation authority are unchanged. This implements explicit manual ranks; it does not claim to reproduce Heart's separate account-dependent fallback preference or locale name collation.

The original Heart source confirms ascending non-collated manual ranks in `core/block/object/objectcreator/object_type.go::setTypeOrderId`, and the original Apple query uses `orderId` ascending with empty placement at the end in `Anytype/Sources/ServiceLayer/Object/TypesService/SearchHelper+Extension.swift::defaultObjectTypeSort`. These are preserved as source references, not a new native execution claim.

## Actual qualification

Seven affected component methods passed with zero failures or skips on the exact product source. The run includes the original immutable 156-snapshot source fixture; its producer's original FAIL remains FAIL. The unchanged context and manifest were read and all original snapshot members remained bound. The other six controls cover exact absent/empty/Unicode rank preservation, malformed fields, future contracts, different source groups, built-in and duplicate-source refusal, stable ties, and unchanged document eligibility and collection order.

- Original log SHA256: `81e83e2b4dc2a7b40c58e546f3198b1f762c004465924b0f2519f8deac25443d`.
- Controller duration: 65.708 seconds; original Swift build: 48.38 seconds.
- Source files and dependency identities were unchanged during the run.
- The owned process group was positively absent at 2026-11-25 20:16:04 UTC.
- Native calls: zero. Destination writes: zero. New Apple builds: zero.

The original fixture contains 20 types: one has a manual rank, 19 lack it, and none has an explicit empty rank. Its 126 property definitions contain 119 explicit null defaults, six absent defaults and one explicit non-null default. The source census contains no private account IDs or source values. It retains the original null-list representation in its counts.

The prepared metadata still needs one actual native persistence/readback and fresh-process cold check before this new presentation contract can be counted as native migration acceptance. The complete source remains blocked by the semantic requirements in [remaining-full-source-gaps.md](remaining-full-source-gaps.md). No source or destination admission was promoted by this change.
