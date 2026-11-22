# Original editor: explicitly typed Undo/Redo preparation

This packet retains the actual failed Apple input and a narrow source-level inference repair. Only the subsequent genuine Apple build can establish that this repair resolves the original framework failure.

## Actual failed Apple input

[Run 44992780854](https://github.com/davidpovarsky/anytype-swift/actions/runs/44992780854), attempt 1, checked out 925b7e3cc687dcccad7703f57bd0a6b374dc1919. The actual original framework command ran 06:15:15.834641–06:23:56.239354 UTC, exit 65, no timeout. Its single source error was:

> UndoRedoView.swift:18:25: error: failed to produce diagnostic for expression

The compiler located the whole SwiftUI body. The nested optional preparation closures inside two generic AsyncButton invocations are the reviewed inference boundary being simplified; the compiler did not provide a more specific cause. The proposed cause remains an inference until actual Apple compilation succeeds.

The original framework semantic build did not complete. The driver's original_framework_build NOT_RUN is its unreached success checkpoint, not evidence that no compiler command occurred. External binary consumer, native runtime and UI tests were not reached. The 221 source controls passed for this exact failed input; source-before/source-after bytes were identical; exact original macro trust restoration succeeded. Those facts do not qualify the repaired product source.

## Exact narrow repair

Original path: Anytype/Sources/PresentationLayer/TextEditor/Views/UndoRedo/UndoRedoView.swift.

The two inline optional preparation ternaries now have explicitly typed private computed properties. Reading a property only checks the same hasDocumentWriteOwner value and returns a deferred closure; prepareUndo/prepareRedo still execute only when the original AsyncButton invokes its preparation at the actual tap, before the original asynchronous action. Legacy nil preparation and fallback action remain unchanged.

The native AsyncButton, model, owner checks, scheduled mutation, labels, accessibility identifiers, layout, snapshot and RPC code are unchanged. No new dispatcher, renderer, permissions or native action is introduced.

Root read the entire original/candidate/patch and full real AsyncButton/model, and approved the exact patch. SOURCE_PROVENANCE.json and FINAL_REVIEW.json bind all source bytes.

## Actual focused validation

One whole-file syntax parse passed. A separate Windows Swift 6.3.3 strict-concurrency executable compiled the exact extracted property declarations against the exact original nested closure type. An explicitly labelled model timing probe observed four boundaries: legacy absence returns nil; property access does not prepare or execute; invoking the returned factory prepares synchronously; awaiting its result executes the deferred action. No previous behavioral suite was replayed.

This probe does not compile or execute SwiftUI, the original AsyncButton body, real Owner, native service/RPC, UIKit or any editor UI. It does not reproduce or claim to resolve the Apple compiler failure. The full raw compile/execution commands, explicit cwd, source/probe/binary hashes and output are retained. Compiler stderr is only the Windows linker library/export informational line.

## Bounded related-source review

The actual prepareAction callsite inventory found two analogous alert constructor ternaries and three AsyncStandardButton ternaries. Their immediate constructors are non-generic and have explicit parameter types. Related full immutable snapshots are retained. Root agreed to leave these sources unchanged without a matching diagnostic. Other sites pass already typed properties or factories.

This is a bounded same-pattern review, not exhaustive compiler certification. No earlier actor/weak-capture inventory or successful lifecycle suite was repeated.

## Artifact and operational provenance

Artifact 14742544086 was downloaded once as 1,253,644 bytes, SHA256 e7c9c7e80ee66fa526005ec1f91836918fc15ba7f89cc87a89717fa7b5645e31. Its inner ZIP is 5cefd4fdb6cad972dfe3bea376645b164410b908cb3819710bd8b4d28b1868b8. All 38 members passed bounded path/duplicate/symlink/encryption/expanded-size and CRC checks. The complete archive retains all original logs and xcresult bytes; selected records are copied unchanged for review.

The sole observer job_95b7330a0add completed with watch exit 1, no timeout and no source mutation. No second observer or duplicate download was created. .gitattributes keeps packet bytes unchanged, including Windows log line endings. Issued preparation/validation/inventory/intake scripts are retained without a claim that host-upload newline bytes were independently captured.

## Remaining gates

The coherent source/profile must pass its original source admission and one genuine Apple producer retry. Exact 51 package pins, original Modules/resources, scoped macro preparation, Heart provenance, public facade and mandatory gates remain unchanged. The isolated Participant/Space authority components are not merged into this producer repair.

No qualified simulator distribution, actual editor mounting, application persistence, physical-device build, production account/runtime bootstrap, annotation metadata registration, identity receipt, native writer or cross-app completion is claimed by this packet.
