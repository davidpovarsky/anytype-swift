# Original Heart native schema defaults: verified focused completion

Source: `0896ae82864142e0b633278a8c5cb718ddf66e1e` (parent `8885a230159570a58ab2b8de4d09df632dcfc8f1`).
Actual run: https://github.com/davidpovarsky/anytype-swift/actions/runs/45046749798, push attempt 1, job `137282928691`, terminal success on 2026-11-22 at 17:11 UTC. This directory is evidence only; it does not trigger another test run.

## Measured result

Four new controls passed in the real original Heart model/Diff package, and the unchanged `MissingAttachmentUsesOneNativeApply` native child passed. Neither the twelve previously passed registration children nor the earlier observer/readback/strict cases was selected again. Their historical results and source assertions remain retained; this is not a claim that those twelve were rerun at the new head.

The two real Go 1.26.5 Darwin/arm64 compilations completed successfully (232.267 seconds and 69.014 seconds). The semantic command took 2.597 seconds; the native command took 6.290 seconds, with the selected native child reporting 1.87 seconds. All 21 owned command process groups drained and the disposable native fixture directory was removed.

The original native repair phase reports `creates=0 apply=true returned=true disposition=MATCHING_SCHEMA_OBSERVED error=<nil>`. The unchanged test requires exactly one successful Apply, no recreation of an existing definition, two preserved original views and complete native protobuf equality of all unrelated persisted fields after removing only the declared expected addition. The paired post-repair read independently shows one added hidden property ID, one relation link and one hidden column in each view; all other decoded persisted state is unchanged and persisted heads advance.

## Exact evidence

Original artifact `14764570821`, `Otzaria-Schema-Native-Defaults-45046749798-1`: 3,191,815 bytes; SHA256 `3ac1d224746d3a466cf978798fc238eaec0c556ffd5ed4ae2f3fcb894a07210a`; Git blob `4ad4d5e61752a4566568048e6cb730a3c50bb34c`.

`verify_native_defaults_artifact.py` independently checks the ZIP CRC, all 54 indexed payloads, 21 command stream hashes/drain facts, exact five selected leaves, the 21 composed product/test inputs, nineteen unchanged diagnostic inputs, seventeen unchanged original registration inputs, thirteen earlier baseline inputs, and all six complete raw state pairs. The complete dependency inventory and logs remain inside the original ZIP. `VERIFIED_SEMANTIC_RESULT.json` records the measured outcome.

The native runner observed the two compiled executable hashes before and after execution. Executable bytes are intentionally absent from this artifact, so their hashes have not been independently recomputed during intake. The original Go-declared dependency inventory is retained; generated cgo output and all Apple SDK headers are not claimed as a complete archive.

## Comparison boundary remains explicit

All six raw pairs continue to report `blocks_equal=false`: the live dataview contains a top-level empty Restrictions message (`1a00`) absent from strict persisted replay. Details and native heads match within each pair; every other block wire byte matches. None of these observations was rewritten or normalized.

The product comparison defaults only nil top-level Restrictions on deep comparison copies, then compares every represented native field. This matches the immutable original `Base.Diff` allocation behavior. Original generated Block/BlockRestrictions decoders discard unknown wire fields; this result does not claim preservation of unknown wire data or equality of the unequal raw bytes. All five representable restriction booleans and all other native block fields remain checked by the focused controls.

`SEMANTIC_INTAKE_LOCAL_CORRECTION.json` preserves the first local verifier failure: an empty Go nil slice serialized as JSON null, while the first Python verifier expected an empty list. Only the local evidence parser was corrected. Native code, selector, assertions and evidence bytes did not change.

Swift/RPC generation, generated source compilation, response/error/late-cancellation integration and selected-destination production composition remain separate downstream gates. Historical schema observation is not body, account lease, commit or ACK authority.
