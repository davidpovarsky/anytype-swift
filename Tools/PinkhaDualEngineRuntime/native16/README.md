# Shared NativeUI continuation for sharing and Archive

These files prepare one complete NativeUI runner for the current integrated app. The selected continuations are `sharing-owner` and the full `archive` roundtrip. The already accepted drag method is retained in the complete original source and is not selected again.

No app build, UI build, simulator operation or application test has been performed by this preparation. Wave 3 stopped the proposed a089 App16 queue before compilation and requested the next integrated product. The existing common qualifier `4ec8617c59da3183a68a53ea9f840e57738469f36f9a0bc5b5a00e806d73cd9c` remains an a089 preparation; it must not be relabeled as acceptance of the next source.

## Source authority

At execution, the source commit and SDK/lock/native binary pins come exclusively from a separately reviewed exact shared qualifier and its immutable successful producer admission. There is no source-commit override. The NativeUI profile requires the common qualifier's `APP16_SOURCE` to equal the admission source and invokes its complete `admit_and_clone_products` API before compilation or XCTest. The common qualifier must validate the actual App and complete Stage1 UI producer, not a fabricated receipt or a header-only source change.

The admission API remains:

```python
source_proof, products, app = shared.admit_and_clone_products(
    admission, private_root, evidence_directory, commands
)
```

The verified common file is placed beside the generated controllers as `combined_heart_semantics_current.py`. Its actual reviewed SHA-256 is required on every invocation. Native manifest `8ac407e75a4bfb42c359a2f72b3822c44990caedf2351d00d78315de5c96a04b` is fixed; a different native contract requires a separate review.

NativeUI source remains independently fixed: NativeLaunch `fdb706fc9d1c805ceb7220e4ae64a14244f7437525cf06d8d14e1b1f100de6da`, NativeHistory `2772d790979de88a3b622f17453a91ca792114292016f01e31386de7f4f614ca`, the original project/scheme, and the original projection/selection/result helpers. The title correction is reversed in memory to the complete original `0b4cbd…` file using the two reviewed fragments and original proof `3d7bb101…`. Original invitation, ownership, confirmation, cancellation, reopen and Archive assertions are retained. Source overlays are refused.

## Materialize and build once

Run this preparer against the retained original `build_prebuilt_native_ui8ac.py` (`e6c4c506…`) and `run_prebuilt_native_ui8ac.py` (`18c7cc57…`):

```sh
python3.12 -B prepare_native_ui16_controllers.py \
  --original-controller-root /absolute/original-nativeui-control \
  --native-ui-profile /absolute/native16_profile.py \
  --output /absolute/new-nativeui-control
```

The preparer retains every original controller byte through a reversible delta. The original builder command, disk floor, growth allowances, 1200-second build timeout and process lifecycle remain unchanged. The original consumer's descriptor binder, selected method, enumeration, XCTest result checks and cleanup remain unchanged. The changes load the new profile, bind the shared admission, and add a post-build compiler/product proof.

After Wave 3 has reviewed the final common qualifier and admitted the successful app producer, place that exact common file beside the generated controllers and run the UI-only build under the coordinated Mac owner:

```sh
python3.12 -B /absolute/new-nativeui-control/build_prebuilt_native_ui16.py \
  --main-root /absolute/shared-main-root \
  --main-evidence /absolute/shared-main-root/actual-build-evidence \
  --source-root /absolute/actual-frozen-source \
  --output /absolute/shared-main-root/native-ui16-build1 \
  --shared-controller-sha256 ACTUAL_REVIEWED_COMMON_CONTROLLER_SHA256 \
  --shared-admission /absolute/actual-shared-admission.json \
  --shared-admission-sha256 ACTUAL_SHARED_ADMISSION_SHA256
```

The build preserves the original `receipt.json` and creates `native16-qualified.json` only after the real SwiftFileList contains exactly the two original NativeUI source files. It retains those compiler lists and the complete product inventory including modes and links. Both receipts are required; a build success without the additional qualification is not admitted by the consumer.

## Consume the same runner

Use separate fresh execution roots for sharing and Archive. Supply the actual SHA of `native16-qualified.json`:

```sh
python3.12 -B /absolute/new-nativeui-control/run_prebuilt_native_ui16.py \
  --main-root /absolute/shared-main-root \
  --main-evidence /absolute/shared-main-root/actual-build-evidence \
  --source-root /absolute/actual-frozen-source \
  --ui-build /absolute/shared-main-root/native-ui16-build1 \
  --output /absolute/shared-main-root/native-archive16-attempt1 \
  --stage archive --retain-owned-simulator \
  --shared-controller-sha256 ACTUAL_REVIEWED_COMMON_CONTROLLER_SHA256 \
  --shared-admission /absolute/actual-shared-admission.json \
  --shared-admission-sha256 ACTUAL_SHARED_ADMISSION_SHA256 \
  --native-ui-proof-sha256 ACTUAL_NATIVEUI_QUALIFICATION_SHA256
```

For sharing, use `--stage sharing-owner` and a distinct output root. Each invocation creates a separate adjacent `OUTPUT-app16-intake` directory for verified APFS product copies. Existing directories are rejected, including after a failed attempt. The original build/evidence, simulator account and previous failure receipts are not overwritten.

The old sharing attempt `df8ad97c…` remains a failed/incomplete original attempt; no completed XCTest total is inferred. The old Archive failure `733b210f79f5b31cb07772e104f6dfd43285d0e11dd818346fa28eb537131d94` remains failed. Picker-only diagnostic `8e473704…` is not full export/import acceptance. The full Archive method must perform actual Save, import, canonical mapping/body verification and cold reopen, with original screenshots and xcresult retained. Physical-device acceptance remains outstanding.
