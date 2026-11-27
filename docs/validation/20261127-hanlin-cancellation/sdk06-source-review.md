# SDK06 source and retained ABI review

This review is separate from whole-app acceptance. Product integration at the
time of review consumed original Hanlin `38528941720d9b4f2da8dce7afbc788c2e554a0c`.
Its cancellation proof is recorded in `eof-drain-reviewed.json`. No companion,
TorahInspectorKit, Collections, or native engine pin is changed by this review.

## Collections and the original merge proposal

The current Xcode project declares exact swift-collections **1.3.0**. Its
Package.resolved records `7b847a3b7008b2dc2f47ca3110d8c782fb2e5c7e`, which is also
the resolved library in original Anytype branch
`codex/anytype-original-sdk-collections13-20261125`.

The merge-plan identifier `8ae85a6490c4fb763fcd01d5f93345f7e071db92` is an Anytype
tooling commit, not a Collections library revision. It changes only execution
owner classification in `Tools/OriginalEditor/prepare_local_execution.py`.
The current app already has the proposed library version. The standalone Hanlin
module has no separate Collections lock entry.

Main and Hanlin module locks agree on swift-ai-sdk
`abf0921c6e89e6521cc2b510ff11016b45a0ef08` and TorahInspectorKit
`9058b489e9acc271b4f8ef69e2ed24648f93b4ed`. This is a declaration/lock audit;
qualification of the final resolved app graph remains part of the shared build.

## Original TorahInspectorKit branches

The actual `codex/chatgpt-torah-explicit-close-20261125` head is 9058b489. The
complete remote branch inventory contained 18 branches. The ten relevant code
branches were compared against that exact revision:

| Branch purpose | Original head | Relationship to 9058 |
| --- | --- | --- |
| Common Anytype/Otzaria SDK | `23db0f84e88d9ee9c7053c49de86903fc7bb5785` | Ancestor; 2 commits behind |
| Common SDK original receipt | `1ea2aba49ff69af07a8acca94da946f1f8cfc613` | Ancestor; 1 behind |
| Related access | `511454e49450cb2581ddf77f644146ff3e30dbef` | Ancestor; 10 behind |
| T5 cancellation | `158acb295f832e96907cdadc813a1c2a4bb6a03c` | Ancestor; 11 behind |
| Editor UI | `07bdf7ca3f3318d729a855c0c75137773f16d0bf` | Ancestor; 14 behind |
| Native T5 UI | `4e59e909dd22685bb46f9396bc57e5f8c627d773` | Ancestor; 12 behind |
| T5 UI | `356c6af25d81bb6503ee3fa13aa09a48be386c8b` | Ancestor; 15 behind |
| General UI | `63955b388b0084e228448a9ba738a27adfe2e775` | One unique AGENTS.md/CLAUDE.md authorization-doc commit; no unique product change |
| Original Wave 1 proposal | `c3fbb6c8173858b26fc5b4ce8496ee09fef2b9f9` | Ancestor; 19 behind |
| Faithful native chrome | `19d1b35397af4f10ae70cfb3f444c9de87383b53` | Ancestor; 39 behind |

No additional consumer-required Kit source update was found in these branches.
Wave 2 retains ownership of subsequent Kit changes and acceptance.

## Retained native8ac ABI evidence

`sdk06-native8ac-abi-review.json` records the exact original simulator/device
qualification commands and receipts, and the actual retained header/modulemap
and architecture inspection. Both slices use one Go runtime and have identical
six public Objective-C headers and module maps. Original generated Swift entry
typechecks completed with exit 0 for arm64 iOS 27 simulator and device targets.
The source manifest is
`8ac407e75a4bfb42c359a2f72b3822c44990caedf2351d00d78315de5c96a04b`.

This establishes the scope of reusable native8ac interface evidence. It does not
qualify a new native cutover overlay, physical-device execution, final app
integration, Apple Distribution, or TestFlight. New coherent native source must
produce and qualify its own framework identity.

## Original companion staging case failure

The original a86 staging controller failed before any build/test/boot because it
indexed `before[name]` using canonical `docs/...` names while its APFS inventory
contained `Docs/...`. Its original stage1 FAIL is retained. All 7,693 tracked
identities match through 3,424 unambiguous case aliases. No casing collision or
source-byte mismatch was found.

`Tools/Hanlin/companion_source_inventory.py` fixes only this lookup boundary.
It returns a canonical-to-observed mapping, rejects ambiguous canonical or
observed aliases, and retains the existing missing-file, file-kind and exact-hash
guards. A staging caller uses `matches[name]` to look up the inventory row; it
does not rename files or lower-case a dictionary destructively. Three focused
Python controls passed for the real Docs/docs shape and rejection cases.

The same helper was used for a fresh readback of all 7,693 original files
(192,612,433 bytes), including unchanged bytes/modes and unchanged source HEAD.
`companion-case-gate-original-receipt.json` is the original receipt, SHA256
`abe4ad3a7664564610de39c3b9ae5bde95da6e57248b0775b43f9f9a4c869c0f`.
Full fresh inventory remains on the Mac under
`/Users/m1/builds/hanlin-wave3-cancellation-0a24e2c13b9b/companion-case-gate-20261127`.
This verification started **zero builds, tests, or simulator boots**.

The old 9565 `derived` compiler cache is now absent. The old staging controller
must not be rerun with a claim of that cache's availability. A complete producer
based on canonical 385 needs its nine-file delta from original 9565, exact native
runtime preparation, an admitted compiler footprint, and its own actual native
bridge/companion acceptance. The current compiled producer86 is not relabeled.
The separate original759e producer has identical explicit-handler bridge/test
blobs but its r4 failed at link; its owner's r5 was waiting for capacity at the
last observation. Neither is recorded here as a successful current producer.
