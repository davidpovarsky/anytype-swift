# Exact Native text identity and semantic-anchor audit

## Frozen source correction

This work is bound to App commit `2752229aacf72f468f32a4bfe5fe0a91142f5dbe` (tree `2d8db7a1585d48b857578920fa19b3730dde488b`). This source publication contains the reviewed correction and two proposed regression methods. It has not been compiled or executed; the publication result separately binds the new immutable commit.

The Native presentation can discard a real edit when its new text is canonically equivalent to its baseline but has different stored bytes. For example, `U+00E9` and `U+0065 U+0301` have different UTF-8 bytes and UTF-16 lengths. Hebrew `U+05E9 U+05B8 U+05C1` and `U+05E9 U+05C1 U+05B8` have different UTF-8 bytes despite equal UTF-16 lengths. The existing inline codec and composition mapper preserve those distinctions, but two subsequent draft-removal checks use Swift `String` equality. The same mismatch exists in stale-base, acknowledgement and recovered-draft checks. `exact-text-case-witness.json` retains the concrete raw values and source route; it is not an executed Swift test.

The candidate replaces exactly nine storage-identity comparisons with the existing `utf8.elementsEqual` idiom:

| Source | Exact scope | Candidate SHA-256 |
| --- | --- | --- |
| `Modules/PinkhaAnyUI/Sources/PinkhaAnyUI/AnyDocumentPresentation.swift` | Seven comparisons in draft refresh, rendered baseline, ordinary draft retention, composition baseline/retention, native write preflight and readback | `82b5b2dd0ac3978ec6a867cb3f9220527e1a111e89a601c4f4e9baf15d2c38fb` |
| `Modules/PinkhaAnyUI/Sources/PinkhaAnyUI/AnyNativeLibraryRecovery.swift` | Two comparisons classifying an exact stored draft or an unchanged reviewable baseline | `2abe0317ede786772c8fb1f427f476d24605031fb7f929394f548cd9196e1155` |

The complete inverse in `exact-text-source-edits.json` restores both original files. The public initializer, private/fresh-client `AnyNativeNoteMarker` verification, HTTP client, mounted owner, account/Space checks, lease/version/authorization gates, save scheduling, attachment accessor and attachment-intent owner remain unchanged. There is no new model-publication fixture seam. The earlier unpublished seam draft remains in `review-v1-publication-seam/` as a rejected preparation, outside the active candidate.

Root and Torah independently reviewed the two product files. Their reviews are `root-independent-exact-text-review.json` and `torah-independent-exact-text-review.json`; both explicitly establish source review only. The change can cause a previously canonically equivalent recovered value to require review or conflict rather than be silently treated as already stored. It does not normalize or rewrite text and does not change search/title/label comparison semantics.

## Two actual-input regression methods, awaiting compilation and execution

The existing Native UI source has a suitable owned-account fixture. It creates a normal native workspace and document, obtains a real UIKit range, confirms an anchor, uses ordinary keyboard input, observes native/rendered data and cold-opens the same account. No new production fixture or authority API is needed.

`unicode_anchor_addition.swift` is appended to the complete exact original `NativeApp/UITests/NativeLaunchTests.swift` (271,344 bytes, SHA-256 `8d58c41e8907019bf67088900bb5c35843562edd669422573c1280f800500e86`). All 23 original method declarations and every helper body remain byte-identical. The full 281,769-byte candidate has SHA-256 `7d7d60d61cabaf7e8c968c4d30cd584100e9d90217f6b1b66441146cbf5d943b`.

| New source selector | Declared cases | Original-style allowance | Required evidence |
| --- | ---: | ---: | --- |
| `NativeLaunchTests/testCanonicallyEquivalentLatinTypingPreservesNativeAnchorAndColdReopen` | 1 | 1,800 seconds | NFC-to-NFD exact bytes, changed UTF-16 length, same anchor identity and block, actual saved native text, cold readback |
| `NativeLaunchTests/testCanonicallyEquivalentHebrewTypingPreservesNativeAnchorAndColdReopen` | 1 | 1,800 seconds | Reordered Hebrew marks with equal UTF-16 length, exact bytes, same anchor identity and block, actual saved native text, cold readback |

The new extension reuses the original observed document-creation transition and the original 60-second enabled/hittable Add paragraph predicate. The earlier080a/666d setup draft and the exact corrective inverse remain under `review-v2-unicode-setup/` and `unicode-setup-correction.json`.

Each method retains exact ASCII prefix/suffix guard text inside the one full-paragraph anchor. It requires the exact input SHA and UTF-16 length, one native/rendered marker at location zero, the original marker identity, a changed native source/version and then the same saved source in a distinct process and generation. UI text/guard comparisons use byte/code-unit arrays rather than `XCTAssertEqual(String, String)`. The original observer refuses pending edits and compares the complete current native snapshot with the rendered semantic text; a visible optimistic text value cannot supply success. Typed JSON, the original native observations and three screenshots per case are retained by the source. The new exact-value helper attaches its raw JSON and screenshot before the four unchanged exact assertions, so an actual byte mismatch remains available when the original `continueAfterFailure=false` aborts the test. The5f1f/b38b predecessor and exact evidence-order inverse are retained separately.

