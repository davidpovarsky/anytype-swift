# One actual custom canonical Type UI journey

Status: source and controller controls are ready; actual Apple compilation and the new UI journey are **NOT_RUN**. This supplements the existing Page journey. It does not claim that every possible Type schema has been exercised.

The new selector is:

`PinkhaAnyNativeUITests/NativeLaunchTests/testCustomCanonicalTypeTransitionPreservesNativeDocumentAcrossColdReopen`

## Native fixture and ownership

`NativeApp/Sources/NativeCustomTypeFixture.swift` belongs only to the downstream native executable and is completely inside `#if DEBUG`. It requires `--native-ui-tests`, one canonical UUID scope, the exact corresponding temporary directory and credential namespace, and exactly one explicit v1 fixture mode.

The prepare mode waits for the real application-owned account/Space/session. It accepts only the newly owned Space name for this test scope. It latches before suspension and creates an exclusive attempt marker before any native write. A failure, SwiftUI task re-entry, or process restart cannot silently retry preparation.

Exactly three counted, lease-authorized native writes create a Type, an editor part, and a synced string property. Native policy must report `eligible: true` and `canonicalEditorDataset: editor_blocks`; native definitions must match the returned Type/property IDs and unique scope-derived handles. The fixture never creates a document, changes a document's Type membership, or writes its body/property values.

On cold process launch the prepare flag is removed. The separate audit flag can only read the original bounded seed and attempt marker and perform GET requests. It checks the same account/Space and definitions, a new process and owner generation, and zero native fixture writes. Both modes check the actual owner and lease before publishing their bounded accessibility receipt.

## Actual UI contract

The unchanged normal UI helpers create a Page/document and one native text block. The new method chooses the distinct eligible custom Type through the real Properties picker, edits the new property through its real value sheet, and appends text in the existing editor. It checks exact UTF-8 bytes and the same native block before and after the Type change.

The method returns to the hierarchy to record the actual document ID, terminates the app, and reopens the same account/Space in a new iOS process. It verifies the same hierarchy ID, native block ID, exact appended body, Type name and property value. Original test and helper bodies remain byte-identical: removing only the new marked section reproduces SHA-256 `ffc938a140fbaa6bf3cc4ef30603f6d0fde08b30f82c08ae5f8e07859e917ec2` (Git blob `d1e9dbc8047565c5e5f827b2afa391095a5129eb`).

The native Type/property route signatures were checked against `internal/server/handlers_types.go`, including the strict `TypesCreateRequest`, `AddPropertyRequest`, `typeId`/`propId` response fields, and synced string scope. The part/policy calls match the existing `NativePropertyWorkflowTests.makeFixture`; that previously proved test is not selected again.

The test already imports CryptoKit. Apple's current primary documentation lists the typed `typeKey(_:modifierFlags:)` overload on [XCUIElement](https://developer.apple.com/documentation/xcuiautomation/xcuielement) and the [downArrow constant](https://developer.apple.com/documentation/xcuiautomation/xcuikeyboardkey/downarrow.md), with iOS/iPadOS availability in XCUIAutomation. Physical Command-Down success is still subject to the exact appended-body assertion; documentation is not execution proof.

## Same build, exact result

The `remaining-native-ui` workflow adds this method to its existing one-time build. The old full/default execution excludes the new method. The new execution stage is last, after entry 1, remaining 7, and Files 1, and uses `test-without-building` with the same products and owned simulator. It creates its own fresh account namespace within that simulator.

`verify_custom_type.py` freezes the app, UI runner, xctestrun, native consumer binding and source before the first UI stage. It requires unchanged bytes before and after the new stage and matching installed executable carriers. Acceptance requires the actual exact-one XCTest result on the owned iOS 27+ ARM64 destination as well as the original receipt. A printed receipt cannot replace a failing, skipped, extra, or missing XCTest result. It preserves separate receipts for the previous stages and does not relabel their results.

## Scope and provenance

All edited files are downstream native-app composition, UI acceptance, workflow, or controller files. There are no changes to the retained Heart app, native Go implementation, generated bindings, production Type picker, or conditional property writer. There is no new native binary build or additional App build in this change. Source-only controls and syntax parsing do not close the actual UI acceptance task.

The actual PinkhaAnyNativeApp.xcscheme has one Debug TestAction and exactly one non-skipped TestableReference: PinkhaAnyNativeUITests (A50000000000000000000002). The separate HostedTests targets are not part of that scheme. The runtime product gate verifies the emitted xctestrun against that selection.
