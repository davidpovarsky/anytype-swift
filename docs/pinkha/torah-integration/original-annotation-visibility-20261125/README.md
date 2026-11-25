# Original annotation visibility — source checkpoint

This change composes one downstream policy into the original Anytype query
services. Default document/global/meta search and document Recents exclude the
registered Annotation type by the original native nested relation
`type.uniqueKey` with condition `notEqual`.

The policy obtains the key from the existing
`OriginalAnnotationNativeMetadata.originalTypeUniqueKey`. It does not duplicate
the registered type identifier, create a replacement query engine, filter a
paginated result after retrieval, alter access permissions or mutate objects.

## Explicit access and existing behavior

The existing original search type-token UI remains the explicit opt-in: selecting
the registered Annotation type passes its exact unique key through the original
`SearchWithMetaService` / `CrossSpaceSearchService` query. The policy's
`includeAnnotations` path then adds no exclusion, while the existing explicit
type filter stays in force.

Explicit nonempty type-ID queries keep their prior behavior. Original by-ID
loading, limited-ID lookups, relationship attribution, Archive listing, chat/file
search, templates and property queries are unchanged. The generic shared
`SearchFiltersBuilder` and `SearchHelper` are unchanged. Document promotion
changes the genuine native type, so a verified promoted Document no longer
matches this Annotation exclusion; that behavior still requires actual native
query proof.

## Exact source scope and provenance

Base: `8b1a9ba425eb6d47b397fb8973de5e9514066d39`.

Fresh original upstream `develop` was read with `git ls-remote`:
`d857b23ea540be33d6faab4f7a7a1a260ab578c1`.
Merge base is `d5650321577a209505a3277c8437b7608cff1cb9`. All four edited original
service files have identical Git blobs in the base, merge base and fresh
upstream; no newer change to these paths is omitted.

Downstream-owned new source:

- `Anytype/Sources/Pinkha/Torah/Annotations/OriginalAnnotationSearchVisibility.swift`

Narrow original composition hooks:

- `Anytype/Sources/ServiceLayer/Object/Search/SearchService.swift`
- `Anytype/Sources/ServiceLayer/Object/SearchWithMeta/SearchWithMetaService.swift`
- `Anytype/Sources/ServiceLayer/Object/CrossSpaceSearch/CrossSpaceSearchService.swift`
- `Anytype/Sources/ServiceLayer/Subscriptions/RecentSubscriptionService.swift`

The existing Sources filesystem-synchronized group includes the new downstream
file. The SDK's additive exact source-admission layer must explicitly admit the
new file and four reviewed original deltas before final qualification. Historical
complete-source manifests are unchanged.

A generic shared builder change would also alter explicit relationships,
Archive and unrelated callers. An external result wrapper would filter after
pagination and could miss results. These narrowly placed original composition
calls preserve the production query, pagination, sorting and account/Space
scoping while keeping the downstream policy in its own source file.

## Verification boundaries

This checkpoint records source and lineage review only. No Apple compiler,
simulator/UI, native query or permission acceptance is claimed by the source
change. The next focused gates are:

1. Compile these five exact files in the complete original SDK Swift source
   context, against the real installed Apple SDK.
2. Run the original engine query against a real registered Annotation and
   Document: default nested-type exclusion, explicit exact-type inclusion,
   archived explicit listing and post-promotion Document visibility.
3. Confirm the ordinary original search/type-token and document-Recents UI on
   the final integrated build.

The native owner holds the actual query/lifecycle runtime gate. Existing
Native66, ABI and prior SDK/typecheck evidence retain their historical source
identities. Current SDK public/Debug contract remains 175 requirements pending
the separately coordinated lifecycle facade expansion.

Rollback reverts only these five files. No stored schema or data migration is
introduced. Prior visibility/access code and evidence remain available in Git.