The test suffix SHA is `9a0880aebe30b7e2ac89794b75cdf049a792d3576bbfa1945c50693d9f78bcb1`. `unicode-anchor-source-inverse.json` binds the exact prefix, suffix and proposed 23-to-25 declaration change. The first static inventory regex omitted four existing `@objc` declarations; `source-inventory-attempt1.json` retains that failed inventory assumption. Correcting the inventory changed no source and executed no test.

These two methods are not an IME, recovered-pending-draft, partial-range, source-link, split/merge, clipboard or Undo/Redo acceptance claim. Current Native23 producers, profiles and selectors are unchanged. W3 must separately bind the integrated source, actual compiler inputs, compiled enumeration, two finite selectors and real results before any Native25 execution claim. No consumer has been opened or widened here.

## Other concrete anchor findings handed to their owner

| Finding | Exact evidence | Ownership and next boundary |
| --- | --- | --- |
| Native keyboard Return/backspace has no current mounted structural split/merge route in the audited path | `native-keyboard-structural-finding.json`, SHA `34caee56db65ba2715d190ae83a6fb84341fe2bdfd3d927157684616c2d6601c` | Root/W1 must identify or provide one atomic native structural operation. Existing one-block PATCH and independently journaled POST must not be combined as a synthetic split. |
| The original composed8ac Heart clipboard path copies semantic marker Params through copy/cut/paste | `heart-clipboard-finding.json`, SHA `0498c61b3fb9c112a622668ee34b771c31ae695088c3a441c041190f7ffa19c6` | Root/W1 owns native clipboard correction. Resolver rejection of foreign/ambiguous copied anchors is safe but does not satisfy no-cloning clipboard semantics. No Wave2 UI-only stripping was added. |

The clipboard finding uses eight actual composed8ac members whose sizes/hashes were verified against the original `8ac407e75a4bfb42c359a2f72b3822c44990caedf2351d00d78315de5c96a04b` manifest. Their fixed-path original custody is retained under `wave2-native8ac-manifest-intake/`. Upstream bodies were not substituted for that composed source. This is source reachability/data-flow evidence, not an executed native clipboard result.

## Existing source coverage and remaining actual acceptance

Shared `PinkhaSemanticTextAnchorTests` already declare before/inside/after edits, insertion boundaries, partial replacement/deletion, exact Undo, split/merge, clipboard no-cloning and scope/ambiguity rejection. `AnySemanticAnchorCodecTests`, `AnySemanticAnchorDocumentTests` and typing-continuation tests bind the shared representation to Native inline Markdown and document CAS. Their source bodies are retained/read; no historical test has been replayed or assigned new acceptance credit.

The current Native mounted selectors `testActualSemanticSelectionCancelCreateEditAndColdReopen` and `testSemanticSourceLinkSurvivesEditAndColdReopen` cover their declared full-range routes. Page154 preserves historical preparation/mounted/linked-UI passes and its actual 180-second linked-native enumeration timeout; the cause remains unknown and no test was invoked in that failed enumeration. Today its expired fixture requires the existing fresh six-stage sequence, not a TTL extension. Recovered original evidence remains published at `41f7bb3f0724ec5c9c56b1678545c495644c0ac9`.

The two ordinary Heart structural methods are already published and integrated, not abandoned drafts: source `a892500cfc552c9b975a49440fcf2f19fc1a6659`, integration `2cb70379375a751a8e19eaa24efbba830da1b424`, current Stage1 source `c1e37371…`. Their CLOSED consumer is `ee0986954f92861904130ea4e443b5ccb08594ae`, under `Tools/CurrentAppleValidation/combined_heart_semantics/wave2/heart-editor`; both retain 1,200-second allowances and their original 65/44 typed captures. They exercise ordinary split/merge, range replacement, history and cold reopening. They do not contain semantic anchor assertions.

The finite remaining anchor acceptance is:

1. Before/inside/after/boundary and partial-range edits in each mounted engine, retaining the same scoped marker and any linked source record, with actual native and cold readback.
2. Atomic split/merge preserving all relevant marker fragments, native block topology and exact unaffected fields; Native implementation depends on the coordinated structural capability above.
3. Real copy/cut/paste of full and partial anchored content in the same and another document, ordinary formatting/link preservation and native cut Undo; Heart implementation depends on the coordinated clipboard correction above.
4. Actual Undo/Redo of anchor-related text/structural edits, including stale-history refusal and cold saved state. Ordinary Heart2 history acceptance alone is insufficient.
5. The two new Unicode typing methods on a matching product, plus a separate actual marked-input IME and pending-draft recovery journey.

No device, simulator, native engine, compiler or test execution was performed for this audit/candidate. `current-source-custody.json` binds the 51 bounded App source files to their primary immutable Git blobs. All runtime and final integration ownership remains with root/W3 and the coordinated Native changes with W1.
