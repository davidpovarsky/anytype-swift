# G02: native Properties baseline and exact Word unlink readback

**Source reviewed, future integration only. Apple compilation and execution are pending.**

This addition supplies one hosted selector, `TorahWritingPropertiesReadbackTests/observeOriginalWritingProperties`, invoked once with phase `baseline` and once with phase `postflight`. The source is an exact append to the original `TorahNativeDerivedProductIntegrationTests.swift` at `8f2c11713fb8a40ae13444104723666ffef68afe`. All 84,286 original bytes, including every preparation and Type-preservation method, remain unchanged. This branch is not the current frozen App or a qualified runtime product.

The existing Type-preservation verifier uses a separately reserved subject. It cannot establish preservation for G02's three original writing Objects. This addition reads the actual `chiddush`, `article` and `research` IDs in the unchanged NativeDerived fixture, and explicitly rejects use of that reserved subject.

## What the reader establishes

The UI first selects a Source, Topic and Word and creates/selects one real ordinary Tag on each of the three writing Objects. The hosted baseline then reads the actual native values. The later UI cancels a changed search without changing its existing selection, removes the exact selected document Word and cold-reopens each Object. Hosted postflight compares the actual native state with its retained baseline.

Both native phases preserve full protobuf detail JSON, its byte hash, decoded fields, canonical association bytes and their hash, derived identities, the real Tag option Object, and the original Tag Property Object. They bind the original fixture, source/run/owned simulator provenance, live account ID, Space, three Object IDs, three Type IDs and names. Postflight requires identical container and middleware directory identities from baseline; relocation is not automatically accepted.

For each Object, postflight permits only these source-justified changes:

| Value | Required result |
| --- | --- |
| Canonical association payload | Exactly the baseline document-scoped Word record is absent. Every other record, unknown field and raw JSON value remains equal. |
| Word derived identity | The actual derived list is empty. Its raw protobuf JSON must be absent, null, or an empty array; a malformed scalar/object cannot become an empty success through a conversion fallback. |
| Native label map | Only the selected Word's canonical identity key is removed. Every other entry remains equal. |
| Native canonical digest | It equals SHA-256 of the actual canonical raw bytes in each phase. |
| Engine clocks | Only `lastModifiedDate`, `lastOpenedDate` and `lastUsedDate` may differ. Their original/current values remain in the full snapshots and must be absent, null, or finite nonnegative numbers. |

Source/Topic identities, readiness, projection version, state, other native fields, Tags, Links, Type and name remain equal. The original chiddush has an unrelated block-scoped `Exodus 3:2` record; the reader retains it and does not incorrectly require only three total canonical records. The original shared display formatter determines the English chip label from the actual decoded native item.

This is a Properties readback, not a proof of all native-store bytes, all document block contents, T5 full-Space index completeness, or physical-device behavior. The suffix does not call account creation/selection, bootstrap/provisioning, association writes or native property mutations. Normal App/native startup and `ObjectShow` can perform their ordinary engine work. The suffix itself writes only explicitly named test-evidence files.

## Original native source custody

The policy above was checked against the real Native8ac source archive, SHA-256 `c70592e4ae160cbb5cb8eda3cb1caed08f727476a5c9fac7c207593cd9315830`, 26,130,845 bytes, retained at:

`/mnt/development/projects/evidence/native-d-final-20261125/native-permission-20261126/native-source-8ac407e75a4b.tar.gz`

The six exact extracted members and hashes are retained with this evidence. `projection.go` rebuilds the label map from document-context records; `torahindex/index.go` derives the canonical digest and sorted identity lists; `smartblock/pinkha_torah.go` may reinsert null for an attached empty native Property. The later `legacy_cutover` overlay was not used to infer behavior of the Apple8ac product. The historical Heart Git pin alone does not contain this full exported composition.

## Required future stage sequence

After the unchanged original NativeDerived preparation, one finite controller must bind four actual stages in order:

1. UI selector `PinkhaTorahWordUnlinkAcceptanceUITests/testSeedOriginalWordUnlinkFixturesThroughProperties`; retain the `word-unlink-seed-complete` raw JSON attachment and its actual command/result/XCTest receipt.
2. Hosted selector `TorahWritingPropertiesReadbackTests/observeOriginalWritingProperties`, phase `baseline`; retain the full baseline and compact UI handoff.
3. UI selector `PinkhaTorahWordUnlinkAcceptanceUITests/testChangedQueryPickerCancelThenWordUnlinkAndColdReopenForAllWritingTypes`; retain the `word-unlink-unlink-complete` raw JSON attachment, actual command/result/XCTest receipt, all cold PID observations and visuals.
4. The same hosted selector, phase `postflight`; retain its actual native result and command/result/XCTest receipt.

