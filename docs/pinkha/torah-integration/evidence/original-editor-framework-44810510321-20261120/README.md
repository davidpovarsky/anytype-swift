# Actual framework v4 source-control failure

Run 44810510321, attempt 1, failed on immutable source 962d050eb36b2511616c771b08d92a78b64d2349 (tree a11f06d5f4fdf0ad94e4e8e1d2914c0b480d3cb6). This packet preserves the complete original artifact, canonical run/job/artifact metadata, full job log and all 25 source inputs authenticated against that exact Git source. The activation commit adds only Root review documentation to author head f349d991c20a610038ea3e36be8502b4d4d82551.

## Actual result

The Apple runner executed 96 Python controls: 93 passed, two failed, and one errored. Both mutation controls failed with `ValueError not raised`; the raw compiler-source fixture errored with `Actual framework source list is not the complete original source closure`. The final source-control command exited 1. Source admission itself was successful and did not confer runtime credit.

The failed methods are `test_known_input_changed_during_copy_cannot_publish_success`, `test_changed_materialized_output_cannot_publish_success`, and `test_original_packager_retains_all_four_exact_raw_proofs_as_text`. All original 54 controls passed; this is not a successful 96-control gate.

SDK preparation, verified Heart installation, Simulator creation, Swift compilation, framework build, symbol graph, external consumer compilation and runtime were skipped. No owned simulator existed to clean up. The source-only workflow emitted its original before observation; it did not emit a source-after observation, and none is reconstructed here. Editable mount remains not exposed.

## Preserved evidence

The exact 27,990-byte outer artifact has SHA256 717e082dc604f1f65834efa7997bcccf80f05afa2544720fb62d50ee59807829. Its one nested archive contains all four original files; every ZIP CRC was checked. `canonical-api-and-log.zip` retains seven safe original metadata/log records. `canonical-source-inputs.zip` contains all 25 genuine source files matching the runtime observation and canonical Git blob IDs. Temporary signed download URLs are excluded.

`VERIFY_PACKET.py` performs read-only byte, CRC, source, provenance, exact failure and scope checks. It executes no Python tests, Swift tools or Apple runtime. `REPLAY.json` records that verification, not a new execution of the failed workflow. The actual v4 failure is retained independently of the next candidate path-fixture correction.
