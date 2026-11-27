# Exact text in Properties readback receipts

**Source-reviewed correction; compilation and the four new test methods are NOT_RUN.**

Immutable parent: `af63f6209c38bddf6ed851f0b894e2f627a671af` (tree `c3c3f46ec9241b6d446000bbdb3f5f89826b6a0c`).
Owned branch: `codex/chatgpt-wave15-wave2-property-text-readback-20261127`.

## Problem and correction

The original Properties path preserves edited string bytes, but its later receipt comparator could certify canonically equivalent yet byte-different native readback. That could yield a verified snapshot and Undo despite the requested representation not being established. This is a demonstrated source path, not an observed Native or UI failure.

Only `AnyNativePropertyStore.nativeEquivalent` changes in production. String values compare UTF-8 code units; arrays recurse before synthesized equality; objects compare the complete raw UTF-8 key sequences and then recurse. The original integral-number equivalence, signed zero, RFC3339 millisecond date conversion and absent-property unset rules remain. The original depth-32 guard is explicit: directly supplied over-depth containers no longer bypass traversal; existing canonical preparation/materialization already rejects those values.

All other Store bytes, including creation, current authority, native request/fence checks, definitions and Undo construction, are preserved by the complete inverse. Global `AnyJSON`, Native APIs and the frozen App are unchanged.

## Exact source and test scope

| Existing path | New SHA-256 | Change |
| --- | --- | --- |
| `Modules/PinkhaAnyHost/Sources/PinkhaAnyHost/AnyNativePropertyStore.swift` | `c653fa8489f7f9dc7d835d57ab4ec27be0bc46e189a29d226524d81e70e6db48` | One private comparator replacement |
| `Modules/PinkhaAnyHost/Tests/PinkhaAnyHostTests/NativePropertyStoreTests.swift` | `7ff24aed7ce350c368d9d5d5f31439c3c87566353842013948912001082492ca` | Four appended XCTest declarations; exact original13-method/15,598-byte prefix |

The four new methods exercise direct Latin/Hebrew/typed-URL values, nested values and raw-different keys, existing native normalization/unset compatibility, and the existing canonical depth limit through actual preparation/fence/materialization/receipt helpers. Positive counterparts bind original inverse bytes; wrong raw values must yield no verified snapshot or Undo. Looped fixture rows are not additional XCTest cases, and the accepted-fence fixture is not an actual HTTP acknowledgement. `declared-selectors.json` gives the exact declarations; actual compiler inputs, enumeration and results remain absent.

## Evidence and reviews

`source-audit.original.md` and `audit.json` preserve the original finding. `candidate-review-notes.md` records the exact semantics and depth consequence. Root review `ecedb867…` and independent test review `264bf871…` found no concrete blocker in their stated source scopes. Historical audit/manifest status fields remain unchanged; these later reviews supply the source-review outcome without inventing execution.

All nine primary audit source bodies are retained once under `originals/`, with exact Git blobs in `source-manifest.json`. `source-inverse.json` restores both complete original modified files. The original HTTP422 short-ref lookup remains under `primary/`; the full immutable ref subsequently resolved successfully. That inspection failure is neither erased nor relabeled as a test failure.

## Integration boundaries

This packet changes only the two existing source/test paths plus this scoped evidence directory. It contains no component controller, new test target, Package/PBX edit, runtime adapter, App/source inventory adjustment, compiler or test result. W3 owns the exact later source admission and execution; do not silently broaden an existing whole-suite selection from13 to17 methods or rerun the original13 to claim these four.

The separate ordinary Bookmark proposal is still held and has only a documentation review publication (`78b1549c7a88bd4095b9abff90dd59364bd80ec6`). Its eventual actual-frame successor must compose this comparator function delta with its separate Store binding additions, using the true integrated preimage. This source correction does not enable Bookmark creation or claim its Native contract/bodyless/UI acceptance. Full import/export remains under the existing C/W3 provider-contract boundary.
