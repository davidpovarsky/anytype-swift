# Original corrected Heart r15 artifact admission

Actual original GitHub producer [44943967103](https://github.com/davidpovarsky/anytype-swift/actions/runs/44943967103), attempt 1, source `4ee2d7fd9f8acd74f51cbb2236d08f55a93af08b`, passed the consumer's original-artifact gates on 2026-11-21.

The executed consumer source is commit `7eb2e8d6a02a8cfea2f14babca6cb241bf644358`. The read-only harness downloaded both original GitHub ZIPs, verified their API SHA-256 and byte size, checked the exact corrected patch/inventory and producer identity, compared original build-receipt bytes across both artifacts, and replayed the original native fixture log through the actual fixture qualifier. It did not install a framework or run a native test.

- Runtime artifact: `14722543676`; 265,568,046 bytes; SHA-256 `42fb82875edd0025e8731bb2d6323ebce71621d302b11b0e018f845b5881b915`.
- Proof artifact: `14722434042`; 4,708,422 bytes; SHA-256 `5d70073c5f593e3dc9c80df05bc6548106ce086a3b41ec7372b47859e9eb0996`.
- Exact composed r15 patch: `595f8142f00035da2fff4925c8fe125fa7cf36de9ae124b528a9d2130b2a9bf6`.
- Exact inventory: `a9c381a46a0003c34695f22232b57716096ec51b100bb8dae2a18b47148274d8`.
- Original runtime build receipt: `54ff0f28d82421689f5f5400b7df699e61ca80334eec7e01ac1cd2117b1ec1b5`.

The original producer's two affected native attachment methods and six parent/subtest records all passed. Their original log and qualifier receipt are retained verbatim here. The three original Apple slice receipts carry the complete derived + T5 lookup + attachment version marker. The source-composition object retains its earlier pre-build scope labels without rewriting historical evidence.

This is **ORIGINAL_ARTIFACT_SOURCE_PROOF_PASS_APPLE_RECHECK_NOT_RUN**. Fresh Apple architecture reinspection, app installation, actual app process mapping, simulator behavior, two-client compatibility, and full T5 acceptance are **not** proved by this verification. The retained app workflows must still install this exact runtime via `runtime_profile=r15-attachment-v1` and `heart_source_run_id=44943967103`, independently verify the framework, and bind the complete marker and provenance to their actual observed process.

The original unmodified r14/r15 autoattachment failure is not reclassified. No old runtime is relabeled corrected, and no existing attachment is deleted or migrated.

## Preserved inputs and reproduction

`verification-harness.py` is the exact executed source from the owned `build/verify_original_corrected_runtime.py` path. To reproduce in a fresh checkout of the consumer commit, copy it back to that build path and run it using Python 3.12 with authenticated GitHub CLI. Its fixed work directory must not already exist. The harness does not modify application installation or source. The large original ZIP/tar archives remain GitHub artifacts, not repository blobs.

`verification-source-sha256.json` records the LF-normalized hashes of the exact consumer helper sources and the unmodified harness. `execution.json` records the original SentinelX command result, including exit code 0. No unchanged native fixtures or original 48/250 regression suite were rerun.