Each stage needs its own original invocation and result custody. All stages share the same qualified source, App/native/SDK products, original owned disposable account/fixture, and simulator. They run sequentially, with the owned App stopped before another host opens its store. The controller must verify exact native/UI compiler source-list witnesses for both appended files, use the common full-product qualifier, and retain all failures. This document does not supply a successful producer, authorize a different source pin, or bypass that closed qualifier.

The eleven `PINKHA_UI27_STARTUP_*` values retain their original meanings. In particular, `INVOCATION_SHA256` is the **original NativeDerived preparation invocation** hash. It is shared unchanged; it is not relabeled as any of the four later command hashes. The future controller must bind those separately.

## Native phase inputs

Both phases require `PINKHA_G02_NATIVE_READBACK=1`, `PINKHA_G02_NATIVE_PHASE=baseline|postflight`, the original `PINKHA_NATIVE_UI_FIXTURE_JSON`, and the eleven original startup keys: `SOURCE_SHA`, `RUN_ID`, `RUN_ATTEMPT`, `TOKEN`, `SIMULATOR_UDID`, `LANE`, `ADMISSION_SHA256`, `PREPARATION_SHA256`, `INVOCATION_SHA256`, `OWNED_SIMULATOR_SHA256`, `FIXTURE_SHA256`. `LANE` remains `properties`; the actual process `SIMULATOR_UDID` must match.

Both receive the actual raw seed attachment as `PINKHA_G02_SEED_UI_JSON` with its exact `PINKHA_G02_SEED_UI_SHA256`. Postflight additionally receives the exact full baseline hash in `PINKHA_G02_BASELINE_SHA256`, and the actual raw unlink-complete attachment as `PINKHA_G02_UNLINK_UI_JSON` with `PINKHA_G02_UNLINK_UI_SHA256`.

All nine preparation/account flags in the original `NativeTypePreservation.disabledFlags` and `PINKHA_TYPE_PRESERVATION_POSTFLIGHT` must explicitly be `0`. The reader loads the existing account normally; it does not restore or select one itself.

The original UI environment serializes its fixture with Python `json.dumps`, so its raw bytes are not the pinned original native file. The reader hashes the actual installed `pinkha-native-derived-ui-fixture.json`, requires complete decoded equality with the environment JSON, decodes its fixture from that native file, and checks the original file bytes again at the end. It does not repin the serialized environment as native evidence.

## Outputs in the existing App Support directory

For original startup token `<TOKEN>`:

- `pinkha-g02-word-native-baseline-observed-<TOKEN>.json`: actual native observation retained before semantic acceptance.
- `pinkha-g02-word-native-baseline-<TOKEN>.json`: full accepted read-only baseline.
- `pinkha-g02-word-ui-baseline-<TOKEN>.json`: compact native-to-UI handoff with actual Word record/identity and Tag IDs.
- `pinkha-g02-word-native-postflight-observed-<TOKEN>.json`: actual postflight observation retained before comparison.
- `pinkha-g02-word-native-postflight-<TOKEN>.json`: accepted exact unlink readback, only after every required comparison passes.

These names must not already exist. The compact handoff uses schema `pinkha-g02-word-native-ui-baseline-v1`; pass its exact bytes to the UI through `PINKHA_G02_BASELINE_UI_JSON` and its hash through `PINKHA_G02_BASELINE_UI_SHA256`. The full native baseline remains a retained file; it is not copied into a large UI environment variable.

## Validation and retained findings

The first draft and its successful syntax-only parse remain retained. Review then found and corrected two real custody gaps: raw native fixture bytes differ from the original controller's reserialized environment bytes, and postflight must compare baseline/current directory identity across phases. The final source has a second successful Linux Swift `-frontend -parse -swift-version 6` receipt. This establishes syntax only: imports, Swift macro expansion, Apple type checking and runtime behavior remain unverified.

Root's independent source review binds the final source, suffix, unchanged original prefix and all six exact Native8ac source files. Runtime admission remains false. The common8f2 warm-retry control package and its original failed6aab evidence are separate and unchanged.
