# Native whole source continuation

Status: initial run 45450648145/1 failed at compile before any method ran. This continuation fixes the fixture-only enum spelling to the actual generated RelationFormat_shorttext; selected methods and assertions are unchanged. The corrected methods have not yet run.

Immutable Heart candidate: 67381c31503518b4c0995b29aecd57c89799c6e8
Base: 256d3fd6cb4c2b0df67f67e01edfd8f9b76726f4, after the separately admitted original C4 context delta.
The source delta retains the accepted inventory and selected-object additions, adds the closed whole-source capture, and changes exactly one existing private resolver field. New(spaceindex.Store) is unchanged. Original C4 and inventory tests/receipts remain unchanged; this controller never reruns those methods.

Route: native-whole-source-arm64 (one inline central job).
Host: ubuntu-24.04-arm, same original qualified compiler/source carrier secrets, no network inside the compile/test containers, 1 CPU / 4 GiB.
Command: python3 Tools/AnyEngineValidation/native_whole_source/run_native.py
Required environment: real GITHUB_ACTIONS/GITHUB_SHA/GITHUB_RUN_ID/GITHUB_RUN_ATTEMPT, EXPECTED_SOURCE_SHA, RUNNER_TEMP, PINKHA_NATIVE_COMPILER_URL, PINKHA_NATIVE_SOURCE_URL.
Public upload: RUNNER_TEMP/pinkha-native-whole-source/public; original encrypted private artifacts and result are retained by the unchanged C4 custody helper.
Success status: THREE_NATIVE_WHOLE_SOURCE_METHODS_PASS.

Selected methods:
- TestLoadedAccountWholeSourceBindsLocalPayloadAndMetadata
- TestLoadedAccountWholeSourceRefusesChangedCheckpointAndAuthority
- TestLoadedAccountCapturedResolverAccountsForMissingSchemas

The new source bundle binds raw current snapshots and every admitted local file variant/metadata to the actual source object identity, original native rows, account/session/ACL and a final unchanged checkpoint. Missing local leaves, unsupported roots/store-backed state, unresolved schema/reference identities and raw history semantic gaps remain explicit. It does not claim whole-Space migration or destination writes. Remote prefetch is outside the frozen capture and is not exercised by these LocalOnly fixture methods.

Original failure: https://github.com/davidpovarsky/anytype-swift/actions/runs/45450648145 at app 84a2aae731b04a2a944fb9ebd8463f6ccfe36636 and Heart b8ecd2a04376889077d51b8df459956a27ceafbe. Artifact 14947749604 retains result plus encrypted original build log; the original has zero executed methods. The exact compiler diagnostic was core/application/loaded_space_witness_test.go:377:121 undefined model.RelationFormat_text. RelationFormat_shorttext is generated enum value 1; its collision with file (5) retains the original ambiguity-refusal assertion.
