# Framework v5: original build passed; distribution signature failed

## Exact execution

The immutable workflow **44812859123**, attempt **1**, ran source **196459fc9fa943f90e5c7f256545f94083e373e3** (tree **bd3afe1eb84ec2285d52856b10860a7bae70df9d**). Job **136553572930** concluded **FAILURE**. This packet preserves the complete authenticated workflow artifact **14668938238**: **1,686,079 bytes**, SHA-256 **fda87acf19d28cf2b465b3c081874e1b215a3d49cc2c7c739c2de0d214ccebec**. Its outer ZIP has one member and the complete nested evidence archive has 45 members; all CRCs passed. The full job log, original 10.6 MB compiler stdout, xcresult, commands, raw compiler input list, three generated bundle accessors and final cleanup are retained.

The original Mac source controls executed **99/99 PASS**. The genuine `AnytypeOriginalEditor` target then completed its original `Debug-Anytype` arm64 iOS Simulator build with exit 0, using Xcode 27, Swift 6.4 and SDK 27.0. The exact 6,000-second build bound and original signing/compiler flags were preserved; actual command time was 20:37:40–20:53:56 UTC.

The first failed command was `codesign --verify --strict` on exported `AmplitudeCore.framework`, at 20:54:22 UTC. It returned **1**, without timing out, and reported **“a sealed resource is missing or invalid.”** The distribution inventory was already produced, but the signature gate rejected it. **The separate consumer build, public symbol graph, Simulator boot/install/launch and native editor UI did not run.** The workflow is not a qualified framework delivery or editor mount.

## What the source and build evidence establish

The source observations before and after execution are identical. All 26 recorded source inputs are bound by byte length, SHA-256 and Git blob to the actual frozen Git tree; the unchanged package lock is supplied as a 27th canonical input. The canonical tree corroborates all 2,237 original Swift source paths and the complete original source, resource and module trees. The original compiler list contains the required 2,238 original inputs (all original source except the app entrypoint, plus the original asset constants and the additive inspection facade), and one generated input. Exact raw lists and generated `Assets`, `DesignKit` and `Loc` accessors are retained.

All 44 original package revisions were actually materialized and matched their lock. Original Heart installation and slice verification passed before the build. The initial original Hanlin SDK snapshot records 407 files at revision `116cc6be0654a5d11bc56ba00e0310031107ee36`; the later post-runtime SDK comparison was **not reached**, so this packet does not invent a final SDK-preservation result.

Export produced inventories for 17 genuine frameworks and 34 original resource bundles. The reviewed exact two-location Lib closure check passed; no arbitrary duplicate selection was used. All 1,300 compiler-output lines containing `warning:` are preserved (869 unique exact lines, including repeated diagnostic renderings). These are line counts, not a claim of 1,300 independent compiler warnings.

The owned simulator cleanup records shutdown exit 149 because both devices were already shut down, followed by successful deletion of each owned device. This is retained as actual cleanup, not a successful boot.

## Proven missing upstream resources

The original package lock pins `amplitudecore-swift` at `13fd0eb0aa080816ffa409669758b2e8787322b2`. Its genuine `Package.swift` (Git blob `b8720d5b79c8cad6b13564bc5fa959be2fbf3c26`) pins the upstream release archive by SHA-256 **2c0fbe60170efdf0b634ae73298803880098e1d352c9afef2baface15b45070c**. The downloaded original archive is **1,964,793 bytes**, with all 194 ZIP members CRC-verified.

Every one of the 13 regular files in its original iOS Simulator AmplitudeCore framework has exactly the same path, length and SHA-256 as the actual v5 export. That upstream slice has no symbolic links. Both original resource-seal tables nevertheless require two absent files:

- `Modules/AmplitudeCore.swiftmodule/arm64-apple-ios-simulator.swiftmodule`
- `Modules/AmplitudeCore.swiftmodule/x86_64-apple-ios-simulator.swiftmodule`

Neither entry is optional. All 21 resource-seal digests for present files match. The archive already lacks those two sealed files, including before this exporter can copy it. The independent Root replay of that exact archive and export comparison is retained in the upstream provenance ZIP.

This is byte-level evidence of an upstream missing-resource seal. No local `codesign` was executed. The actual producer filesystem's original signature was not separately checked by v5, and its metadata was not retained for this framework. The evidence therefore does not claim an observed original-product `codesign` result or exhaustive equivalence of every filesystem attribute. No third-party bytes have been repaired, removed, fabricated or re-signed in this packet.

## Read-only replay and limits

Run `python3 VERIFY_PACKET.py <packet-directory>` to verify the sealed payloads and replay the actual result classification. The verifier performs no compiler, test, GitHub, Simulator or signing commands. It checks the real 99 declarations/results, exact command exits and raw log hashes, compiler input closure, source before/after, Git identities, original dependency lock, complete archive CRCs, and the upstream/export/seal comparison.

The failed v4 run and its genuine alias-path fixture repair remain in source ancestry. No earlier build or runtime result is transferred to v5. This packet does not qualify the newer constructor49 or prepared-host draft; those have separate sources. No writable public API, editable UI mount, original app runtime, live account exchange or physical-device acceptance is asserted.

Signed artifact-download URLs and `DOWNLOAD_INPUT.json` are deliberately excluded. The full original archives and safe canonical API responses are retained. Future Simulator packaging changes must be explicit, constrained transformations with their own before/after provenance and actual Apple qualification.
