# Consumer contract for the original catalog and metadata

## Construction and lifetime

The owner supplies an admitted saved `AnyDestinationMigrationPlan` and the exact ordered `[AnyDestinationMigrationMapping]` produced by its committed journal. Construct `AnyNativeImportedCatalogDirectory(plan:mappings:)`; never synthesize mappings from display names, xKeys or catalog-carrier IDs.

Construct `AnyNativeImportedCatalogStore(client:workspace:)` or `AnyHeartOriginalMetadataStore(client:workspace:)` for the current destination account and Space. Execute reads inside the existing `AnyApplicationSession.perform` closure and pass its actual `AnyHostLease`. The returned snapshots carry that workspace, generation and engine-start identity. On account/Space/run retirement, discard UI delivery through the existing owner lifecycle.

The separate cold-context loader is producer-owned follow-on work. These APIs do not discover or reconstruct a missing saved plan, authorize migration, or resume an incomplete import.

## Catalog result

`read(sourceObjectID:directory:lease:)` returns the exact original head identity, source role/native type/unique key, archive URI, original tree JSON and optional captured snapshot evidence. It validates the saved immutable intent, current native receipt, native schema, signed creation and stable current row. Current READ must hold before delivery.

A missing catalog head throws `missingHead`. A catalog head without a snapshot can still be read as a catalog entry. A consumer requesting metadata for it receives `snapshotNotCaptured`. It must never display an invented empty object or treat missing evidence as an absent relation.

## Historical metadata

Construct `AnyHeartOriginalMetadataBinding(evidence:)` only from the exact captured original relation definition. Its decoder revalidates the original definition and closed contract; merely changing a serialized role or contract cannot grant a binding.

`read(_:sourceObjectID:directory:lease:)` independently validates both the metadata definition's catalog row and the requested object's catalog row. The result is `absent` only when a captured snapshot exists and that exact UTF-8 relation key is missing. `present(AnyJSON)` preserves null, false, zero, empty text, empty arrays and the original value shape.

The snapshot explicitly reports `permitsDestinationWrites == false`, `provesCurrentSourceValues == false` and `originalHistoryReconstructed == false`. This is a read projection of preserved source facts. Current native author/time/identity fields keep their existing authorities; no duplicate editable field should be created from these values.

## Integration handoff

The two production files are `AnyNativeImportedCatalog.swift` (19,519 B, SHA256 `bf886d81f6b0fe7b724f0e347f991681e7ca9d6599476ee13dbce9fb1a84b50b`) and `AnyHeartOriginalMetadata.swift` (8,689 B, SHA256 `54710744dc013f3ab48c823d48a6310e0ca537957ccf9800ef0b3219f18cb6c0`). They use the existing prepared migration, immutable records, history, membership and session interfaces. Hanlin, MiniApps and Otzaria should consume those shared authorities through their existing adapters; this handoff edits none of those applications.

Component qualification and actual Native159 proof are separate from a coherent final Apple/App producer. Wave 3 chooses the integration commit; Wave 2 owns the mounted presentation.
