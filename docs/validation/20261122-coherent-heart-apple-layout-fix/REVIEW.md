# Coherent Apple bind ownership repair

The original Apple run [45030504099](https://github.com/davidpovarsky/anytype-swift/actions/runs/45030504099), source `22f4fa5aa8b29c167bcda100e23a30438a22adab`, failed before producing either framework or executing XCTest. Its first generated `go mod tidy` was refused by the unchanged `r15_runtime_go.load_seed_contract` ownership check (exit 91).

## Concrete cause and correction

The reviewed binding preparer writes `work/binding/generated-dependency-seed/bind-contract.json`. The coherent controller then moved `PINKHA_T5_MOBILE_TMP` to `work/production/gomobile-tmp`. The launcher requires the contract to be within the generated temporary root's parent, so the original layout is correctly rejected even with the correct hash.

The new controller puts separate temporary roots at `work/binding/production-gomobile-tmp` and `work/binding/fixture-gomobile-tmp`. Production and fixture framework outputs remain under their separate original directories, and launcher audit receipts remain distinct. The actual unchanged launcher gate is called before bind and still executes in each generated child process. The original binding-contract bytes are now copied into the evidence archive and checked against their original digest; each variant records the accepted ownership scope.

A second deterministic identity mismatch was found by source review: the shared simulator validator hard-coded the earlier authorized-read candidate's runtime version. It now accepts a keyword `expected_version`, with the original version retained as the default for existing callers. The coherent caller passes the full version from the qualified original139 receipt. Platform, variant, architecture, slice path, marker equality, and binary digest checks remain enforced.

## Validation and retained evidence

`VALIDATION.json` and `new-binding-controls.log` record four new stdlib controls with unchanged tested source hashes:

1. Reproduce the original unowned layout rejection using the actual unchanged launcher, then qualify both new distinct roots without changing the prepared contract or environment.
2. Reject an unowned root, changed contract bytes, wrong digest, foreign native checkout, and symlink contract before bind.
3. Require the exact supplied coherent version, retain the exact legacy default, and reject wrong markers, architecture, platform, slice paths, or digest shapes.
4. Reject reuse when any tested source or original log/build/archive evidence changes.

The tests compile the two narrow controller functions directly from their real source AST, with the unchanged complete launcher imported normally. They establish filesystem and identity-gate behavior. They do not execute gomobile, rebuild139, or prove iOS behavior.

The workflow reuses exactly five Python controls, including their three embedded Go assertion-adapter methods, from the original successful control step. `retain_controls.py` requires all seven unchanged source dependencies by SHA256 and validates the byte-exact original ZIP/log/build. It explicitly records the overall original build failure and never translates those controls into framework or XCTest acceptance. Only the four new regressions execute again.

Original evidence requirements (root owns publication):

- `docs/validation/20261122-coherent-heart-apple-failure/original-evidence.zip`: `43c61574eb4aeb2d9a19ccaba88748839b335032548e059a05ab278c17109ad1`.
- `original-controls.log`: `10aa62a87285e947c694ce5882cf7daf5a7b1e57cd8fa6f590b058eb85837a92`.
- `original-build.json`: `8297160846c1c4fa1505c1729fb7ddc6f2ffabee0f5bfe5c10298afe2602bfc3`.

## Delivery and remaining gate

`COHERENT_APPLE_LAYOUT_FIX_FILES.json` lists the five files to publish, with exact Git-verified baseline identities and new hashes. Supporting baseline files and the local duplicate proof are not deliverable source changes. No qualified native139 source, generated native protobuf, original fixture, launcher guard, or Swift module changed.

A new producer execution remains required to establish actual production and fixture builds and the one new XCTest. The original failure produced no framework to reuse. The original native139 proof and unchanged control evidence remain reusable; no prior native or Swift test method was rerun for this repair.
