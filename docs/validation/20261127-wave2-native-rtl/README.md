# Native RTL: exact app-language selection for the original journey

This change prepares the existing
`PinkhaAnyNativeUITests/NativeLaunchTests/testExplicitHebrewDirectionAndAlignmentSurviveColdReopen`
for both requested app/operating-system language pairs. It has not been compiled
or executed on Apple hardware. No current-product UI acceptance is claimed.

## Source change

Only that method in `NativeApp/UITests/NativeLaunchTests.swift` changes. The test
runner selects `PINKHA_NATIVE_RTL_APP_LANGUAGE=he` or `en`; any other explicit
value fails before creating an account. The compatibility default is Hebrew.
Every matrix invocation must select its language explicitly.

The Hebrew launch arguments remain unchanged. The English branch preserves the
same fresh account scope and original native-test flags and sets the app's
`AppleLanguages` to `(en,he)` and `AppleLocale` to `en_US`. The shared
`makeApplication`, cold-reopen helper, engine selector, Hanlin, MiniApps, sharing,
Archive and drag journeys are unchanged.

All original actions and assertions remain: create a paragraph, enter the same
Hebrew text, verify the saved status, preserve one block, force LTR before RTL,
select center alignment, verify the native saved-style readback, cold reopen the
same document, preserve the same block ID/body/count, and verify selected RTL and
center plus unselected LTR and natural alignment. The exact three saved-style
strings and two menu titles are selected by the requested app language. Their
English values match `AnyNativeDocumentView.savedWritingStyleDescription` and its
menu source; no alternative-label predicates are introduced.

Two `.keepAlways` app screenshots follow the existing exact native style
assertions: `NATIVE_RTL_<he|en>_center_before_reopen` and
`NATIVE_RTL_<he|en>_center_after_reopen`. They add no input action. Actual images
must be extracted from the original successful or failed xcresult and visually
reviewed when the shared product is available.

## Review and byte preservation

- Before file SHA256: `fdb706fc9d1c805ceb7220e4ae64a14244f7437525cf06d8d14e1b1f100de6da`.
- Prepared file SHA256: `e32f68676df1330c0255aa7ffa93b71c16f158570250013c607084f440c54375`.
- All bytes outside the RTL method are identical; the 18 declared test method
  names and their order are unchanged.
- Resolving the Hebrew branch and removing only the added configuration and
  screenshot observations restores every original action/assertion byte.
- The accompanying `source-proof.json` contains the exact before/after method
  blocks and an inverse that restores the complete original file. The original
  sharing title proof can then restore the earlier `0b4cbd…` source as before.
- The editor subagent independently reviewed the exact Swift diff, original
  launch/reopen helpers and product localization. It found no concrete compile,
  actor, relaunch or localization blocker by source inspection. No compiler was
  run for that review.

## Existing acceptance stays separate

The historical RTL method passed in run `45087682296` at source
`7293e4fd0bcabdcdb643d5768b777b8e87ff1b73`, on iPad mini (A20 Pro), iOS 27.2
build 24B8117, in 156.65911900997162 seconds. Its named receipt SHA256 is
`257f4fa40aa3c3b3375f7b479ca812fbcb98fc66e3aa6f5e9e7c9ee08dfa0500` and retained
archive SHA256 is
`6625e363c7cd9e4c256dfc116073687228db7a0564ae6f2aed8213eca089616b`.
The original batch remains 2 PASS / 4 FAIL / 0 skipped. Earlier failures,
including runs `45038244641` and `44695105165`, remain retained.

That PASS attests the original Hebrew-app journey. Its OS language and appearance
are not attested, so it is not counted as a cell in the new matrix. The original
360-second method allowance is retained. The passed drag journey is not selected.

Original repository evidence:

- `docs/validation/20261123-nativeui-source-drag/native-ui-continuation-test-methods.json`
- `docs/validation/20261123-native-ui-terminal/originals/native-continuation-retained.json`
- `docs/validation/20261122-any-ui-continuation/ORIGINAL_RESULT_AUDIT.json`

## Remaining execution

The required eight cells are the Cartesian product of:

| Dimension | Values |
| --- | --- |
| App language / simulator OS language | Hebrew / English; English / Hebrew |
| Device family | iPhone; iPad |
| Appearance | Light; dark |

The prepared host consumer already has fresh-device ownership, supported device
admission, opposite-language configuration with reboot/readback, and appearance
set/readback helpers. The NativeUI consumer must reuse those validators and its
original exact native descriptor, compiled-method enumeration and xcresult
parser. Dynamic type remains the existing `large` setting for this scope.

The new NativeLaunch bytes must be part of the same exact integrated source as
the successful shared product and separately qualified two-source NativeUI
runner. The existing Native16 `fdb706fc…` source pin must fail until the reviewed
inverse-bound profile is supplied; changing a hash alone is not qualification.
No source overlay, SDK/native substitution or manual product-path override is
authorized by this preparation.

All eight current-product cells, visual review, and physical-device validation
remain **NOT RUN**. Empty fields, lists, headings, quotes, selection, gestures,
keyboard and accessibility have their own editor acceptance requirements; this
single persistence journey does not establish those additional behaviors.
