# Bookmark6: only the two missing Swift Testing methods

**Source preparation only. No host, Swift, process, cache or publication action. No runtime window belongs to this continuation; W1 Type25 remains next.**

## Decision

Use the already-qualified **Integration test runner directly**, with:

```text
/mnt/development/projects/evidence/pinkha-wave2-bookmark6-20261127/build/out/Products/Debug-linux-aarch64/PinkhaAnyIntegrationTests-test-runner
  --testing-library swift-testing
  --no-parallel
  --filter (?:creationOverrideRejectsAnotherWorkspaceBeforeDispatch|creationOverrideAndDefaultCreatorShareTheExistingMutationQueue)(?:\(\))?$
```

This is one fixed invocation and no automatic retry. It cannot select the Host test product. The actual generated entrypoint sends this library choice to `Testing.__swiftPMEntryPoint`, and its XCTest branch is conditional on the different literal `xctest`. The exact two-name filter is the same supported argument that SwiftPM forwards to this entrypoint. The result reader requires exactly those two start/pass pairs, the original named suite and one positive two-test summary; it rejects XCTest, other methods, skipped/failed/parameterized events and empty-run acceptance.

| Route | Exact source support | Decision |
|---|---|---|
| Direct Integration runner | Actual generated body `ef1ea588…`, qualified runner/shared-library/link proof `ac38377d…`, original SwiftPM argument forwarding and Linux test environment | **Selected**; avoids package/manifest/build-system dispatch |
| `swift test --skip-build --test-product PinkhaAnyIntegrationTests --disable-xctest --enable-swift-testing` | Original `SharedOptions`, explicit library resolution, single-product selection and skip-build guard | Supported alternative, not implemented or dispatched |

The original reason that automatic Swift Testing dispatch was omitted remains unproven. This choice does not relabel that diagnosis.

## Actual product authority

The read-only completion `ac38377da08aac68629d2ae04f8d4878a52eb8b28ee3e1009700c810902302d7` qualified all nine compiler/link groups and 84 original plus four generated inputs. It retained the original six-method `FAIL`.

- Integration runner: **10,805,344 B**, SHA256 `c5334175861cc165de9751240d4532e2eea73d4ac850756074f7ffb150d91b34`.
- Integration test library: **21,171,736 B**, SHA256 `5eac396345bc469d9712ec7a776e10671652cc1366aa6f08b4269ff49f8f70ab`.
- Original failed receipt: `4441afb94ce64ef8656dd001ec040bee2cb69201eaddba16d2fc8e7a3d4fb556`.

The four observed XCTest passes remain separate accepted observations. This new receipt can report only the missing two Swift Testing methods. It will neither replay the four nor rewrite the original result. All old 27 Integration methods and old seven Host methods remain excluded.

## Environment and source custody

One additional bounded primary intake established Linux environment construction: `swiftlang/swift-package-manager`, exact `swift-6.4.3-RELEASE`, `Sources/Commands/Utilities/TestingSupport.swift`, Git blob `6132b8b7b7b2fb3a2c020ef8b02c45f8e1298875`, SHA256 `3996284a9b32d12f63a8869d9f25d5f30ff88c29bb659cd61e39e42e193d2513` (52,269 UTF-8 bytes). The full original response and the two finite directory listings are retained under `primary/`.

For Linux, that source adds the product parent to the library path and sets `NO_COLOR` for captured output. Package tools6.0 adds no default interop override. The direct invocation explicitly supplies the actual product directory plus the exact Swift runtime directory observed in the original link command, with a fresh continuation-local temporary directory. It refuses an unqualified preload or nonempty interop override. No claim is made that the full original inherited environment was recorded.

Before, after and at final retention, the controller checks all 90 immutable input bodies, the 85 Package/source copies, original ten artifacts, completion receipt, qualified compiler/link artifacts, and 102 Crypto originals/aliases/private copies. Current device/inode/mode/mtime and byte identities of fixed artifact paths must remain unchanged across this continuation. No product is copied or rebuilt, and no unknown runtime artifact hash is learned into the allowlist.

## Existing lifecycle and resource policy

The exact original `owned_process.py` SHA `58624c3f…` is retained and loaded only after its original custody check. Only the newly created `Popen` session may be observed or cleaned up. Original group2634766 remains a historical record and is never passed to a process helper.

Ten original functions are byte-identical: SHA/write/pin/source inventory, custody, allocation/resource/budget checks, private-directory creation and Crypto verification. The source inverse restores the full original3729 controller. The new entry, witness and result paths are explicit specializations; identical executed behavior is not claimed.

Original gates remain: ROOT2GiB and DEV512MiB live floors, 32MiB admission margin, 256MiB whole owned allocation cap including its 1MiB final-evidence reserve, 512MiB available memory, 300s owned-command deadline and 360s outer dispatch allowance. The fresh fixed output is `/mnt/development/projects/evidence/pinkha-wave2-bookmark6-20261127/continuation1`; existing output is never reused. First errors and original evidence remain retained through owned cleanup and final checks.

## Frozen preparation

`run_missing_two.py`: **34,063 bytes**, SHA256 `0e8fa19767222fef6f954bf4bfdb34e58a77986251e69cf461b29f7311f01627`.

`source-inverse.json` records the complete byte-preserving forward/reverse proof and all ten retained function hashes. `continuation-plan.json` binds the exact actual products, command, dependencies and scope. Preparation has used static AST parsing and source-byte comparisons only; no controller, parser, test or portable control was executed.
