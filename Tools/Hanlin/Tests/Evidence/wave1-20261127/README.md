# Original Hanlin component acceptance ? 2026-11-27

## Product sources

- Hanlin: 9bcdecfc829d446a773a78b249e894e204b1bcaa.
- Same-owner Anytype integration: ae86bf287a9df4fee32ea4c1a76c6eb78cadbb01.
- Focused tests: 66bcfeaa0bd38eb3071605711b3e1e2f2914a243.
- Strict original Logging ownership observer: 4b06226c8cca4c3ae22e705a2cb486816259f5b6.
- The existing AnytypeOriginalEditor owns AI_Hanlin. Existing Logger owns Logging. OriginalEditorSharedFirebase retains Firebase/Google.

## Actual component execution

Seven unique Swift Testing cases passed on an actual arm64 iOS Simulator using the original AI_Hanlin component. This is explicitly two successful subsets, not a single seven-case successful run:

1. Run 1 could not run tests because the fixture omitted try for a throwing descriptor revision initializer. Native exit 65.
2. Run 2 executed all seven cases: two passed and five failed. The five failures all preceded dispatch because the fixture supplied uppercase UUIDs to the original lowercase-only invocation ID contract. Native exit 65.
3. The fixture-only correction uses UUID().uuidString.lowercased(). Run 3 selected exactly the five failed cases, all five passed, native exit 0. The two earlier passing cases do not use that helper and their bodies and dependencies are unchanged.

The exact commands, tests, outcomes, prior failures, source snapshots and unmodified xcresult bundles are retained. No product source changed between runs. COMPONENT_SOURCE_OBSERVATION.json independently verifies all 159 selected original Swift files and 958 tracked nested-package files against the immutable producer. The selected package manifest and resolved 29-package closure are recorded in the receipt.

The cases exercise per-facade validation over the one original process runtime, actual original search over supplied Core metadata, raw-schema and forged-projection rejection before dispatch, actual original result-store history, duplicate-alias recovery, original pending-consent cancellation before script dispatch, and owner changes/permanent revocation.

Core catalog entries and one in-memory Skill metadata entry are explicit fixtures. No fake MCP transport, model provider, script runtime, engine or dispatch loop is installed. These component controls do not claim an actual remote MCP execution, script execution, native host UI or real-provider Hanlin Live result.

## Original ownership observation

The retained original Release Simulator SDK75 archive was independently inspected; its Logger image defines 151 Logging symbols and its AnytypeOriginalEditor and OriginalEditorSharedFirebase images define none. This is an observation of the old qualified Release artifact, not a pass for the new candidate.

The strict observer 4b06226c requires Logging to remain exclusively in Logger and rejects duplicates, missing definitions and wrong owners. Its 11 synthetic policy controls passed. The new integrated candidate must still satisfy the native single-owner observer; no product-type change or duplicate-symbol relaxation is included here.

## Raw artifacts

Canonical copies are preserved under both:
- /Users/m1/builds/otzaria-wave1-hanlin-20261127
- /mnt/development/projects/evidence/otzaria-wave1-hanlin-20261127

Component archive:
hanlin-original-component-66bcfeaa-native-evidence.tar.gz
57,329,770 bytes
SHA256 cceea03bd993525dbb67bf87e4c67582063bde82852d3dd7a3cd5a825be83e0b

Component receipt:
SHA256 3d5fdcfa82245ff3b3d8386b10d3cf166eb427fc76150ca3c1b7583e4b279f24

Compact original Release Logging observation:
logging-75-release-inspection-evidence.tar.gz
2,553 bytes
SHA256 a6e7e2d8edd6ed53eaca8558ea9f72e4cf19d95ac7f0b37a500a87ce85cf2ffb

The original prepare_sdk.py --check revalidated every file of the frozen 5,162-file Dependencies/Hanlin snapshot after the tests. Marker before/after:
4fcb921d8a3e359ea1cc2ba4e5bb704b3e6b6bcc5daccd50c00d40fd5513329f.

## Integration gates

The root/integration agent owns the new full SDK configurations, original shared-owner and exported-module verification, native host UI, the four Guided Tours selectors, final MiniApps paired tests and real-provider Hanlin Live. This record adds component evidence only; pending gates remain open.
