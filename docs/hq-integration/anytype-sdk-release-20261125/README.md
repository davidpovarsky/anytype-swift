# Anytype SDK release continuation and native reuse controls — 2026-11-25

## Observed Release Simulator result

The original SDK source `34b8a7c5ddb34e9287acdb5c189849eeac8cff86` completed actual Release Simulator ownership verification and exact packaging on the Scaleway Mac. SentinelX job `job_82a54c1b8ad1` exited 0. The continuation used controller `616646f74170f66a252b94b4bf97676b31787947`, branch `codex/otzaria-release-resume-20261125`.

The original framework build, external consumer build, 89 public declarations, absence of 22 Debug SPI declarations and actual English/Hebrew resource executions were preserved from original execution `local-6e3e3d5e-ab07-4c1e-8c01-83b088faf4f6`. The ownership/package continuation has its own execution `local-7975dadf-ad1b-42de-97a1-823efefce8a9`. Neither execution identity was relabeled.

The original `xcrun nm -gjU` timeout came from reconciliation of a Mach-O nlist with a much larger native dyld export trie. A 600-second retry still timed out. The new bounded observer combines the actual nlist with the actual native export trie, requires the relevant Mach-O flags, strictly parses every entry, and omits no export. Exact parity with original successful nm output was established for four arm64 images. OriginalEditorSharedFirebase required 170 extra dyld definitions; Release AnytypeCore required 654. An initial parity batch rejected a fat Amplitude image; that batch remains failed and was not relabeled.

Final Release ownership observed 9,366 selected definitions with exactly one owner, 12 shared Host modules and 603 original dependency source files. The Release archive has 2,324 exact members; CRC, membership and every member's bytes/hash were checked. This is SDK compiler/consumer/resource acceptance. Native editor UI, C–F synchronization, physical-device acceptance and TestFlight are not granted by this result.

| Artifact | SHA-256 |
| --- | --- |
| Original failed Release execution | f8a5e893dd6c3e9e0f46163d7f5882c3db2c9407fc83c19b4c9639b6d45a1f39 |
| Continuation RESULT.json | 0d36dbd7722e4add236eb291ccb94e2b7821b9d24cf7d1d95592e164b9f241b3 |
| Shared ownership receipt | d0b903dae30c5af3feea79756815358b3906fba9fc4c5c55ad875fdd19d8cb17 |
| Release QUALIFICATION.json | d8c04de3ca4a5d97d28c63470d7364c8f9b26b28f01b43314108ab1618156548 |
| Release production-input.json | 064dbd09515e3f13a4af48b1d38be9df2633330024f03a9069b639e37cbc21e1 |
| Release-SDK.zip, 317,962,802 bytes | 44032267bb25372db2ff097965f67e4f47f7a7206f910bfb64e5da22f34faad3 |

Mac evidence: `/Users/m1/builds/anytype-34b8a7c5ddb3-sdk/build/SDK-Release-Simulator-Continuation-20261125`.
Qualified distribution: `/Users/m1/builds/anytype-34b8a7c5ddb3-sdk/build/SDK-Release-Simulator-Work/distribution`.

## Current facade checkpoint and strict native reuse

Product checkpoint `73291acd232ead88a3d25dd75848e7fe5bac05f3` changes five production facade files, has 105 public requirements plus 22 Debug SPI requirements and pins Hanlin `4e921b9517f2fc28fcaebcb2ba7441ab1fb46a90` / Swift AI `3f38f1302764635c9991d0d00fd7b12471a5373c`. Further C–F product API work is pending. It has not received final three-configuration SDK qualification.

Historical generated-source gates previously required the older facade tree. The additive adoption document now binds exactly the separately reviewed five-file change, verifies committed and working bytes, checks ancestry and keeps the original generated/native/UI/resource trees unchanged. Historical generation and local-annotation adoption documents remain untouched.

The native donor adapter preserves the original source `34b8a7c5ddb34e9287acdb5c189849eeac8cff86`, its actual execution, native66 proof, three-architecture wrapper checks and ABI receipt. A fresh interpreter imports the original owner's unchanged verifiers and checks the original live source against its retained source-before record. The consumer must have its own real local execution and exact source identity. Shared native/generated/wrapper Git inputs and all 17 native library members (941,569,950 bytes) must match exactly. A reference document grants no acceptance by itself.

The adapter does not rerun native tests or generators, does not alter original receipts and does not grant new SDK/UI acceptance. Every new SDK variant still requires actual compilation, external consumer linking, complete public/SPI checks, ownership, applicable resource runtime and exact packaging.

The local qualification branch is explicitly `codex/otzaria-annotation-sdk-requalification-20261125`. Further production facade changes require a newly reviewed exact adoption before any expensive qualification run.

Controls: 13 Python tests passed (7 new provenance-control methods and 6 existing local-identity methods). These reject changed/missing/extra facade members, altered source or document binding, acceptance inflation, wrong source/run/policy references and nonlocal identity. They are not native SDK or C–F acceptance.

## Storage retention

An independent exact archive of 14 inactive old product roots contains 42,910 members and 16,790,725,514 regular bytes. The archive is stored on Oracle:
`/mnt/development/artifacts/otzaria-retained-20261125/retained-products-v1/retained-products.tar.gz`.

- Archive: 5,447,045,120 bytes; SHA-256 `9acb16c572f787929692bd86fabd2fbb982d0d85cff682daf545f13c8998c8a3`.
- Manifest SHA-256: `8726cd1d47144d4e5a90ca31d24df036ba52838bb4e1195879b028ddf856dafa`.
- Independent verifier: exact membership, all regular bytes and SHA-256, modes, symlinks, hardlink closure and gzip CRC passed.
- Verification receipt SHA-256: `3a77d16435591e729d6be602532734e4a7604832e316548311e560684931f527`.

Source/Git/checkouts/repositories, historical evidence and the current 34b8/c7e9 workspaces are protected. Final retirement requires a second current-source/product/open-file check on the Mac and its own terminal receipt. Do not infer completion from the archive alone.

To restore, verify the archive and manifest on Oracle, transfer through the existing pinned SSH route, and extract the verified archive with its relative member names under `/Users/m1/builds`. Do not rewrite the historical source/proofs or claim fresh execution. The archive is a retained rollback artifact, not a newly qualified SDK.

## Remaining gates

Finish the actual production API needed by C–F, observe the targeted facade compiler result, update the exact adoption to the final product source, stage/materialize matching Hanlin, and perform actual Debug, Release Simulator and Release Device qualification. Integrate only those final accepted SDK artifacts into the matching Maktabah source. Application Native116/Release114+2, real UI/synchronization/library acceptance, official signing and TestFlight remain separate gates.
