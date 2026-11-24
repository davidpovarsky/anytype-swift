# Original editor Release continuation

This external controller builds the already qualified original Anytype SDK
source in `Release-Anytype` for one platform per invocation. The product checkout
is not edited. The controller is committed in a separate checkout whose only
changes from `8cb346841fcb18490798d32d8d90470d045dfc3f` are in this directory.

## Required actual inputs

`run_release.py` requires an explicit actual SDK commit, its current product
checkout, the original local execution descriptor and source observation, the
qualified Import ABI receipt, and the completed original Debug Simulator SDK
qualification. Their exact digests are arguments. The original source observer
and ABI verifier are loaded from that SDK checkout. The ABI verifier therefore
retains the final producer's pinned wrapper graph requirements; this controller
does not contain an older substitute ABI verifier.

The original ABI execution descriptor, source observations and receipt are
never rewritten. A separate `otzaria.original-editor.release-execution/1`
descriptor records this controller's actual commit/tree/files, the unchanged
SDK commit/tree/root, host, platform, invocation and fresh local UUID. A named
`current-build-source-context.json` binds new compiler and Clang receipts to
that Release invocation without relabeling the original source observation.

## Actual gates

- Original complete Swift/compiler input closure and exact dependency lock.
- Actual optimized `Release-Anytype` compiler command with `RELEASE_ANYTYPE`,
  `PINKHA_NATIVE_DERIVED`, no `DEBUG`, and complete public plus SPI graph emission.
- All original production API64 requirements observed in the actual graphs;
  all22 Debug qualification requirements absent; no own SPI, unowned constructor
  or private original editor/writer exposure.
- Original Clang package declaration closure and path-only module map relocation.
- Owned genuine exported frameworks, resources, modules and notices. The normal
  ad-hoc producer seal preserves every nonsignature image byte, including UUID,
  platform, install names, code and resources. Device exports acquire a real
  signature command before Host applies its separate Apple app-copy signature.
- A separate Release consumer imports only the exported production API. It has
  no project/package/source dependency on the producer. The original producer
  build directory is moved aside before consumer compilation and execution,
  excluding absolute `Bundle.module` build-path fallback.
- Actual single implementation ownership for the original shared runtime,
  Hanlin, Inspector, math and markdown dependencies.
- Before/after equality of source, Hanlin, ABI, controller and distribution,
  finite owned process groups, and deletion of only the disposable owned Simulator.

Simulator builds execute the original resource probe in English and Hebrew and
may earn `ACTUAL_ORIGINAL_FRAMEWORK_EXTERNAL_IMPORT_LINK_RESOURCES_PASS`.
Device builds earn only
`ACTUAL_ORIGINAL_RELEASE_DEVICE_BUILD_LINK_API_PLATFORM_PASS`, with
`device_runtime=NOT_RUN` and no runtime observations. Neither result grants
editor UI, save/reopen, physical device, release signing or TestFlight acceptance.

Final `production-input.json` uses
`otzaria.original-editor.production-input/1`. It binds the verified ZIP,
noncircular distribution manifest, qualification, original source/Hanlin files,
and six separate local receipt roles. Archives are verified member by member
after writing; a packaging failure cannot leave a successful qualification.

`test_release_controls.py` contains synthetic refusal controls. Its results are
never native compiler, simulator, device or product acceptance.

Run only after the previous owner releases the shared Mac build slot. The
controller starts no external coding agents and never reruns the accepted
Native66, generated protobuf or original ABI compilation.
