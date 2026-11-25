# Typed native file references and source file-property mapping

The native Any server uses `any://f/<spaceId>/<fileId>` for files. Source references must not be encoded with the ordinary object URI form. The public source definitions are Any548 `docs/19-links.md`, `docs/27-descriptors.md` (file/image shape has no built-in format slug), and `docs/03-api.md` (file-kind link/backlink API).

## Product behavior

- `AnyNativeFileReference` validates and preserves the exact canonical original-file identity. It rejects credential URLs, variant/query/fragment forms, escaped separators, traversal segments and object/foreign namespaces.
- The destination plan has an explicit `fileURI` encoding, valid only with a file slot. Both executor and independent content verifier resolve it using the bound destination Space and the native committed file ID. Ordinary object URIs now require object slots. Existing ordinary object plans and their serialized encodings remain unchanged.
- `AnyHeartNativeFileBinding` takes the one native-original variant from an independently byte-verified source bundle. It retains exact source/checkpoint/manifest identities, original name/MIME/payload path/size/hash, and emits an inert prepared file draft. Missing or ambiguous original variants cannot be guessed. All other variants still need separate coverage.
- Heart file-format properties map to native arrays of canonical file URIs through an explicit consumer-owned `pinkha-file` format and native `links` indexing. This uses the supported vendor descriptor mechanism; it does not mislabel a file as an object relation. The shared property consumer validates file values and cardinality.
- The value mapper preserves source order/duplicates and empty arrays; file references are deferred until real file commitment. It refuses missing, foreign-checkpoint or duplicate source bindings and unqualified file-type restrictions. Page previews can consume the bound files, while complete source/definition/admission gates remain unchanged.

## Actual qualification so far

**55 distinct controls passed**, zero product-test failures. The original reference/executor/verifier run passed18/18. The expanded mapper/property/page run passed37 methods and explicitly skipped4 methods needing native fixture/runtime inputs; the3 historical source-fixture methods were then supplied their exact SHA-bound originals and passed3/3 without rerunning the37 successes. The4th skipped method is the new real-native roundtrip and is still pending. The total55 deduplicates3 reference controls shared between the runs. Full logs/commands/source hashes and exact method census are retained. The original real156 fixture's producer failure remains a failure; its successful read-only controls do not grant current source authority.

The first reference-controller invocation timed out at30s during final compilation, before any test. Its complete log/source/timeout receipt is retained. No process remained. The correct300s background budget was used for the single continuation; native/product gates were not lowered.

## Pending native proof

`AnyDestinationNativeFileReferenceTests.testActualNativeFilePropertyLinksAndColdReadback` and the retained launcher exercise the actual mapper,5 prepared native operations,4097 original file bytes, exact stored native file URI, native forward/backlink index, new-process OS-offline reopen, and identical content/mapping/index readback. It compiled but has **not run yet**: Mac free disk measured2078248960B and then1490665472B, below the already-coordinated2GiB emergency floor. No new Go build or duplicate peer workload was started.

This checkpoint is component-qualified. It does not claim native file-property acceptance, cloud durability, mounted Apple UI acceptance or whole-Space migration. Previously qualified independent peer byte transfer/cold file reads remain separate exact-source evidence. Task C remains open for the full native schema/layout/context/history/source-authority closure.
