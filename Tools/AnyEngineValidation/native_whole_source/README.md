# Native whole source continuation

Status: source implemented; the three new methods have not yet run.

Immutable Heart candidate: b8ecd2a04376889077d51b8df459956a27ceafbe
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
