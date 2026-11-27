# Native Properties Name cancellation and Undo — one future UI case

**Source candidate only. No Swift compilation, enumeration, simulator, Native operation or UI execution has run.** This is one appended XCTest method; no product, observer, controller, fixture API or existing test is changed.

## Why this case

The retained native hierarchy/type journey already covers a successful Name edit and visibility changes. It does not exercise the Name editor's Cancel action, the original **Undo property change** command, or the persisted result of that Undo. This new method selects those missing interactions without performing or selecting the accepted hierarchy, drag, custom-Type or visibility journeys.

The immutable current Properties view exposes the existing native Name row, value editor, Cancel/Save controls and Undo menu. `AnyNativePropertyPresentation` commits and undoes through the same native property operations; it accepts only verified-current readback and then reloads the document. The test reads actual UI values, Library object IDs and the existing read-only native/body observer. It adds no property state injection, direct HTTP call, test-only writer or permission override.

## Exact selector and sequence

`PinkhaAnyNativeUITests/NativeLaunchTests/testNativePropertyValueCancelAndUndoSurviveColdReopen`

One method / one declared case, with a finite 900-second execution allowance. Existing source-bound consumers remain unchanged and cannot be relabelled as admitting this new source.

1. Create one account/Space and one document through the original UI helpers. Create and save one Hebrew paragraph. Retain the original native body observation and block identifier.
2. Open the original Properties panel. Replace Name through real text input and **Cancel**; require the original value, then reopen the editor and require that same value before a deliberate **Save**.
3. Require the saved Name, invoke the original **Undo property change** action, and require the original Name and unchanged selected Type. Close Properties and verify exact native object/Space/block hashes and unchanged saved body/source bytes.
4. Identify the actual Library row, cold reopen through the existing account helper, and require the same object ID, original Name, body and block. Original native observations must show a different process and document generation.
5. From that reopened panel, perform one further deliberate Name save. Cold reopen again and require the same object/block/body with the final Name, unchanged Type and another process/generation transition.

There are six planned UI JSON/AX/PNG checkpoints and five observations through the original native/body helper. Native context in each Properties checkpoint is explicitly identified as the latest original body observation from that process; the UI Name is not falsely described as an added native raw-metadata field. No new collector is introduced. XCTest's eventual original result and source/product admission remain authoritative.

The value sheet must be absent before the test scrolls the parent Properties list; enabled/current Name is then required before another edit. Replacement uses the already existing command-A/Delete keyboard path. Original creation uses `createNamedItemWithObservedTransition`, preserving the known creation-transition correction.

## Source ownership and preservation

The exact 281,769-byte Native25 prefix is from Editor's published `13dc5b060c23527aeaedb1d1e250a86c9a2fc17c`, SHA `7d7d60d61cabaf7e8c968c4d30cd584100e9d90217f6b1b66441146cbf5d943b`. All 25 original declarations and every prefix byte remain untouched. `properties_undo_suffix.swift` is the only appended source; the candidate has 26 methods. The older 23-method prefix, original owner-sharing method/900-second allowance and dd251 rendered-title detector are consequently preserved exactly.

`candidate-manifest.json` and `source-inverse.json` bind the full prefix, suffix and candidate. `primary/NativeLaunch25.json` retains this agent's direct immutable GitHub readback; the property model is likewise read directly at App275. Existing exact App275 view/store reads and the original observer source are retained under `source/`. No current App or NativeUI source/product pin has been silently updated. A future matching product and separately qualified Native26 runner/selection are required before execution.

## Privacy and failure evidence

All screenshots and accessibility captures occur only after a real owned document has been created and its saved native/body observation succeeded. Captures explicitly exclude backup/recovery and account-gate screens. The test never opens ShareLink, reads an invitation or recovery phrase, or contacts an external recipient. A bounded final marker and safe current AX/PNG are retained before app termination, including failure paths once the document fixture is safe. Evidence-size failures remain test failures.

## Sharing and Bookmarks remain separate

The proposed revoked-invitation recipient test was not authored. The original Join view maps all non-cancelled errors to one generic failure message, so observing that message cannot distinguish revocation from offline/provider failure. A future owned recipient journey needs a paired actual typed Native rejection receipt before revocation can be credited; this is an **unmapped evidence requirement**, not a demonstrated product revocation failure. Approval/decline, accepted-member roles and sharing Refresh remain open.

The existing Bookmark opening route likewise needs its original imported layout/type/source-role/visibility fixture. This Properties Name case makes no Bookmark or imported-layout claim.

No optional build-custody operation, remote filesystem mutation, compiler/account process, Mac action or runtime slot was started while preparing this source.
