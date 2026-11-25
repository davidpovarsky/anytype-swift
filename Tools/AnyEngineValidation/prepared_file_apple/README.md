# Full-tier file Apple acceptance

This lane builds a separate native candidate from the exact Go commits in native-source.json, then selects a separate runtime identity: v0.5.0-pinkha.prepared.file.1. The retained native UI artifacts keep their existing identity and source pins.

The producer runs only on the dedicated ARM64 Mac with verified Go 1.27.4 and the actual Xcode iOS SDKs. The unmodified upstream scripts/build-xcframework.sh creates both device and simulator slices. The producer verifies the complete tracked source census before and after building, preserves its command logs, and records per-member archive hashes. A built artifact reports zero tests until a consumer executes it.

The consumer installs the source-bound artifact into a fresh isolated control checkout and selects PINKHA_ANY_NATIVE_ARTIFACT=verified-prepared-file-v1. One actual XCTest uses the embedded C runtime, managed authorization, ordinary native owner objects, and the production AnyNativePreparedFileMigration client. It stages 4,096-byte and 2,097,152-byte files, reopens the native account, commits their original signed identities, reads all bytes through ordinary native HTTP, repeats commit, and reopens again. A known prepare is reconciled even when the original input URL is absent.

Actual xcresult counts, selected test identity, destination UDID, compiled product hashes and bounded JSON observations are checked separately. The proof distinguishes local content completion from remote durability. It does not claim an OS process crash, injected HTTP acknowledgement loss, network synchronization or whole-Space completion; the independent Linux native process-kill result remains separately recorded.

A real local execution UUID identifies each producer and consumer. No GitHub run identity is fabricated. The controller refuses GitHub identity variables during a local run.

## Commands

Run after the shared Mac queue owner grants the heavy build slot. Use fresh task-specific paths for sources, evidence, native output and consumer work. Preserve failed attempts and completed artifacts.

Producer:
python3 -B Tools/AnyEngineValidation/prepared_file_apple/native_artifact.py --control CONTROL --expected-app-sha EXACT_SHA --execution-uuid UUID --any-root ANY_CHECKOUT --artifacts ARTIFACT_DIRECTORY --evidence PRODUCER_EVIDENCE --go-root /Users/m1/toolchains/anytapy-go1.27.4/go --go-cache /Users/m1/caches/anytapy-go1.27.4-build --module-cache /Users/m1/caches/anytapy-go-mod

Consumer:
python3 -B Tools/AnyEngineValidation/prepared_file_apple/run_host.py --control CONTROL --expected-app-sha EXACT_SHA --execution-uuid UUID --artifact ARTIFACT_DIRECTORY --native-producer-commit PRODUCER_SHA --work FRESH_WORK --evidence CONSUMER_EVIDENCE

Native commits are Any4e91d6327c298a0b0218b0a5125d9fc91cabd29a and SDK ccb0339d8640a1c890ddf6e224a839d702ec6a3c. The SDK checkout belongs at ANY_CHECKOUT/.runtime-artifacts/sdk-source. The full patches reproduce those commits' exact trees from the original upstream bases.

## Current qualification

Before the first Mac execution, source replay, the complete native source census, Python 3.9 syntax, selected XCTest source digest and Swift parsing were checked. These preparation checks do not count as an Apple build or an executed XCTest. The producer and consumer receipts supply the actual execution status.
