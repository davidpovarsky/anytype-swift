# Original editor: template and nested-callback compiler repair

This packet retains the actual failed producer input and a bounded compiler repair. It is not framework, editor, consumer, production or physical-device acceptance.

## Actual failure

GitHub run [44986944930](https://github.com/davidpovarsky/anytype-swift/actions/runs/44986944930), attempt 1, compiled source `06d3366988be76c0fe6594f2e6fdc3257997fdd1`. The genuine Xcode framework command ran from 04:53:38 to 05:02:04 UTC and exited 65 without a timeout. The actual log contains two semantic errors:

- The original TemplatePickerViewModel calls the public AnytypeCore assertion function without importing AnytypeCore.
- The original TemplatesCoordinator passes its documentWriteOwner property into TemplatePickerView's synthesized StateObject initializer autoclosure without explicit self.

The framework success checkpoint, graph/export acceptance, separate binary consumer and runtime were not reached. The raw execution record retains its original NOT_RUN success-checkpoint value; FAILURE_DIAGNOSIS.json distinguishes the real attempted/failed command from unexecuted downstream phases.

The one artifact download matches GitHub SHA256 `be2b22b0776234214f3183081e5661e709f31dfa523446cf12d6df8bbf198384`. The inner ZIP is `3f57e924dfcd6fe9752b698754e87743a1c5543d7c736b732c1e12bfb04cc0cd`, with 38 safe members and verified CRCs. Both the original bytes and authoritative run metadata are retained.

## Narrow source changes

All changed product files remain original upstream-owned source; the continuing owner authorization and root's exact full-source reviews cover these narrow changes. No generated code, Heart, dependency pin, Owner implementation, native invocation or public facade is modified.

| Source | Change | Evidence classification |
| --- | --- | --- |
| TemplatePickerViewModel.swift | Import the original AnytypeCore module containing the unchanged public assertion function. | Observed 06d compiler diagnostic |
| TemplatesCoordinator.swift | Pass self.documentWriteOwner to the existing original StateObject-backed view initializer. | Observed 06d compiler diagnostic |
| PropertiesListCoordinatorViewModel.swift | Qualify three member references inside the existing nested source-publication callbacks under the existing weak Task capture and strong guard. | Analogous static compatibility correction |
| SelectPropertyListViewModel.swift | Qualify two options references inside the existing nested original-property publication callback under the existing weak capture and strong guard. | Analogous static compatibility correction |

These qualifiers preserve the receiver, capture lists, synchronous callback ordering, original permissions/source gate and child-retirement paths. The same canonical original property helper is in `Anytype/Sources/PresentationLayer/PropertyValueFlow/PropertyValueCoordinator/OriginalEditorPropertyScope.swift`; it forwards the nonescaping operation through the original scope or the existing legacy path and is unchanged.

## Verification and limits

The two observed source files passed one actual syntax invocation. Its original receipt incorrectly labeled an inherited working directory as the repository; the raw receipt remains intact, and SYNTAX_METADATA_CORRECTION.json records that the exact inherited cwd was not captured. Compiler and input paths were absolute. The command, input bytes, timestamps and successful exit are unchanged. No invented cwd observation or syntax rerun is used.

The two additional property files passed a separate new syntax invocation with an explicitly set working directory. The first pair and earlier behavioral suites were not rerun. Syntax parsing does not establish Apple module type correctness or runtime behavior.

The static inventory contains 149 changed Swift files between the retained v10 input `c89d6726c3b2ad6e418296c5ed0f7d705fb88433` and frozen 06d. Every source snapshot is bound to its exact Git blob and SHA256. The scan examines direct original assertion imports and the known owned nested-callback and StateObject constructor patterns; it is candidate discovery and human source review, not an exhaustive compiler certification.

The failed 06d run's 221 source controls passed, its before/after source observation was identical, and its exact original macro trust was restored. These are retained facts about that input, not proof of the new Swift product source. The exact 51-pin package closure, all original modules/resources, original Heart provenance, scoped macro preparation and public facade contract remain separately enforced by the unchanged producer gates.

## Integration gate

The next source/profile seal must bind these exact reviewed file bytes and all original execution inputs. A single normal push runs the actual Apple framework route. Only its genuine result can authorize exporting a qualified simulator framework and advancing the separate consumer. The existing Debug/simulator guards and device/production runtime requirements remain in effect.

The production annotation policy/readback/permission work stays on its separate branch. No identity receipt, native schema registration, mapping writer, body acknowledgement, account bootstrap or live production create is enabled by this compiler repair.
