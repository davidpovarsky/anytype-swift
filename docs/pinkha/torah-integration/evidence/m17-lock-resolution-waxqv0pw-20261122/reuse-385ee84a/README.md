# M17 dependency identity for the new frozen Maktabah consumer

**The historical strict resolution of all 17 Swift packages is reusable for the unchanged dependency graph at application `385ee84a8acb3fbc3c013c0977417b61fd3d8a17`, using execution metadata `46a185242b28b71d4b6d253747f2b8d46e4189a0`.** This review performs no resolution, preparation, compilation, test, Git mutation, Actions query, watcher action, or secret operation.

This is the requested response to Asana handoff comment `1220765861889338` of 22 November 2026, 03:18:47 UTC. The immutable source baseline is `813fbe79c1b325ee21a8c2be78bb86577f44bf6c`. Its actual M17 run `44976915323`, attempt 1, succeeded with one strict invocation, no automatic resolution and no strict replay. Its complete original evidence was already published at:

https://github.com/davidpovarsky/anytype-swift/tree/538b2c9ca153c81a593faa08fab3b6a080d428e8/docs/pinkha/torah-integration/evidence/m17-lock-resolution-waxqv0pw-20261122/actual-run-44976915323

## Actual source comparison

The review fetched complete, untruncated immutable Git trees for the baseline, application and metadata commits. The original and changed project files, all three stage2 manifests, and the original preparation driver were read as immutable Git blobs. Their complete UTF-8 bytes were verified against the expected Git object hashes; no line normalization was used. The standalone audit and machine-readable result are retained beside this README.

| Boundary | Observed identity |
|---|---|
| Original committed preparation inputs | 21 of 23 are byte-identical. The two differences are the project file and stage2 source-binding JSON. |
| SwiftPM lock | The same schema-2 blob `99a5b952aab40cb3d5ffe03153c9cf8c07ed341b`; all 17 full pin objects are unchanged. |
| Package objects and owning attachments | All 36 local/remote reference and product objects are unchanged. The complete PBXProject and all six PBXNativeTarget sections are byte-identical, including every package-reference and package-product attachment array. |
| Build configuration | Complete XCBuildConfiguration and XCConfigurationList sections are byte-identical. All four committed schemes are unchanged. |
| Local package manifests | Complete Source/Vendor `Package.swift` and `Package.resolved` membership and Git blobs are unchanged. All seven actual local package reference paths remain the same. |
| Original preparation | The entire stage2 driver, both preparation helpers, Podfile, submodule declaration, privacy plist, iOS plist, Google configuration blob, and whole Vendor tree are unchanged. |
| Hanlin | The same `e00498e33f106cc43be0476ffa2e09329c8ca300` gitlink. The current immutable Git tree exactly matches all 424 paths and Git blobs in the original before/after/final receipt. |

The complete project difference is **eight added lines** registering `AnnotationCloudImportIdentity.swift`: three build-file objects, one file reference, one group entry and three original target source-phase entries. No prior line was removed. Removing exactly those eight additions reproduces the baseline project bytes. This changes application compilation inputs, without changing package resolution or target ownership of packages.

One local package also has a real compiled-source change: CommandPalette's source tree changes from `871a6ce1…` to `3d4c6f71…`. The sole changed file is `CommandPaletteView.swift`, whose complete diff adds the existing row's accessibility identifier. Its manifest and file membership are unchanged. The other three non-Hanlin local package trees are identical. **No compiled CommandPalette or application-code equivalence is claimed.**

## Source binding and preparation scope

Application commit `385ee84a…` contains the preceding source-binding manifest, still naming `5f862ea7d785de813fc28680cfe403a3e082ba22`. Execution metadata commit `46a18524…` names the actual frozen application `385ee84a…`; its Source, Vendor and project tree identities match the immutable application tree. Use the latter as the current execution binding. This audit does not silently treat the application commit's older metadata as a new self-binding.

Against the baseline manifest, the changed top-level keys are `application_source_sha`, `application_trees`, and `otzaria_test_additions_sha256`. The original preparation functions read only `hanlin_gitlink` and `sefaria_gitlink` from that configuration. Both values are unchanged, and the complete function-containing driver is unchanged. Actual original preparation calls, local package manifests, target settings and package attachments therefore preserve the resolution input graph.

## What remains bound to the old run

The archived M17 before/after workspace receipts remain internally identical over 268 generated files, and the old Pods project introduced no Swift package references or attachments. **That complete 268-file byte stamp is not transferred to the new consumer.** Its current workspace has not been generated by this audit, its project contains new source registrations, and `Podfile.lock` is not committed at either source. A fresh `pod install` must not be assumed to produce the same external Pod closure solely because Podfile is unchanged.

The normal new preparation/build gates must still inspect their actual generated workspace, dependency lock, privacy aggregation and provider output. Historical preparation used Node 22.23.4, Ruby 3.3.14 and CocoaPods 1.17.0; historical resolution used Xcode 27.0 and Swift 6.4. This review does not observe a new runner or grant new Apple, Native, Stage B, provider, release or device acceptance.

The bounded reusable result is the existing successful strict resolution of the identical 17-package graph. There is no need for a duplicate standalone resolver run for these source-only changes. A later SDK distribution, dependency pin, manifest, package attachment or preparation change requires a new input-identity assessment.

## Coordination state observed from owner comments

The producer owner reported run `44978502186` / `cb2df9baa201db0ce404ba37eac853424bae6204` terminal failure in CrossApp comment `1220766040567913` at 03:28:01 UTC. The sole observer ended at 03:13:20 UTC. Macro admission succeeded and the original macro trust bytes were restored. Actual compilation exposed the typed-error boundary in PublishingService and five app-only ObjectDetails extension uses in TemplatesService; their owner is repairing them. This audit did not query Actions, start an observer, or alter that producer.

The Native owner retains the next four-case run: the three previously failing cases plus the consent diagnostic, without a provider key, Connect or Send. This dependency audit does not take over that lane.

`M17_REUSE_AUDIT.json` records the exact hashes, mismatches, section proofs and reuse limits. `audit_dependency_identity.py` only reads the retained immutable source/evidence and writes that local report; it executes no production or test body.
