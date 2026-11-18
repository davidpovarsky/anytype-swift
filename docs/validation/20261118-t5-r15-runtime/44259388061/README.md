# r15 generated dependency scope — actual failure and bounded correction

## Actual result

Run [44259388061](https://github.com/davidpovarsky/anytype-swift/actions/runs/44259388061), source `28efafceb3970762a3a988581755984a3718e9ce`, completed **FAILURE** on 18 November 2026 at 08:31:44 UTC.

The failure was `Selected genproto differs from the existing reviewed dependency and checksum`. This was **selected dependency validation before gomobile/native compilation**, despite the encompassing workflow step being named “Build and verify all three r15 Apple binary architectures.” No new framework was produced and zero native tests executed. The earlier immutable-seed guard was retained and the run advanced to the selected dependency check.

Original artifact `14410966676` is retained as `artifact-14410966676.zip`; its SHA256 is `30a3a032db1f753d229ea85d025ad5b1af816d0211a408d71eb6807120a1e368`. The inner ZIP is `30e39ab7689eef84eb6db2ce5a2c7d8b691681fa1eb422108af727859bd91d30`. All 21 original members, totaling 1,754,170 bytes, are preserved under `original/` with individual hashes in `artifact-verification.json`. Raw files have Git text normalization disabled.

## Evidence and cause

The original native graph contains 882 modules. Its selected root `google.golang.org/genproto` version is `v0.0.0-20240903143218-8af14fe29dc1`, replaced by the already-reviewed `v0.0.0-20241021214115-324edc3d5d38` with the expected module and go.mod checksums.

Pinned gomobile flattens that graph into a generated module and writes a **version-qualified** replacement. The original and hydrated manifests both contain the replacement for the September 2024 selected version only. The hydrated generated graph contains 1,070 modules including its main module; it selects `v0.0.0-20260128011058-8636f8732409` without a replacement. Its real checksums therefore belong to another selected dependency. This is not a missing-checksum error.

The original generated module's `googleapis/rpc` replacement still resolves to its reviewed October 2024 revision. No change is made to that replacement or any other module's replacement.

The successful original r14 run `44203168617` was also compared. Its small receipt and command logs prove a three-slice build with `NOT_RUN_BUILD_ONLY` native test scope; neither those records nor its original job log records effective genproto selection. The r14 helper removes GOWORK and invokes gomobile init. **No effective genproto version is inferred from successful r14 compilation.** Comparison metadata is in `r14-r15-comparison.json`; the retained r14 receipt remains in `docs/validation/20261118-heart-r14-rebuild/records/heart/custom-heart-build.json` on the integration branch.

## Correction

The generated dependency seed remains an immutable, exact reproduction of the pinned gomobile input. A new narrow operation applies the existing versionless genproto override to the disposable hydration copy, after checking that its original manifest exactly matches the seed. The same operation runs in each actual generated gobind module after the original pre-tidy input has been verified.

The operation removes only `Old.Version` from the one existing reviewed root-genproto replacement. It rejects missing, ambiguous, already-normalized, foreign, or otherwise changed original replacements. Actual Go metadata readback must show that every other module declaration is unchanged. Before/after manifests and original bytes and hashes are recorded separately.

The version 2 bind contract carries both the original manifest and the prepared runtime manifest. Hydration's selected-MVS requirement comparison uses the prepared manifest. The final three-architecture gate requires the same exact scope correction, ties it to each original pre-tidy module, and retains all existing actual selected-module and download checksum checks. Module pruning after tidy remains the only permitted graph reduction.

Heart source, native patches, native go.mod, Go 1.26.5, pinned gomobile, reviewed genproto revision/h1 values, rpc replacement, and the r14 builder are unchanged.

## Validation and limits

- **38 Python controller test functions / 114 subtest outcomes passed**, with zero failures, errors or skips. These cover original input, foreign mutations, scope isolation, retained byte evidence, contract drift and all prior graph/checksum gates. The original log and source hashes are retained.
- A bounded **actual Go 1.26.5 metadata-only probe** loaded the original captured seed and reproduced its original manifest, then applied the new production helper successfully. No module hydration or compiler was invoked for this original-source check.
- A separate synthetic local file-proxy fixture reproduced the Go selection behavior: the version-qualified replacement let the newer selected version escape; the versionless replacement retained that selected version while resolving its effective dependency to the reviewed revision. This used 43,289 bytes of task-owned files, zero network downloads and zero native compiles/tests. Its fabricated module hashes are explicitly **not** genproto checksum or native acceptance evidence. `go-metadata-probe.executed.py` preserves the exact executed script; `go-metadata-probe.json` preserves actual results.

A complete hydration/build with this correction remains **NOT_RUN** until the reviewed CI attempt. Apple runtime pairing, T5 native UI and Hebrew/RTL Light/Dark R08 acceptance remain **NOT_RUN**. The global capability stays OFF; indexedTargetsOnly must not be reported as Space-wide coverage. The T5 task remains open.
