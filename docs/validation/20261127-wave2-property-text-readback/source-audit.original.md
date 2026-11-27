# Properties Unicode representation audit

**A concrete Host receipt-verification gap exists in immutable source `af63f6209c38bddf6ed851f0b894e2f627a671af` (tree `c3c3f46ec9241b6d446000bbdb3f5f89826b6a0c`).** This is a source-derived finding, not an observed Native/UI failure. No compiler, tests, Native operations, Oracle or Mac calls were made for this audit.

## Actual path

The current Properties value form does not compare edited text with its original value before saving. `AnyNativePropertyValueCodec` passes string values through without trimming or normalization. `prepareSetValue` retains the supplied value in its one-property patch, and `apply` sends the authorized, fenced POST. No local canonical-equality no-op suppression was found in this path.

The gap is later: `receipt` calls `nativeValueMatches`, which reaches `nativeEquivalent`. Its first `lhs == rhs` uses synthesized `AnyJSON` equality and thus Swift String canonical equivalence. Given an otherwise matching accepted fence, a readback with a different Unicode scalar/UTF-8 representation can be marked `verifiedCurrent`. Matching definitions then permit an Undo. The presentation accepts this receipt, clears its pending/review state, reloads the document and returns success to the form. That reload does not independently compare the requested property bytes.

The finding applies to direct string properties such as `any/name` and the dynamically mapped imported `sourceURL` row. It also identifies why a later correction must consider composite values and raw object-key representations: whole-container synthesized equality can skip recursive comparison, and the existing key-set comparison is canonical too.

## Intended value contract

The current caller/codec retains raw string values. `AnyHostCanonical` uses length-framed UTF-8 bytes for string intent/revision identity. The receipt comparator explicitly permits two native representation conversions: integral numeric encoding, and RFC3339 timezone/fraction representations of the same millisecond. Null requests represent removal and match an absent property. No Unicode normalization allowance for ordinary strings was found in the inspected code or tests.

The separate Bookmark URL-open projection parses a URL for a user action; it does not rewrite the stored Properties edit. The sourceURL role is resolved from exact native owner/property metadata, with a synced string definition and URL format.

The official [Swift String and Character documentation](https://raw.githubusercontent.com/swiftlang/swift-book/main/TSPL.docc/LanguageGuide/StringsAndCharacters.md) confirms canonical String equality and access to raw UTF-8 code units. Literal NFC/NFD, Hebrew combining-order and URL examples are recorded in `audit.json`; they were not executed as Swift tests.

## Existing coverage and next boundary

The inspected original `NativePropertyStoreTests` covers patch/inverse custody, kind checks, numeric equivalence and date equivalence. `NativePropertyFenceTests` covers accepted sequence, target/epoch identity, numeric value mismatch and Undo binding. These sources provide an existing `prepareSetValue` / `materialize` / `acceptedFence` / `receipt` test route; no new production test seam is needed.

The root authorized a separate local source/test successor after this report. That candidate will use a typed property comparator, retain the existing null/numeric/date rules, compare string values and object keys by UTF-8, and keep the global `AnyJSON` conformance unchanged. Any effect on the existing depth-32 ceiling must be explicit. It is separate from this immutable audit and cannot inherit runtime acceptance from earlier editor-text tests.

## Evidence

- `source-manifest.json`: all nine primary source bodies independently Git-blob verified against the exact immutable ref.
- `audit.json`: finding `PROPERTY-UTF8-READBACK-01`, exact call sites, documented equivalences, preconditions and limitations.
- `primary/`: original connector source responses and the resolved immutable commit.
- `swift-equality-semantics.json`: concise official-source attribution; no full documentation copy.
- The failed short-ref lookup is retained separately; the full commit and tree were subsequently resolved and verified.

No claim is made that the Native engine actually returned the wrong representation, that data loss was observed, or that the source-only regression is accepted on Apple.
