# Frozen Properties value comparison successor

The isolated candidate changes one private function, `AnyNativePropertyStore.nativeEquivalent`, over exact `af63f6209c38bddf6ed851f0b894e2f627a671af`. The original full Store and Host test file remain under `source/`; the candidate remains local and uncompiled pending independent review.

## Production behavior

- Direct string pairs compare their UTF-8 code-unit sequences.
- Arrays recurse before any synthesized equality shortcut.
- Objects first compare their raw UTF-8 key sequences, sorted using the existing `AnyHostCanonical` ordering convention, then recurse through the values.
- The original integer/integral-Double comparison and `$date` native-millisecond conversion remain intact.
- Scalar fallback retains original equality, including signed zero, booleans and nested nulls. The outer native-unset rule still requires an absent property for a top-level null request.
- All other Store bytes, including authority, dispatch, native fences, exact definitions, Undo construction and creation routes, are unchanged. `AnyJSON` and Native APIs are unchanged.

## Explicit depth consequence

The original `depth <= 32` check is retained. Previously the whole-value synthesized-equality shortcut could accept a directly supplied identical over-depth container without traversing it. The candidate traverses ordinary containers, so such direct helper inputs now fail on an over-depth recursive visit. This does not exclude an otherwise admitted prepared/read value: the original `AnyHostCanonical.bytes` already validates the full value to the same limit in preparation and raw record materialization. The existing dedicated `$date` conversion remains at its original object node; the separate full-value depth guard still applies before receipt creation.

## Focused appended regression source

The complete original 15,598-byte `NativePropertyStoreTests.swift` prefix is preserved. A same-file extension adds four XCTest method declarations. These are four declared cases; internal fixture loops are not advertised as separately enumerated XCTest cases.

1. Direct Name NFC/NFD, Hebrew combining-order and a typed URL-value fixture use the real `prepareSetValue`, `acceptedFence`, `materialize` and `receipt` helpers. Each raw-different readback must return `nativeAcceptedButCurrentStateUnverified`, nil snapshot and nil Undo. Its exact counterpart must retain the original inverse bytes.
2. Nested array/object text and canonically equivalent but raw-different object keys exercise the same receipt path, with exact accepted fence and exact readback positive counterparts.
3. Five compatibility rows retain integer/Double equivalence in both directions, signed zero, RFC3339 timezone/fraction conversion, and absent-property unset. A stored null remains rejected as an unset result.
4. The changed standalone depth behavior is tied explicitly to the existing canonical-byte validation at depth 32/33, preparation and raw materialization.

The URL row is an explicitly named typed fixture. It is not a claim that native Bookmark metadata, URL opening, HTTP transport or Apple UI has run. No production fixture seam, HTTP server, process manager, new target or consumer profile is introduced.

## Review artifacts

`candidate-manifest.json` binds the frozen two-file tuple. `source-inverse.json` independently restores the original Store by reversing only the one function replacement and restores the original tests by removing the exact appended suffix. `source.patch` contains the full bounded source delta. Original numeric/date tests are retained byte-for-byte; no old suite was replayed.

Compiler/typecheck, test execution, compiled enumeration, Native reproduction and Apple acceptance are all **NOT_RUN**. This fixes the receipt's ability to certify a supplied raw-different value; the audit did not observe a Native fault or a suppressed property write.
