# Actual iOS source typecheck — 25 November 2026

The original Apple Swift frontend passed source checkpoint `86d738c662c332cec370cee6a09dd434808dbeb9` in job `job_7c9c089b9779`.

The invocation typechecked all 31 changed Swift files as primary inputs within the complete 2,281-file original module context, targeting `arm64-apple-ios27.0-simulator`. Every Git-managed input was matched to the checkpoint's actual Git blob. The one original generated asset source was matched to its retained successful producer receipt. The original dependency modules, macro executables, compiler options and module maps were reused without writing to the previously qualified SDK products. All source bytes remained unchanged across this invocation.

This is a source/API typing result. It does not claim a newly linked framework, public symbol-graph qualification, a native lifecycle execution, ordinary app/UI acceptance, a 5,000-native-note run or network delivery. The source contract contains 237 public requirements and 22 Debug SPI requirements; their new binary qualification belongs to the SDK release lane.

## Actual failure and correction

The retained invocation of `6168d8b4ee875b58f534eddec190d072cfb3a5ac` (`job_b0dbf775cca1`) failed in the lifecycle response decoder. The original module has a distinct `Decoder` type, so the custom `Decodable` initializer did not implement the standard protocol. The one-line correction explicitly uses `Swift.Decoder`; the public contract is unchanged. The failed result and original compiler diagnostics are retained beside the successful result, with their exact input manifests and commands.

## Evidence

`RESULT.json` identifies the source, target, jobs and complete evidence archive SHA-256. `COMPLETE_EVIDENCE.tar.gz` contains both actual compiler outcomes, commands, source file lists, per-input SHA-256 manifests, admission budgets, memory observations and unmodified stdout/stderr. It also includes the final externally pinned Git-source manifest and the exact bounded controller.

The successful invocation took 4.166 seconds with 469,581,824 bytes peak child RSS; the owned candidate occupied 2,127,183 bytes and reused the existing owned compatible module cache without growth. Native/runtime acceptance remains separate.
