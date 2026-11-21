# T5 R05: one shared alias connection

The new `T5ResolvedAliasIdentityTests.testResolvedAliasesRemainDistinctFromOtherVersesAndProviders`
connects the real `SefariaReferenceProvider` to `TorahEditorSession.inspectorSelection(for:)`
and both shared T5 query implementations. Controlled HTTP responses reuse the exact existing
`reference-resolved.json` bytes for Hebrew and English aliases. A second controlled response
names another verse. A different-provider canonical record remains a separate identity even
when every candidate has the same displayed label and document title.

The test proves alias convergence through the production selection mapper, exact segment
identity, provider separation, and exclusion of overbroad native candidates in both the
ordinary document and expanded target queries. It does not contact a live Sefaria server,
invoke either native query adapter, build the application, or run a simulator.

The six original provider methods remain qualified by the original 2026-11-02 log at
`653aa1aac2e61987999d1a54fcdd91e1cfcae228`. Their provider/client/transport/test/fixture Git
blobs match this source. The controller verifies that retained log and source closure and
executes only the one new method. Existing native query and mounted UI evidence have their
own source and runtime boundaries; this package proof does not replace them.

Dispatch the fixed `t5-r05-alias` route with the reviewed source commit. The controller first
checks exact source and dependency resolution, then requires both the original successful
XCTest terminal record and exact-one xUnit record. Zero tests, duplicates, other cases,
skips, failures, changed locks or different dependency pins cannot qualify.
