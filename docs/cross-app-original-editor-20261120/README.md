# Original Anytype editor: prepared-document and service seams

## Result and scope

Source commit: **9dd379b5b88af9f8baa955c0828967f1d9021c49**, based on reviewed original source **a05088b98844bba30f90b794effb8cf579e2ef08**. This is the first source tranche for [CROSS-APP task 1220545194715722](https://app.asana.com/1/1219597879016953/task/1220545194715722).

Actual Windows validation: **29/29 Foundation controls**, plus **8/8 full-file syntax parses**, with zero warnings or errors. The portable fixture compiles the whole new identity validator, whole original text-service forwarding implementation and protocol, original value models, new dependency bundle, and actual BlockActionService construction prefix. UIKit, the complete editor assembly and native block-action methods are not compiled or executed by that fixture.

There are **11 new Swift Testing declarations** in the original AnytypeTests target. Apple typechecking and execution are **NOT_RUN**. The original editor has not yet been mounted in Maktabah. This tranche does not establish annotation persistence, complete writer isolation, Native input, or task completion.

## Source changes

1. EditorPageModuleAssembly retains its normal entry and adds a prepared-document entry. The new entry checks exact object ID, Space ID, document mode and actual open state synchronously on MainActor before constructing editor state. It does not call OpenedDocumentsProvider or initiate another open. Empty/whitespace IDs, another object/Space/mode/version and a closed document are rejected.
2. Both entries use the same controller/VM construction body. Except for the document-resolution expression, that body is identical to the baseline. The private downstream assembly remains identical.
3. EditorPageView adds a lazy StateObject initializer for explicitly prepared original state. Its original initializer and entire body remain identical.
4. BlockActionService receives its seven existing services through an immutable instance bundle. The default bundle resolves the same original Container factories. Every original action method, focus registration, split ordering, event send, conversion and upload body is byte-identical.
5. TextServiceHandler can receive its original TextServiceProtocol instance explicitly. The default resolves the original factory. Every text method is identical, including the rule that split does not publish a local render event before the caller records focus.

No original renderer, Heart runtime, generated protobuf, Services package, binary pin, signing, account, Space or Xcode project changed. The alternative AnyNativeEditorController is not used.

## Validation boundaries and retained attempts

**Attempt1:** the fixture added a checked Sendable conformance for DocumentMode in another source file, which Swift6 rejected. No test ran.

**Attempt2:** 29 controls passed after that test-only conformance moved beside the copied enum. Root review rejected using this attempt as qualification, since a fixture-only conformance could conceal an actual isolation error. Its successful output remains retained and explicitly superseded.

**Attempt3:** the qualified Foundation attempt. No conformance is added to the original or compiled DocumentMode. Its compiled bytes equal the canonical original Git blob. The immutable DocumentProbe uses the same unchecked Sendable document boundary declared by original BaseDocument and MockBaseDocument. All probe fields are immutable and lifecycle records are actor-owned. This explicit double does not establish thread safety of real BaseDocument or UIKit.

SENDABLE_BOUNDARY_REVIEW records the original declarations and hashes. Neither the validator nor prepared assembly creates new stored mode state or asynchronous mode transfer; both are synchronous on MainActor. A separate reviewer confirmed this. The original pinned SwiftProtobuf Enum protocol requires Sendable, covering original generated SplitMode in the new Apple test records; PROVENANCE includes the immutable revision/source URL.

The controls cover identity/version/closed-state rejection without lifecycle calls; Unicode text and mark payload forwarding; forced text; UTF16 split ranges/results; no premature split publication; checked/merge/icon parameters; errors and cancellation; two separate injected service instances; absence of native fallback on those injected paths; seven constructor identities; and unchanged default factories. Protobuf/value/event/Factory boundaries are declared doubles. Rich-text formatting semantics, CRDT behavior, durability and complete editor UI remain unproven.

The Apple test files moved without byte changes into existing canonical **AnytypeTests/Markdown** and were explicitly indexed with that exact casing. The repository also contains AnyTypeTests paths which alias on Windows. The original synchronized Xcode group names AnytypeTests; no target exception excludes the new files. Syntax receipts retain pre-relocation names, with identical-byte mapping in TEST_TARGET_PATHS.

## Remaining integration

This API is not yet an annotation editor adapter. The prepared entry still runs the original native service graph. Writers remain in EditorPageViewModel, EditorPageBlocksStateManager, BlockViewModelBuilder, BlockActionHandler, UndoRedoViewModel and nested router/header/table/media/paste modules. Passing one custom text/block service cannot qualify complete isolation.

The next tranche must propagate original document-owned mutation context through all reachable writers, preserve focus/event/undo ordering, and prevent writes to another document or Space. Annotation UUID and structured body stay authoritative; expansion must not promote to Document. Existing Maktabah envelope/ledger work must be reused.

The future host must bind SwiftUI identity/lifetime to the retained document/session. Replacing the prepared-state argument under an unchanged StateObject identity intentionally does not recreate the editor. Recreating it on every text edit is also incorrect.

Apple validation must then compile the complete original editor with its real model/resource/Services/runtime closure, mount it inside Maktabah, edit two real blocks through native controls, verify unchanged annotation identity/type, and reopen/relaunch against durable original storage. No such operation is automatically enabled by this branch.

## Reproduction and evidence

Run Scripts/CI/run-original-editor-boundary.py with --swiftc pointing to actual swiftc and --output pointing to a new owned output directory. It requires 29 unique passing controls and checks preservation before compilation. PreparedEditorPageDocumentTests and TextServiceHandlerInjectionTests are the new existing-target suites; existing focused CI filters do not silently select them.

RESULT records scoped outcomes. RAW_FILES binds logs, JSON, compiled-source projections and exact executed fixture bytes by SHA256. PRESERVED_INPUTS proves unchanged original runtime/model/project/resource objects. PROVENANCE records fresh Asana criteria, exact upstream/fork comparisons, pinned SwiftProtobuf source and independent review. No workflow was dispatched.
