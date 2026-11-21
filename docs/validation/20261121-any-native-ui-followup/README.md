# Any native UI follow-up and real Files archive acceptance

Status: implementation and focused portable validation complete; the changed native UI journeys have not yet executed on Apple hardware/simulator. Nothing here closes the native UI or full migration acceptance task.

## Original execution retained

Run [44948053285](https://github.com/davidpovarsky/anytype-swift/actions/runs/44948053285) executed commit `c6ecc8ae89891b335434faec36f40b3b63e79334`. Its original artifact `14726365685` has SHA-256 `c9921459b644923a68a18f6344b3ba4108a55f1d70abcef4f4f087e8ac4c8f65`. The original xcresults, logs, screenshots and failed qualification receipts remain unchanged in the private build evidence.

Eight real UI methods failed. Six stopped while waiting for the first native text view after Add paragraph. The actual synthesized tap matched the visible empty-state button; the available evidence does not establish whether the action failed to dispatch, awaited a flush, lost its owner, or failed native creation/readback. The source-Inspector method had already inserted a quote but its expanded real Inspector covered the editor in accessibility. The topic/word method queried derived Properties rows before scrolling the lazy List.

The raw picker-observation method passed, while its original aggregate qualification remained FAIL. That method proved modal coverage only. It never proved saving a file, importing it, explicit remapping, or persistence. It is not selected again by the new focused scope.

## Changed product and test behavior

The document surface records bounded DEBUG-only noncontent phases under the existing explicit disposable UI-test scope. The record contains readiness booleans, phase names and local request UUIDs, never document text, account/object/block IDs, tokens or native error descriptions. Notification observation does not add a SwiftUI scene-phase render dependency. The read-only host collector validates the schema and bound before copying these records and can never supply acceptance.

The existing source journey collapses the real sheet before checking the background quote. The existing Properties journeys scroll the actual Lists, and visibility toggles use the actual physical switch when one is exposed. Existing acceptance assertions remain in force.

The archive sheet offers a normal user-visible `Documents/Exports` directory through Apple's Files integration. Native databases, journals and secrets stay outside Documents; see `storage-boundary.json` and the storage audit below. Security-scoped import retains the coordinated bounded read. The native app also declares the exact custom source-transfer UTI already exported by the pinned TorahInspectorKit; this addresses the observed missing-declaration warning without changing its transfer format.

A new, distinct method, `NativeLaunchTests/testCanonicalArchiveFilesRoundtripPreservesMappingAndBodies`, creates a private synthetic source and destination. It uses the actual provider/Inspector, system Files save/import controls, explicit destination-block mapping, confirmed native import, one process cold reopen, and re-exports both documents. It checks exact UTF-8 bodies through the native UI. Its read-only postflight opens only the three uniquely named files actually saved in the owned app's Exports directory. It compares full canonical payload/provenance with only the explicit location remap and permitted readiness-generation difference. Canonical archives contain associations, not the document body; the separate UI assertions are the body proof.

## Efficient execution boundary

The focused workflow uses one app build and the existing strict native binary reuse.

1. Run the one existing create/edit/Hanlin/background/cold-reopen method and require its actual named one-case receipt. An empty, extra, failed, skipped or wrong-destination result fails the step.
2. Only after that gate passes, run the other seven pending native UI methods from the same build.
3. Independently after the first gate passes, run the new archive method alone from that build, then its read-only canonical postflight. A failure in the independent seven-method group does not relabel or suppress the archive result.
4. Preserve diagnostics and clean up only the owned provider/simulator.

The original UIKit14 producer remains run `44942212731` at `96173b0afc6b360c8f780ae70c6c80042fda98da`. The review file binds eight exact before/after Git blobs that those fourteen component methods do not execute; 61 protected files remain identical. Changed files are separately labelled reviewed-different and never reported as passed by that producer. Renderer, focus, composition, render policy and test files cannot be excused by this review. Generic strict matching remains the default; the focused workflow explicitly requests this fixed review record.

## Validation retained with honest scope

- Original 19 portable controller checks: PASS; original log and exact input hashes retained. The Windows attempt timed out before producing a log and is separately recorded as not qualified. The successful execution used copied exact sources under Python 3.12 on Linux.
- New exact-profile controls: four methods PASS, covering selections 1/7/1 and rejection of extra/failed/skipped or inconsistent execution. Their observed tool result and source hashes are recorded separately.
- The comparator's twelve previously executed controls remain unchanged; this commit does not create a new execution claim for them.
- Swift syntax: earlier five-file parse PASS and diagnostics-only Foundation typecheck PASS; three subsequently changed files parsed again successfully. Original receipts and explicit CRLF-to-LF source normalization are retained. This is not an Apple UI typecheck.
- YAML and changed shell blocks: PASS. Other four workflow jobs, including the isolated authorized-read candidate, compare unchanged. Independent read-only workflow review found no blocking stage/count issue.
- Actual changed native entry1, followup7, archive1 and canonical postflight: NOT_RUN. Full acceptance remains open.

## Storage audit

The source-bound audit records the exact paths/blobs supporting these facts: the executable selects `AnyNativeApplication.defaultDataDirectory()` in production; that directory is Application Support/PinkhaAnyNativeV1 and is forwarded to the C runtime. Native creation and Hanlin journals use Application Support/Anytype. Account credentials use Security's Keychain APIs with device-only accessibility. The UI fixture uses its own temporary directory and Keychain namespace. This change creates only the intentional user export directory under Documents.

Apple documents that enabling both [file-sharing keys](https://developer.apple.com/documentation/fileprovider) exposes Documents through Files, so the private storage audit precedes those keys. The normal [file-dialog default-directory modifier](https://developer.apple.com/documentation/swiftui/view/filedialogdefaultdirectory(_:)) selects the Exports folder without replacing the system picker. Unavailable or ambiguous actual Files controls produce bounded private failure evidence and a failed test; they are never simulated or accepted as a successful journey.
