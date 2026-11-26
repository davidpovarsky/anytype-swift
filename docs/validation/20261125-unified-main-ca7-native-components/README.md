# Unified App, complete UI continuation, and native component evidence

## Exact build identity and custody

Actual original App build-for-testing: **ca7cb16f91c3d5fc4f7c8c178369abc9276e9a07**, 296.557 seconds, exit 0. This is a Debug simulator build containing both real engines, not a distribution Archive or physical-device acceptance.

The initial complete original UI bundle failed on the new source-review test's actor isolation. The unchanged App was retained. The full UI bundle then built from **8aa603ddb179a98a711a1cb2208d556a498c602f**, 6.341 seconds, exit 0. Only two Self.isDigest qualifiers and the pure helper's nonisolated static declaration changed; all original test bodies and assertions remain unchanged.

The actual mixed provenance is explicit in build7-ui2/receipt.json: sameCommitForAppAndUITests is false; appBuildsThisContinuation is zero. No receipt pretends the App was rebuilt from the UI derivative. The 4,453 source inputs matched before/after. Original 4,602-product inventory, all xcresults, and full build logs remain on the Mac, hash-bound by manifest.json. Both prior failure and subsequent UI success are included.

Native source manifest: **70f0b2a66286ae87afdc5a8d5becb267fd1aa5c5110e54381a3b0384afd69a72**. Simulator Lib SHA256: **c3374a58dffb64658fe6840ee9bd2711a4b1bf8c449c32da5bd51ede4901cece**. Canonical Hanlin SDK: **30e5f09f8494d913fa36e75f877b541020c92ee0**, marker SHA256 **0ae5a1476c899b1790f01a2a3b4118034e848d8ad8dcf2d97f12104f7387f798**. All 56 dependency pins remain bound by Package.resolved SHA256 **ffc47556534ee279d01bb771c6d49637766e8828bd872cce739e541d8ce4f124**.

## Actual native acceptance

The exact ca7 App executed **2 tests, 2 passed, 0 failed, 0 skipped**, with no App/native rebuild:

- testMiniAppsNativeReplacementPreservesFormattingAndAcknowledgesAfterReadback
- testNativeBinRestoresExactObjectAndBodyAndRejectsRetiredPresentation

The formatted-text fixture now uses actual rendered text length instead of Markdown source length. Original outcome assertions and native validation remain intact. Together with the four unaffected original MiniApps methods accepted at preceding 94d, the five distinct MiniApps native controls have passing evidence. This does not qualify cross-app companion UI or complete Hanlin UI. New Bin UI remains unrun.

Private native data and keychains were retained before owned-simulator deletion; owned process groups were absent. Originals remain under /Users/m1/builds/pinkha-dual-main-20261125/.

## Unresolved original UI results

| Scope | Actual result | Observed boundary |
| --- | --- | --- |
| History | 1 failed, 0 skipped | Fresh backup acknowledgement failed before History. Accessibility frames were infinite/zero; new keyboard-selection preparation was not executed. |
| Hanlin | 1 failed, 0 skipped | Real account, document contents, selected block and cold reopen succeeded; tapping Hanlin did not present the connection sheet. No SDK tool/continuation UI pass is claimed. |

These runs overlapped; that alone does not prove an infrastructure cause. Original failures, recordings, accessibility snapshots and private native sandboxes remain retained. Subsequent UI diagnosis uses isolated runs without relaxing assertions. Previously accepted hierarchy-drag/cold-reopen evidence is preserved separately.

## Files export and private network settings candidate

Original Archive UI failed because the shipping app did not expose Documents exports in Files. Candidate source declares Pinkha's display name, file sharing and the existing canonical archive type. Imported network YAML settings move from Documents/Servers to app-private Application Support/Pinkha/Network/Servers, retaining exact filenames/bytes/inodes and selected custom network. Conflicting destinations, symlinks and unexpected entries refuse without deleting either original. An unavailable selected custom network throws instead of silently selecting a different network.

Actual APFS component qualification at **ef34fd3bdc78182eabd861a8a165aace25bb1668**: **7 original methods passed, 0 failed, 0 skipped**, source/assertions unchanged. Earlier 450676 and 4d136 failures remain included: they exposed nonexistent-suffix symlink handling and Foundation's canonical Darwin /var alias. The final helper validates the existing canonical app container and each descendant before directory creation. Original final log SHA256: **b0a380f4d7a3415ec823d433dcaf3345908ae2819d20a320b152c2397a1953e7**.

This component pass does not qualify the next App build or original Archive Files roundtrip; both remain required.

## Limits

manifest.json hashes every included original receipt and references full source/product inventories and build logs. Raw source captures, recovery material, keychains, screenshots and recordings stay private on the Mac. No broad task, full migration, final Release or TestFlight completion is inferred from these scoped results.
