# Semantic text anchors: portable core and codec checkpoint

This isolated, unpublished checkpoint contains seven Swift source/test changes and retains 20 original passing Swift Testing methods. It is a reviewable shared model/codec increment for EDITOR-02. It does not enable a durable anchor capability in either engine and does not complete the editor task.

## Behavior covered by the source and original controls

`PinkhaSemanticTextAnchor` stores a versioned UUID and exact Space/document identity in a reserved native link URI. The association payload stores that URI and version in its existing custom metadata. It does not persist a selected range, quote search result, or historical block ID as the durable locator. Current UTF-16 ranges are transient projections of current native markup.

`PinkhaSemanticText` provides the common capture and edit rules. Capture rejects existing links and partial grapheme selections, including the tested Hebrew niqqud and emoji cases. Ordinary edits before, inside, and after the selection preserve or remove the marker according to explicit boundaries. Split/merge retains the same marker across current block fragments. Replacement, deletion, inverse edits, and plain clipboard export have explicit behavior; inverse edits require exact current text/marks. Marker parsing rejects future, malformed, foreign, and redirected identities. Resolution requires the complete current document and returns missing or ambiguous when the marker cannot be uniquely resolved under its fragment rules.

The Any inline Markdown codec reads and writes the marker in the actual inline field representation. Its six controls cover styled Hebrew, decoding a newly encoded field, edits, formatting, deletion and exact inverse bytes, unsupported reserved syntax, existing links, emoji/niqqud, and literal paste escaping. Those tests exercise the codec in memory. A test name referring to reopening a persisted native field means reparsing the encoded field bytes; no Any native engine was started by these controls.

Semantic association metadata retains the existing association item ID and unknown metadata. Distinct phrase markers and whole-document associations have distinct collection identities. An item with no semantic metadata retains its previous storage key byte for byte. Invalid semantic metadata cannot silently deduplicate with a legacy whole-document association.

## Original execution and retained evidence

| Scope | Original passed methods | Evidence |
| --- | ---: | --- |
| Shared semantic text/identity model | 10 | `result.json`, `swift-test.log` |
| Any inline marker codec | 6 | `any-codec-result.json`, `any-codec-test.log` |
| Semantic association payload/identity | 4 | `association-result.json`, `association-test.log` |

The original executions used Swift 6.3.3 on `x86_64-unknown-windows-msvc`. They have zero failures and zero skipped methods. The logs contain an XCTest compatibility runner reporting zero XCTest cases; the 20 actual methods are the separately recorded Swift Testing methods. They are not Apple XCTest execution.

All six original receipt/log files are copied byte for byte, including their original line endings. Their fixed SHA-256 values are checked by `Tools/PinkhaSemanticAnchor/verify_portable.py`. The verifier requires the exact named method sets, original success counts, original commands, unchanged source-before/source-after maps, and the current bytes of the ten staged source/dependency files. Running it reads evidence; it does not rerun the 20 tests.

The first core and codec receipts directly hash their respective source/test pairs. The later association receipt records the complete ten-file staged source closure, including the unchanged core and codec files. `observed-final-harness-Package.swift` is the final harness read back from the original temporary workspace; an original before/after Package.swift hash was not recorded. It is supplied for inspection and is not promoted into a historical harness-hash guarantee.

The association controls use the real `TorahInspectorCore/Models.swift` at revision `511454e49450cb2581ddf77f644146ff3e30dbef`, with Git blob and SHA-256 checked against `dependency/SOURCE.json`. They do not substitute a model stub. The other two unchanged local dependencies are `TorahAssociationModels.swift` and `TorahAssociationRepository.swift`.

`canonical-git-baselines.json` records the two modified source baselines and the two unchanged dependencies at shared commit `58b9de8f7a26d798e18e301ad1ed8be14f2a8c14`. Canonical bytes were verified against their reported Git blob IDs before recording the hashes. The bundle does not include a replacement for either unchanged dependency.

The retained result is in `RETAINED_CONTROLS.json`. `VERIFIER_AUDIT.json` records two new negative checks rejecting modified executed source and a modified original log. No Swift methods were rerun for this packaging audit.

To verify after integrating the seven source changes:

```sh
python -B Tools/PinkhaSemanticAnchor/verify_portable.py \
  --control . --output /tmp/pinkha-semantic-portable-retained.json
```

## Explicit integration boundary

The materialization protocol, mounted editor adapters, Any native conditional write/readback, Heart typed CAS candidate, generated wire, and Apple acceptance are separate work. They are not included in this core/codec manifest. Full PinkhaKit/PinkhaAnyHost packages were not compiled by these minimal component harnesses.

The resolver accepts matching marker fragments spanning adjacent block boundaries as a split anchor. An uncontrolled whole-block copy could clone that marker into an adjacent block and resemble a legitimate split. The pure plain-text clipboard method and inline literal-paste control do not establish the actual whole-block clipboard policy. The mounted copy/cut/paste paths must remove or remap copied internal identities while preserving cut/undo behavior before a durable capability can be enabled. Ambiguous cases must remain explicit.

Further acceptance must exercise actual conditional native writes, reopen and current authority/session fences in both engines; native split/merge, formatting, cut/copy/paste, undo/redo and RTL editing; complete current-document resolution; and stale/concurrent edit rejection. Any's existing version CAS must remain intact. Heart's durable write capability remains unavailable until its additive current text/all-marks CAS and actual native/wire/Apple behavior are qualified. Legacy offset and whole-object association behavior remains available.

The feature's native and mounted acceptance statuses remain `NOT_RUN`; EDITOR-02 is not complete.
