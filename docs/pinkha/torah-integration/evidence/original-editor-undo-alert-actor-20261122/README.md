# Original undo-alert actor contract repair

Frozen producer [45003378181](https://github.com/davidpovarsky/anytype-swift/actions/runs/45003378181), attempt 1, ran at 56d5d0b68d9d46b93ea31fdc69873d5f1d9ee793. Genuine framework compilation exited 65 without a timeout on 2026-11-22, 08:34:40.462705–08:48:38.618654 UTC. Its sole source-located error is EditorPageViewModel.swift:575:40: scheduleMutationTask(operation:) is MainActor-isolated but the undo alert supplied a synchronous nonisolated callback.

The full one-download artifact, hash/CRC proof, actual command, 221 passing source controls, source-before/after byte equality, exact original macro trust restoration and sole terminal observer are retained under failed-56d5. No separate binary consumer, native editor UI or framework distribution was qualified by that failed run. No unlocated corrupted-JSON driver diagnostic was observed.

## Exact source boundary

The complete original AlertModel changes only two function types: ButtonModel.action and undoAlertModel's undoAction parameter both retain @Sendable and add @MainActor. All callback bodies, alert labels/styles/buttons, imports and scheduling code remain identical. The original AlertsFactory is already MainActor-isolated and invokes the stored action directly from its UIAlertAction handler. The original EditorRouterProtocol is MainActor-isolated. The original shake callback must synchronously call scheduleMutationTask on the tap stack before asynchronous work can wait; no Task wrapping, delayed owner recapture, assumeIsolated, scheduler modification or new dispatcher is introduced.

The complete source callsite inventory, full original model/factory/router/view-model and original scheduler are retained. The only actual undoAlertModel caller is the original shake handler. Other records whose type names merely contain AlertModel are not treated as callers. The original object action protocol and both concrete undo layers confirm the unchanged async-throws Void signature.

## Focused actual validation

One bounded old-model compilation uses the unchanged original shake/scheduler projections and must reproduce the same attributed actor-isolation error. The complete changed source file is parsed once. The candidate then compiles and executes exactly two new genuine Swift Testing groups, with raw commands, PID/times, errors, XML, executable bytes and fixed input hashes retained. No existing cut, composition, Participant, Space, SQLite or native UI suite is replayed.

The new groups distinguish alert construction/cancel from the actual tap. A tap records the original scheduler's synchronous admission before the deferred undo service call; they also preserve exact object forwarding, the original rejection branch, weak view-model release and nil-owner legacy scheduling. The original AlertModel is complete apart from projecting its UIKit import to a small explicit Style enum. The complete shake method and actual four field types/MainActor declaration are retained; other ViewModel initialization and bodies are explicit projections. The generic scheduler/default owner/context/helper bodies are exact unchanged production bytes.

Owner/scheduled admission, native object service, router, document and localization/style values are explicit portable probes. They are not native authority or a replacement editor. The actual UIKit factory/router are retained and reviewed as source, not compiled against a fake UIKit and claimed as Apple proof. The next genuine framework build must accept the real UIKit handler and complete original module. Portable execution does not qualify native undo, original Owner/Invocation lifetimes, UIKit, full module behavior or a device runtime.

A preparation-only regular-expression typo stopped before control files/manifest were frozen or any compiler/test ran. Its complete error and caller recipe are retained as PREPARATION_FAILURE.json. The finite preparation continuation only completed the still-unexecuted fixture; this is distinct from the actual old-source compiler result and candidate test execution.

The exact original 51 dependency pins, macro preparation and resource trees remain unchanged. Separate production runtime/selected-Space audit and root-native permission/metadata/held-read integration do not enter this producer. Full genuine framework/external binary/resource/runtime acceptance and subsequent consumer acceptance remain required.
