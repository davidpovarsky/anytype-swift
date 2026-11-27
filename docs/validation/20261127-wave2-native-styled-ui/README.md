# Future native block-menu and live typography acceptance

This is a separate source preparation for the published native block menu (`dc582ba3239d6dcb66dbe1f7098b95349e4289f9`) and typography repair (`33e31c64ca9e35e258a4d64cfe8690b08a6cbc39`). Its product basis is the later, separately published Hanlin hook (`dfbb481102226e5484b5b8e4dd730661f9b03d14`); that hook's entire function is retained unchanged. It does not modify the frozen shared App source `8f2c11713fb8a40ae13444104723666ffef68afe` or qualify any current product. Apple compilation, enumeration, XCTest, visual review, simulator execution and physical-device review are **NOT_RUN** for these additions.

The entire published future accessibility NativeLaunch source at `0e964628b520f5f8f13c827f557ad9c585e7103c` is retained as a byte-exact prefix, including its 21 existing methods. The new suffix adds only these two selectors:

| Selector | Actual missing acceptance | Bound |
| --- | --- | --- |
| `PinkhaAnyNativeUITests/NativeLaunchTests/testTypedBlockMenusPersistAllNineKindsAndColdReopen` | Create the nine published choices through the real document menu, observe each empty field and persisted text, check the second UIKit “Add block before” menu once, then cold reopen the exact objects and blocks. | 1,800 seconds; one account and Space; nine small documents; one cold-reopen phase. |
| `PinkhaAnyNativeUITests/NativeLaunchTests/testNativeStyledTypographyRefreshesLiveAtAccessibilitySize` | Observe H1, code and an empty paragraph in the mounted editor while the owned simulator changes from `large` to `accessibility-extra-extra-extra-large` and back. | 900 seconds; one document with three short rows; each external setting response is bounded to 60 seconds. |

The nine small documents preserve the original observer's requirement that the **complete** native document be mounted and visible. Nine rows cannot reliably fit the iPhone viewport at accessibility sizes. The 24 KiB output limit, 64-block bound, exact native/rendered text and mark comparison, unique identity checks and pending-edit guards are unchanged. No partial-visible shortcut is introduced.

## Real observation and assertions

The existing `AnySemanticAnchorObservation` reads `AnyDocumentPresentation.read.snapshot`. A new, separately opted-in simulator-only field records its actual block type and full native style JSON together with the mounted `UITextView` attributed fonts, paragraph styles, typing attributes and content-size category. The existing fixture-scope/UUID checks remain in force. This readout makes no engine call, mutation, selection change, font choice or style normalization; all existing output fields retain their original meanings.

The UIFont evidence describes the **assigned UIFont**. It does not identify a per-glyph fallback face or replace the required screenshot review. Expected faces and nominal sizes come from the original DesignKit and original text-style mapping, not from invoking the new typography function. Native `pinkhaTextAlignment = natural` is preserved; the actual UIKit alignment must follow the original shared writing policy and effective application language. Explicit RTL and the empty paragraph's real typing attributes are checked separately.

The cold phase binds actual hierarchy object IDs to the native object hash, retains actual block IDs, full style JSON, native type, displayed text and markers, and requires a different App PID. The live-size phase requires the same App PID, native version, read generation, object/Space identities, block identities, native text/style and selection while the actual UIKit category and assigned point sizes change and return. Independent source review found that checking only the first expanded font run could miss partial refresh. The final predicate requires **every** attributed font run, or the empty field's typing font, to exceed that block's already-qualified nominal baseline.

Every successful observation retains typed native JSON, context JSON, AX text and a PNG. A failed read retains its last actual observation; the unchanged future accessibility finalizer retains final private AX/PNG before terminating, including failed startup. These attachments remain private fixture evidence and require the original raw xcresult manifest/export qualification before acceptance.

## External controller boundary

No simulator controller or setting mutation is dispatched by this preparation. The second selector uses a fresh test-runner Application Support rendezvous, bound to the original exact invocation, owned scope, runner PID/bundle, App PID, simulator UDID, request nonce and request hash. Only the existing sole NativeUI controller may service it. The response is coordination evidence; actual mounted UIKit observations remain mandatory.

Before execution, that existing controller must be extended and independently reviewed to:

1. Admit an actual successful future **same-source** App/UI producer, all exact source/native/SDK/product and two-file Swift compiler-input witnesses, with the reviewed 23-method NativeLaunch source. Current 19-method and 21-method profiles cannot admit this candidate.
2. Retain and verify the exact selected device, original app/OS language, appearance, initial `large` category, code carriers, fresh owned account/scope and runner data-container identity.
3. Respond only to the two finite requests in the known owned runner container. Reject stale, duplicate, aliased or changed request files and unsolicited settings changes; retain the original request, actual command output and response bytes.
4. Use the installed Xcode 27 `simctl ui <device> content_size [desired_size]` interface already observed in its read-only help. Read back using the same command without a size argument. Preserve the actual outputs and hashes; do not infer state from a successful setter exit alone.
5. Restore the original category and verify it in `finally`, including XCTest/setup failure or missing response. Preserve the first failure and append cleanup failures; either must prevent acceptance. No shared simulator or another agent's device is eligible.
6. Retain the original result, one selected XCTest case per invocation, raw attachments, process exit, original source/product/readback witnesses and mandatory screenshot review. No self-reported context or response JSON is sufficient to declare acceptance.

The initial context must specify app language `he` or `en`, the actual independently read OS language, device family and appearance. The existing cross-language/device/appearance admission remains the authority; this source preparation does not claim any matrix cell has run.

## Retained gaps and dependencies

This tranche depends on the separately published future accessibility prefix `0e964628…`, the menu and the typography change. It does not add block conversion, native RPCs, App state setters, renderer overrides or new production controls. An external same-ID/same-style type conversion is outside the UI journey because no supported typed conversion API has been established; the published type-cache invalidation remains source-reviewed and awaits an appropriate future runtime case.

Passed hierarchy-drag, historical T5 calls, Quote/Note and Topic/Word journeys are not replayed. Existing SourceDrag failures and Page154 failures remain intact. The public VoiceOver API probe from the accessibility tranche proves only that exact small probe compiled; it does not qualify this complete NativeLaunch source or any accessibility runtime behavior.

The separately owned Hanlin fixture hook was published as `dfbb4811…` after its exact SDK contract arrived. This read-only observation delta preserves that entire function. Removing the observation hunk restores the hook's exact editor; removing the hook instead restores the independently reviewed typography/observation editor. The two deltas commute without changing either body.
