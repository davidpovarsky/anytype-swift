# Original protobuf import assignment observations

This isolated source packet adds an opt-in historical observation of the original protobuf importer's ID assignments. It preserves original import behavior and enables no production caller, RPC, durable mapping or ACK. The implementation and its remaining limits are described in [IMPLEMENTATION.md](IMPLEMENTATION.md).

## Verified milestone

The six original-source changes received independent review. Fifty new leaf controls compiled and passed once on actual Go 1.25.6, using the actual observation/response/drain source with explicitly declared dependency fixtures. The original worker pool itself executes in the unit controls, so an outstanding cancelled worker and a successfully drained result channel remain distinguishable. No earlier suite was replayed. This is a unit result, not native import acceptance.

The raw result is [evidence/controls-v1/RESULT.json](evidence/controls-v1/RESULT.json), SHA256 `cdd51f4581c2d78bacc072cf81956b51f94a8370c3e1d57f22e95ee2fd8d1cfb`. [INPUT_READBACK.json](evidence/controls-v1/INPUT_READBACK.json) records the exact retained 15-file compilation closure; [INTAKE_VERIFICATION.json](evidence/controls-v1/INTAKE_VERIFICATION.json) reconciles it with all logs and current frozen source. Supporting packages with no test files are not counted as skipped test cases; the corrected post-download check is recorded without replaying tests.

## Correct integration source

Use **[composition/r14/native](composition/r14/native)** for the actual r14 native build. The original r14 patch also modifies `processor.go`; copying the earlier d984-only candidate would erase its existing Torah remapping step. The composed source retains that step and only marks assignment completion after it succeeds. Its processor SHA256 is `4588c5b5f596a8a3db0454270f6ddad467d9ab775d8a491d06490fda657968a1`.

[COMPOSITION_VERIFICATION.json](composition/r14/COMPOSITION_VERIFICATION.json) proves that the exact formatted r14 additions are retained and that removing them restores the independently reviewed hook candidate byte for byte. All five other source files and every actually compiled unit fragment are unchanged. The historical result remains tied to its original full-file metadata and is reused only for that identical compilation closure.

[install_native_sources.py](install_native_sources.py) checks all six source hashes and all four existing preimages before any reversible source write. It accepts only the exact original d984 files and the exact raw or Go-formatted r14 processor preimage. It rejects unknown native changes. [ORIGINAL_MODULE_GATE.md](ORIGINAL_MODULE_GATE.md) defines the next full-original compilation gate, which has not been dispatched by this packet.

## Source inventory

| Path | Change |
|---|---|
| `common/types.go` | Bounded copied source records, separate generated IDs, and explicit JSON exclusion for diagnostic fields. |
| `pb/converter.go` | Captures archived IDs before normalization and the actual returned converter ID, including selected/filtered origin facts. |
| `processor.go` | Captures actual assignment/key locals, records original successful drains, and retains the existing r14 remapper in the integration afterimage. |
| `types.go` | Internal opt-in flag and copied observation accessors with private backing state. |
| `mapping_observation.go` | Typed domains, collision/coverage refusal, copy independence and explicit non-injective destination reporting. |
| `mapping_observation_processor.go` | Conservative final eligibility and diagnostic-only reset for sequential processor reuse. |

All paths above are relative to `core/block/import`. Exact primary source files are retained under `original`, with their original Git blobs in the manifest. [PROPOSAL.md](PROPOSAL.md) preserves the source audit that led to this change. [audit/PEER_REVIEW.json](audit/PEER_REVIEW.json) records the independent source review and its limits.

The full original module has not yet compiled with this addition, and no genuine native import has used it. Account/attempt/source-archive binding, failure-worker drain, converter/provider concurrency, background file remapping, whole native semantic readback and the closed durable mapping consumer remain open dependencies. These diagnostic rows do not satisfy any of those gates.
