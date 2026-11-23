# Canonical Hanlin native UI runtime acceptance — 23 November 2026

## Verified result

**PASS for the original selected native/UI journey and its actual same-process runtime observer.** GitHub [run 45219628237, attempt 1](https://github.com/davidpovarsky/anytype-swift/actions/runs/45219628237) completed successfully on consumer source **988f451959af1a40d1bc49bd6ed3798a730f5e37**. The installed canonical Hanlin SDK remained pinned to **32da9e314e22bbf22391fcf8902302acfbb281e2**.

The original fixture preparation passed once (7.902669 seconds). HanlinNativeAcceptanceUITests/testRealNativeConsentCreatePageAndAuthorityRevocation() passed once (111.144778 seconds). Both exported xcresult trees and summaries name the actual selected methods, with one pass, zero failures and zero skips each. The actual device was arm64 iPad Pro 13-inch (M5), iOS Simulator 27.0 build 24A434, UDID 1A82019A-CBE9-4BC7-B5CD-7981BC3DFCB1. The UI exported 18 original attachments. All 22 final native receipt checks are true.

The terminal runtime qualification is PASS_ACTUAL_UI_PROCESS_RUNTIME. It binds the original fixture 96EB24F5-7B31-4537-B6CF-A7327B642B69, session 34A4DA4A-B2F4-42DC-BD8A-751739B2C892, PID **51314**, original document/space/account authority and process start identity across the in-flight receipt, live mapping, final native result, and entry/final UI hierarchy. The observer performed **zero extra app launches**. PID and process start identity were unchanged after the actual UI method.

The observer first saw AWAIT_READ_CONSENT; its post-mapping receipt was still in flight at AWAIT_STALE_CONSENT_PRESENTATION. Mapping finished inside the final native receipt's real start/finish interval. The built, installed and post-UI executable manifests match: 112 code carriers, 812,515,712 bytes, manifest SHA256 18968c3defaa859a8aecfba08267086746de558b3b0b513b57e9a04d9f249cd3. The original Anytype.debug.dylib and Heart ProtobufMessages.framework were mapped into that process. Its 51 observed code carriers include all eight selected Hanlin framework products represented in the actual app mapping: AgentCore, ChatCore, ChatUI, HostContracts, PersistenceAdapters, PlatformContracts, PresentationKit and ScriptUI, together with the Pinkha Hanlin adapters. This does not assert execution of every function or all 112 carriers.

## Why this execution was needed

The previous [run 45181802668](https://github.com/davidpovarsky/anytype-swift/actions/runs/45181802668) remains **UI PASS / runtime observer FAIL**. Its original source-validation stage took 63.220238 seconds and exhausted the original 60-second mapping budget before live mapping could complete. No runtime pass is retroactively attached to that earlier UI.

Commit 988f4519 overlaps only the two independent, fresh built/installed code-carrier scans. Original hashing, alias/path checks, byte equality, failure propagation and joins remain intact. The original UI method, app implementation, SDK pin, fixture/session/PID/process-start checks, and observer budgets are unchanged. Controller proof is retained separately in ../20261123-canonical-source-scan-concurrency/: two new overlap/error controls, seven affected mapping controls, and two admission controls passed; 62 unaffected controls retain their earlier qualification.

In the current original execution, map_installed_source took **17.633098 seconds**, map_running_process 15.362763 seconds, and the interval from validated identity to completed mapping was **40.412059 seconds**, within the unchanged 60-second window. Stage times include their original work such as container lookup and file walks; this comparison is not a controlled benchmark.

The original route was dispatched exactly once:

    gh workflow run torah-inspector-ipados27.yml
      --repo davidpovarsky/anytype-swift
      --ref codex/chatgpt-wave15-canonical-hanlin-20261123
      -f route=wave15-acceptance
      -f runtime_profile=r15-attachment-authorized-current-read-v1
      -f source_run_id=45091223011
      -f acceptance_lane=hanlin-native
      -f acceptance_device=ipad
      -f acceptance_language=en

A sole bounded watcher finished with exit code 0 at 17:26:35 UTC. No retry or duplicate native execution was dispatched.

## Evidence and integrity

- Original GitHub artifact **14844786330**, Pinkha-UI27-hanlin-native-45219628237-1: 16,522,408 bytes; SHA256 d76ff5beab1dc2a04b8c1c2f47d3e3f368e9a6935489a81dd820c047c5cac616.
- Its original inner Pinkha-Native-Derived-Evidence.zip: 16,555,588 bytes; SHA256 7965fab6e168b252f833b9d5a59650365a44e07178e9b463effa6ee894829c98.
- The complete original was acquired once. ZIP CRC, member path/symlink constraints and all **185** extracted file byte lengths/SHA256 values were verified. inner-members.json records the complete member inventory.
- originals/ contains byte-preserved small original results, the SDK snapshot, runtime qualification, phase receipts, two real test summaries/trees, attachment manifest, final source-bound JSON attachment and both UI hierarchy boundaries.
- audit.json records the independent source/identity/timing checks and their scope. stage-diagnostics.json is a derived scalar view of the original observation diagnostics; its original file hash is retained. retained-files.json seals the curated originals and original acquisition/dispatch/final-run records.
- The complete acquired ZIPs and extracted originals remain on Oracle under build/sdk06-live-observer-native-988f4519/ in the isolated observer worktree. They are not replaced by the curated subset.

The UI's final JSON attachment is a re-encoding through the unchanged Receipt: Codable model. All 23 modeled fields equal the final file export. The exported file has two additional diagnostics (sceneObservations, nativeAuthorityStage) that this original UI model does not declare. These original files are therefore **not byte-equal**. The audit preserves both hashes, the exact two-field distinction and all field comparisons; it does not relabel them as identical bytes.

## Acceptance boundaries

**SDK06 and the complete host acceptance matrix remain open.** The separate shared-editor owner still owns SDK23 methods/32 argument cases and ACK7. This successful native consent/read/create/revoke/return UI journey does not substitute for those tests or authorize a concurrent replay of that lane.

The native journey deliberately has no configured AI provider. Provider/network behavior, physical devices, the other device/language/OS matrix, every app launch, selected-block UI authority and a fresh visual screenshot assessment are not newly qualified here. The original receipt fields full_sdk_acceptance=false, every_launch_verified=false, all_carriers_executed=false and full_bundle_equivalence=false remain unchanged.

This directory adds evidence only. No product/controller source, test selection, SDK pin or acceptance condition is changed by its documentation commit.
