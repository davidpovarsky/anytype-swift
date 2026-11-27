# Native live render cache — exact text identity

**Reviewed source correction; compilation and live UI acceptance are NOT_RUN.**

## Concrete defect

`AnyNativeEditorController.configure` compared its cached source with Swift `String` equality. Canonically equivalent text can have different UTF-8 bytes and different UTF-16 offsets. A native/current refresh that keeps the same block, style, block type and content-size category can therefore skip the attributed renderer for the visible cell. The shared `PinkhaTextInputRenderPolicy` already compares exact UTF-8, but the outer cache predicate prevented that policy from being reached.

## One-predicate correction

The sole product edit changes the cached-source condition to:

```swift
cell.renderedSource?.utf8.elementsEqual(renderedSource.utf8) != true
```

A nil cache still requests initial rendering. Exact byte equality still skips the text render unless an existing style/type/category condition changes. Raw-different text now reaches the existing renderer. Its marked-input/pending-local-change behavior, applied-only cache update, focus, history, selection, observations and native authorization remain unchanged. The same UTF-8 comparison API is already used in the surrounding configure/composition code.

The exact inverse restores every byte of the parent source by replacing this one predicate. Parent: `d528e5413c72320c423ce9ccdbd4fbe423ca4a4a`; original source blob: `81eec84bc476ce7d0c4835ebee912e57b35717c6`; corrected source SHA256: `ec8f72a34e9823c7ba84ab8dbb013d9827c9302fc6143436de3ec8a3bfdf2f37`.

## Verification boundary

Independent source review checked the complete primary parent bytes, inverse and surrounding configure/render-policy behavior. No compiler, test, Native, Mac or Oracle call was made. There is no new authority seam, fixture setter, selector, Package/PBX change, source membership or Native contract change.

The existing three renderer methods call the renderer directly. The two Native25 ordinary typing/cold methods update local text/cache directly and reopen. Neither scope exercises this live same-cell cache gate; retained results from those methods cannot be credited as acceptance for this correction. The complete parent Native26 source remains unchanged. Interfaces is separately assessing a truthful full-controller regression fixture.

## Integration and remaining acceptance

Wave3 owns final integration, source-matched shared compilation and actual acceptance. Any external control pinning the complete previous `AnyNativeEditor.swift` must explicitly qualify this exact successor. No consumer or product gate is opened by this source publication.

The remaining targeted observation is a real live external/current refresh of the same visible cell using Latin NFC/NFD and Hebrew combining-mark reordering. It must check exact text bytes and UTF-16 effects, current block/anchor identity, and the original selection/focus behavior. Marked-input and pending-local-change preservation are separate obligations; ordinary typing does not establish them.

## Evidence

- `source-change-proof.json`: original finding and exact source hashes.
- `editor-independent-source-review.json`: independent source-only review.
- `exact-inverse.json`: one literal replacement and full-byte inverse.
- `handoff.json`: exact source, ownership and pending acceptance.
- `workflow-preflight.json`: current source/default workflows checked before creating an owned branch; no dispatch.
- `complete-merkle-retention.json` and `packet-manifest.json`: complete scoped tree and payload custody, without a compiler/source-gate execution claim.
