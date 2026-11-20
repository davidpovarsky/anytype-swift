# Framework v6: constrained Simulator export signing

## Intended correction and exact boundary

The preserved actual v5 run `44812859123` passed all 99 Mac source controls and built the genuine original framework, then failed strict verification of the exported AmplitudeCore signature. The exact upstream package archive already omits two required sealed `.swiftmodule` files. All 13 exported AmplitudeCore files match that pinned archive byte for byte. The full failed run, original archive, canonical inputs and independent Root replay are in parent **e147e0030edf7d9cf487522738f9d6d34f59d591**. This candidate does not relabel the upstream signature as valid.

This candidate adds one explicit transformation of the owned **iOS Simulator export** of `AmplitudeCore.framework`. It authenticates all 13 source/export file names, sizes, SHA-256 values and modes against the exact original package revision and archive-derived manifest. Its original Info.plist must identify an iOS Simulator framework. Both original resource-seal tables must have exactly the known two missing, nonoptional compiler-module entries, and all present resource hashes must match.

Before any signing, it preserves complete copies of the original framework and exported framework, their metadata, and the actual strict native signature failures. It signs only the distinct owned export with the standard command `codesign --force --sign - --timestamp=none`. The pinned upstream archive and the original producer product remain unchanged. No missing compiler file is fabricated, no resource seal is deleted, and no general framework exception is added.

The final native strict verification remains mandatory. The original per-framework strict gate also remains in the driver. Every other framework still follows the original strict path. The independent consumer must embed the exact resulting export, with the original producer path absent; the complete import/link/resource/native gates still determine qualification.

## Executable and resource preservation

Signing may change only the executable signing envelope and `_CodeSignature/CodeResources`. All framework membership, ordinary file bytes and relevant filesystem metadata remain exact. The driver independently requires that these are the only two changed file hashes in the entire distribution, and records both the old and transformed distribution inventories.

The real pinned executable has two FAT slices. The validator requires their original CPUs, subtypes, order and alignment, with exactly the original allocator's zero-filled FAT alignment holes. Both thin binaries remain original little-endian `MH_DYLIB` files with the same header and full command shape.

The signature starts are fixed at **292,784 bytes for x86_64** and **307,792 bytes for arm64**. Every preceding byte is compared, including all symbol, fixup, export and other LINKEDIT data. Only 20 bytes of documented allocation fields may differ: LINKEDIT virtual size, LINKEDIT file size and signature data size. File size must end exactly at the new signature end. Virtual size stays unchanged unless the larger end requires the original allocator's growth formula, using 4 KiB VM alignment for x86_64 and 16 KiB for arm64. FAT alignment is separately 16 KiB for both. Signature movement, string-table changes and page-alignment mode are refused.

Both before and after signatures must retain the exact ad-hoc identity `AmplitudeCore`, SHA-256 page hashing, empty requirements/CMS wrappers, and no entitlements. Every executable page and the Info.plist, requirements and resource-seal slots are independently rehashed. These checks do not replace native `codesign --verify --strict`.

The initial real binary inspection and Apple's immutable allocator/header sources are retained in the peer review archive. **The actual post-signing envelope produced by the new Apple runner is still unobserved.** The deliberately narrow constraints fail if that real envelope differs; the local controls do not imply native compatibility.

## Exact source preservation

The isolated source parent is **e147e0030edf7d9cf487522738f9d6d34f59d591**. Exactly nine CI paths change:

- A new signing module, its exact archive-derived pin manifest, and 32 new Python controls.
- The existing driver gains only the exact Amplitude branch and the measured distribution transformation.
- The workflow, source profile, one original branch expectation and original Heart installer gain only the new reviewed v6 branch/pin bindings.

All six existing files reverse exactly to their canonical parent bytes. All original 99 test declarations remain; their original bodies are unchanged except the required branch literal in the existing branch test. The project, scheme, inspection facade, consumer, original application and package source, SDK helpers and resource oracles are unchanged. The original 6,000-second framework build, 600-second consumer build, 60/180-second boot pair, 120-minute step and 140-minute job bounds remain unchanged. New signing/verification commands have individual 30-second limits; they do not increase those enclosing budgets.

The canonical baseline has 29 retained input files, and the candidate has 32. The source packet retains every full input, including the already-published pinned archive used by the controls. No frozen branch is modified by this authoring packet.

## Actual local evidence

All executions below are **Linux Python**, with explicit native-tool/source doubles where necessary. No local `codesign`, Swift compiler, Xcode, Simulator or editor mount ran.

| Observation | Actual result |
| --- | --- |
| New FAT-padding rejection against the first helper draft | 1 executed, 1 failed: extra alignment-sized zero padding was incorrectly admitted |
| Initial complete candidate run after exact FAT-rounding guard | 131/131 passed |
| Final complete candidate, with unique retained new driver traces | 131/131 passed, exit 0, 3.59 seconds |
| Whole candidate inputs before/after final execution | 32/32 identical |

The 32 added controls use the genuine checksum-pinned binary and resources. They cover the known seal defect; all original code pages; same/growing/shrinking signature allocation; code and LINKEDIT mutations with recalculated page hashes; timestamp and virtual-size mutations; signature movement; extra FAT gaps; architecture/entitlement/identifier changes; wrong package, device, alias or resource inputs; exact native command order; native command failures/timeouts; complete retained payloads; source mutation; and the complete original driver's strict-gate and exact-consumer behavior.

The synthetic signing fixture only allows tests to distinguish nonsignature payload preservation from a trivial bad page hash. It is an explicit boundary double and is never installed into the runtime driver. Full-driver tests stop before actual installation and retain failure/zero-native scope. The final run preserves separate traces for all three new driver controls. The earlier successful run remains intact; its shared trace name collision is fixed only in the final test evidence identity.

## Qualification and next action

This packet is ready for independent source/evidence review and a fresh immutable Apple run. It does not grant a framework binary, resource runtime, writable facade, host mount, account, exchange, or device result. Root alone activates the exact reviewed v6 route. The prior v4/v5 failures and constructor49 qualification retain their own immutable source identities.

`VERIFY_PACKET.py` verifies complete sealed payloads, exact inverses, canonical source blobs, original/new case identities, actual local results, source preservation and the retained discriminating failure. It reruns no tests, build tools, signing tools or network requests.
