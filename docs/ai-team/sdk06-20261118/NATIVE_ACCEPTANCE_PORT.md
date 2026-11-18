# Native Properties and document-source acceptance port

## Why the old selection could not pass

The initial Wave-15 acceptance helper compiled the application with
`PINKHA_NATIVE_DERIVED`, while
`PinkhaTorahPropertiesAcceptanceUITests.testOriginalPropertiesCanonicalLinkUnlinkAndRelaunchForAllWritingTypes`
required the retired `torah-property-ref` projection row. Production
`PinkhaTorahPropertiesModel.showsLegacyProjectionRows` is false under that flag.
The native Properties suite also explicitly requires that old row to be absent.

`PinkhaStage1AcceptanceUITests.testDocumentSourcesEntryOpensExistingSearch`
expected a Sources header on an ordinary Note and Page whose fixture had never
installed Sources. `PinkhaTorahPropertyPolicy.presentsSources(on:)` correctly
requires the native Sources property to be attached. The universal Properties
acceptance flow deliberately verifies that blank ordinary documents have no such
header before Add Property.

Root excluded these two obsolete paths from its initial runnable selection. This
patch makes their native fixtures and UI expectations consistent; it does not
establish an Apple acceptance result.

## Changed test contracts

- Stage1 preparation still creates a fresh local-only account and disposable
  Space. After verifying native Note/Page document shapes, it opens those two
  documents through the original document provider, verifies Sources/header are
  absent, and uses `ObjectPropertiesViewModel.onAddPropertyTap` plus
  `PropertyCreationViewModel.addPropertyToObject` with the actual catalog entry.
  It checks the native row/header, closes/reopens the document, and checks the
  persisted installation and empty source values. It does not change their Types
  or the production eligibility policy.
- Canonical writing-type fixture preparation verifies that all three native
  property keys are present and their canonical projections start empty before
  emitting the original fixture IDs/labels. Its existing JSON marker and state
  filename are unchanged.
- The canonical UI test opens the exact mounted fixture document, uses the
  original property name/value row and the fixed-scope native picker, and links
  Source and Topic through the existing search actions. After each completed
  mutation it cold-reopens the application and checks the actual native value
  row. It then removes each association and verifies both the cleared native
  placeholder and preservation of the other value. Original property labels
  remain checked throughout.
- The empty native tag-row value is the existing English `Select options` hint
  (`PropertyItemModel.hint`, regular `PropertyStyle`); it is not the retired
  projection row's empty accessibility value. Canonical UI remains an English
  label test. Values are matched against their visible native row geometry so an
  unrelated label elsewhere cannot satisfy the assertion.
- Native property sheets have no explicit close action in their current host.
  Cold reopening after mutation directly verifies persistence and avoids copying
  the older iPad-specific outside-popover dismissal gesture into a phone lane.
  The test does not claim to cover interactive sheet dismissal.
- The document-source UI method accepts the native search field's own identifier
  or the sheet identifier propagated by SwiftUI, and waits for the localized
  document-scope title. Its ordinary fixtures now legitimately have Sources.

## Selection and evidence

The original method IDs are unchanged:

1. `PinkhaTorahPropertiesAcceptanceUITests/testOriginalPropertiesCanonicalLinkUnlinkAndRelaunchForAllWritingTypes`
2. `PinkhaStage1AcceptanceUITests/testDocumentSourcesEntryOpensExistingSearch`

Canonical suite count remains one method; editor suite count remains three
methods. Native Stage1 preparation remains one `@Test`. Root owns the Python
selection/workflows and may restore these named paths after integrating this
patch. No root helper/workflow or T5 session/coordinator file was edited here.

`native-acceptance-port-parse.json` records the actual two-file Windows Swift
6.3.3 syntax parse with Swift 5 mode and `PINKHA_NATIVE_DERIVED`. `git diff --check`
passed. This is syntax evidence only: Apple typechecking, real property mutation,
relaunch, and phone/pad UI remain **NOT_RUN** for this patch. The unrelated SDK
native run 44209702553 was dispatched after the separate macOS fixture-path fix
60b0192d3c3458180f983db372a293536fc8a7a0; it does not execute these UI methods.
