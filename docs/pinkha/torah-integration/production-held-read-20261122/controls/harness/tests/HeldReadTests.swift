import Foundation
import Testing
import SwiftProtobuf
import PinkhaKit
import Services
@testable import ProtobufMessages
@testable import OriginalHeldRead

private enum HeldReadFixtureError: Error {
    case missingUUID
    case missingAccountLifetime
    case unexpectedResult
}

private final class CallbackFailure: Error, Sendable {}

@MainActor
private final class CallbackState {
    var count = 0
    var effects = 0
    var mutationBodyCount = 0
    var sourceCurrent = true
    var bindingID: UUID?
    var signalled = false
    private var waiters: [CheckedContinuation<Void, Never>] = []

    func signal() {
        signalled = true
        let pending = waiters
        waiters.removeAll()
        for waiter in pending { waiter.resume() }
    }

    func wait() async {
        if signalled { return }
        await withCheckedContinuation { waiters.append($0) }
    }
}

@MainActor
private final class HeldReadFixture {
    let objectID = "held-original-object"
    let spaceID = "held-original-space"
    let accountID = "held-original-account"
    let source = EditorDocumentWriteLifetime()
    let manager = AccountManager()
    let basic = PortableBasicUserInfo()
    let state = CallbackState()
    let drained = CallbackState()
    let document: BaseDocument
    let session: PreparedEditorPageSession
    let adapter: OriginalAnnotationObjectReadback
    let driver: PortableObjectShowDriver
    let identity: TorahAnnotationNativeIdentity

    init(responses: [Anytype_Rpc.Object.Show.Response]? = nil, paused: Bool = false,
         retainCompletion: Bool = false, failure: (any Error)? = nil) throws {
        guard let uuid = UUID(uuidString: "ACB9B4E1-E209-4EBA-B4C1-F39D6F9A3FE7") else {
            throw HeldReadFixtureError.missingUUID
        }
        let scope = try TorahAnnotationNativeScope(
            destination: "held-original-destination", account: accountID, space: spaceID,
            namespace: "fixture.namespace", annotationUUID: uuid
        )
        identity = try TorahAnnotationNativeIdentity(scope: scope, objectID: objectID)
        var account = Anytype_Model_Account()
        account.id = accountID
        account.status.statusType = .active
        manager.account = try account.asModel()
        basic.usersId = accountID
        guard let accountLifetime = manager.editorWriteLifetime else {
            throw HeldReadFixtureError.missingAccountLifetime
        }
        document = BaseDocument(objectID: objectID, spaceID: spaceID)
        let state = state
        let drained = drained
        let sourceBinding = try EditorDocumentWriteSourceBinding(
            lifetime: source, accountLifetime: accountLifetime,
            isCurrent: { state.sourceCurrent }
        )
        session = try PreparedEditorPageSession(
            data: EditorPageObject(objectId: objectID, spaceId: spaceID, mode: .handling),
            document: document, sourceBinding: sourceBinding,
            onDrained: { drained.signal() }
        )
        Container.shared.install(manager: manager, basic: basic)
        adapter = try OriginalAnnotationObjectReadback.bindExistingOriginal(
            session: session, requestedIdentity: identity
        )
        let responses = try responses ?? [Self.response()]
        driver = PortableObjectShowDriver(
            responses: try responses.map { try $0.serializedData() },
            paused: paused, retainCompletion: retainCompletion, failure: failure
        )
    }

    static func response(text: String = "בראשית — opaque body 𐐷 e\u{301}") throws -> Anytype_Rpc.Object.Show.Response {
        var fields = Google_Protobuf_Struct()
        fields.fields["id"] = Google_Protobuf_Value(stringValue: "held-original-object")
        fields.fields["spaceId"] = Google_Protobuf_Value(stringValue: "held-original-space")
        fields.fields["type"] = Google_Protobuf_Value(listValue: .with {
            $0.values = [Google_Protobuf_Value(stringValue: "unqualified-native-type")]
        })
        fields.fields["opaqueSource"] = Google_Protobuf_Value(structValue: .with {
            $0.fields["untouched"] = Google_Protobuf_Value(stringValue: "source \u{0} value")
        })
        fields = try addingUnknown(fields)
        var block = Anytype_Model_Block()
        block.id = "original-block"
        block.text.text = text
        block.text.color = "red"
        block.childrenIds = ["nested-original-block"]
        block.fields.fields["opaque"] = Google_Protobuf_Value(boolValue: true)
        block = try addingUnknown(block)
        var view = Anytype_Model_ObjectView()
        view.rootID = "held-original-object"
        view.blocks = [block]
        view.details = [.with {
            $0.id = "held-original-object"
            $0.details = fields
            $0.subIds = ["linked-original-object"]
        }]
        view.history.undo = 7
        view.history.redo = 2
        view.blockParticipants = [.with {
            $0.blockID = "original-block"
            $0.participantID = "original-participant"
        }]
        view = try addingUnknown(view)
        var response = Anytype_Rpc.Object.Show.Response()
        response.objectView = view
        return try addingUnknown(response)
    }

    static func addingUnknown<Value: SwiftProtobuf.Message>(_ value: Value) throws -> Value {
        var wire = try value.serializedData()
        wire.append(contentsOf: [0xA0, 0x06, 0x07])
        return try Value(serializedBytes: wire)
    }

    func read<Value: Sendable>(
        _ consume: @MainActor @Sendable (OriginalAnnotationHeldReadObservation) throws -> Value
    ) async throws -> OriginalAnnotationHeldReadOutcome<Value> {
        try await PortableObjectShowContext.$driver.withValue(driver) {
            try await adapter.withFreshNativeObservation { [state] observation in
                state.count += 1
                return try consume(observation)
            }
        }
    }

    func legacyRead() async throws -> ObjectDetails {
        try await PortableObjectShowContext.$driver.withValue(driver) {
            try await adapter.readFreshDetails()
        }
    }
}

@MainActor
private func completed<Value: Sendable>(_ outcome: OriginalAnnotationHeldReadOutcome<Value>) throws -> Value {
    switch outcome {
    case .completed(let value):
        return value
    case .completedWithoutCurrentOwnership:
        Issue.record("Expected current-owner completion.")
        throw HeldReadFixtureError.unexpectedResult
    }
}

@MainActor
private func late<Value: Sendable>(_ outcome: OriginalAnnotationHeldReadOutcome<Value>) throws -> (Value, any Error) {
    switch outcome {
    case .completed:
        Issue.record("A late ownership failure must not appear as current-owner completion.")
        throw HeldReadFixtureError.unexpectedResult
    case let .completedWithoutCurrentOwnership(value, error):
        return (value, error)
    }
}

@MainActor
private func expectNativeRejection(
    _ response: Anytype_Rpc.Object.Show.Response,
    _ expected: OriginalAnnotationObjectReadbackError
) async throws {
    let fixture = try HeldReadFixture(responses: [response])
    do {
        let _: OriginalAnnotationHeldReadOutcome<Int> = try await fixture.read { _ in 7 }
        Issue.record("Invalid native response reached a completed result.")
    } catch {
        #expect(error as? OriginalAnnotationObjectReadbackError == expected)
    }
    #expect(fixture.state.count == 0)
    let records = await fixture.driver.recordedRequests()
    #expect(records.count == 1)
    #expect(fixture.session.owner.isDrained)
    #expect(!fixture.session.owner.isCapturing)
}

@MainActor
private func expectOwnerRejection(
    _ fixture: HeldReadFixture, reason: EditorDocumentWriteRejection, requests: Int
) async throws {
    do {
        let _: OriginalAnnotationHeldReadOutcome<Int> = try await fixture.read { _ in 7 }
        Issue.record("Invalid owner reached a completed result.")
    } catch {
        #expect(error as? EditorDocumentWriteError == .rejected(reason))
    }
    #expect(fixture.state.count == 0)
    let records = await fixture.driver.recordedRequests()
    #expect(records.count == requests)
}

@Suite(.serialized, .timeLimit(.minutes(1)))
@MainActor
struct OriginalHeldReadTests {
    @Test
    func testFreshBinaryViewAndRootPreservedInsideOriginalReadLineage() async throws {
        let response = try HeldReadFixture.response()
        let roundtrip = try Anytype_Rpc.Object.Show.Response(serializedBytes: response.serializedData())
        #expect(roundtrip == response)
        let fixture = try HeldReadFixture(responses: [roundtrip])
        let result = try await fixture.read { observation in
            #expect(fixture.session.owner.isCapturing)
            #expect(fixture.session.owner.pendingOperationCount == 1)
            let binding = try #require(InvocationDispatchContext.binding)
            fixture.state.bindingID = binding.contextIdentity
            #expect(observation.objectView == response.objectView)
            #expect(observation.rootDetails == response.objectView.details[0].details)
            #expect(observation.objectView.blocks[0].text.text == "בראשית — opaque body 𐐷 e\u{301}")
            #expect(observation.objectView.history.undo == 7)
            let value = try fixture.session.owner.performSynchronousOperation(
                contextId: fixture.objectID, spaceId: fixture.spaceID, requiresEditing: false
            ) {
                #expect(fixture.session.owner.isCapturing)
                #expect(fixture.session.owner.pendingOperationCount == 2)
                #expect(InvocationDispatchContext.binding != nil)
                return observation.rootDetails.fields["opaqueSource"]
            }
            return value
        }
        let value = try completed(result)
        #expect(value == response.objectView.details[0].details.fields["opaqueSource"])
        #expect(fixture.state.count == 1)
        let records = await fixture.driver.recordedRequests()
        let record = try #require(records.first)
        #expect(records.count == 1)
        #expect(record.bindingIdentity == fixture.state.bindingID)
        #expect(record.request.contextID == fixture.objectID)
        #expect(record.request.objectID == fixture.objectID)
        #expect(record.request.spaceID == fixture.spaceID)
        #expect(fixture.session.owner.isDrained)
        #expect(!fixture.session.owner.isCapturing)
        try fixture.session.owner.validateOwnership()
    }

    @Test
    func testLegacyFreshDetailsUsesSameStrictActualResponse() async throws {
        let response = try HeldReadFixture.response()
        let fixture = try HeldReadFixture(responses: [response])
        let details = try await fixture.legacyRead()
        #expect(details.id == fixture.objectID)
        #expect(details.values == response.objectView.details[0].details.fields)
        #expect(fixture.state.count == 0)
        let records = await fixture.driver.recordedRequests()
        #expect(records.count == 1)
        #expect(fixture.session.owner.isDrained)
        #expect(!fixture.session.owner.isCapturing)
    }

    @Test
    func testMalformedRootAndDetailsRefuseConsumer() async throws {
        let original = try HeldReadFixture.response()
        var cases: [Anytype_Rpc.Object.Show.Response] = []
        var value = original
        value.clearObjectView()
        cases.append(value)
        value = original
        value.objectView.rootID = "other-object"
        cases.append(value)
        value = original
        value.objectView.details = []
        cases.append(value)
        value = original
        value.objectView.details.append(original.objectView.details[0])
        cases.append(value)
        value = original
        value.objectView.details[0].id = "linked-only"
        cases.append(value)
        value = original
        value.objectView.details[0].clearDetails()
        cases.append(value)
        value = original
        value.objectView.details[0].details.fields.removeValue(forKey: "id")
        cases.append(value)
        value = original
        value.objectView.details[0].details.fields["id"] = Google_Protobuf_Value(numberValue: 7)
        cases.append(value)
        value = original
        value.objectView.details[0].details.fields["id"] = Google_Protobuf_Value(stringValue: "other-object")
        cases.append(value)
        for response in cases { try await expectNativeRejection(response, .wrongObject) }
    }

    @Test
    func testNativeSpaceRequiresExactStringScope() async throws {
        let original = try HeldReadFixture.response()
        var missing = original
        missing.objectView.details[0].details.fields.removeValue(forKey: "spaceId")
        try await expectNativeRejection(missing, .wrongSpace)
        for field in [Google_Protobuf_Value(stringValue: "other-space"),
                      Google_Protobuf_Value(stringValue: "held-original-Space"),
                      Google_Protobuf_Value(boolValue: true),
                      Google_Protobuf_Value()] {
            var response = original
            response.objectView.details[0].details.fields["spaceId"] = field
            try await expectNativeRejection(response, .wrongSpace)
        }
    }

    @Test
    func testNativeTypeKindsCountsAndIdentifiersRefuseConsumer() async throws {
        let original = try HeldReadFixture.response()
        var missing = original
        missing.objectView.details[0].details.fields.removeValue(forKey: "type")
        try await expectNativeRejection(missing, .malformedNativeType)
        let string = Google_Protobuf_Value(stringValue: "type")
        let fields: [Google_Protobuf_Value] = [
            Google_Protobuf_Value(stringValue: "type"),
            Google_Protobuf_Value(boolValue: true),
            Google_Protobuf_Value(listValue: .with { $0.values = [] }),
            Google_Protobuf_Value(listValue: .with { $0.values = [string, string] }),
            Google_Protobuf_Value(listValue: .with { $0.values = [Google_Protobuf_Value(numberValue: 1)] }),
            Google_Protobuf_Value(listValue: .with { $0.values = [Google_Protobuf_Value(stringValue: "")] }),
            Google_Protobuf_Value(listValue: .with { $0.values = [Google_Protobuf_Value(stringValue: "bad\u{0}type")] })
        ]
        for field in fields {
            var response = original
            response.objectView.details[0].details.fields["type"] = field
            try await expectNativeRejection(response, .malformedNativeType)
        }
    }

    @Test
    func testPresentStateKindsAndUnavailableValuesRefuseConsumer() async throws {
        let original = try HeldReadFixture.response()
        for key in ["isArchived", "isDeleted"] {
            for field in [Google_Protobuf_Value(stringValue: "false"),
                          Google_Protobuf_Value(numberValue: 0),
                          Google_Protobuf_Value(nullValue: .nullValue),
                          Google_Protobuf_Value()] {
                var response = original
                response.objectView.details[0].details.fields[key] = field
                try await expectNativeRejection(response, .malformedNativeState)
            }
            var response = original
            response.objectView.details[0].details.fields[key] = Google_Protobuf_Value(boolValue: true)
            try await expectNativeRejection(response, .unavailableObject)
        }
    }

    @Test
    func testLinkedRowsAndFalseStatesPreserveUnqualifiedNativeType() async throws {
        var response = try HeldReadFixture.response()
        response.objectView.details[0].details.fields["isArchived"] = Google_Protobuf_Value(boolValue: false)
        response.objectView.details[0].details.fields["isDeleted"] = Google_Protobuf_Value(boolValue: false)
        response.objectView.details.append(.with {
            $0.id = "linked-original-object"
            $0.details.fields["id"] = Google_Protobuf_Value(stringValue: "linked-original-object")
            $0.details.fields["arbitrary"] = Google_Protobuf_Value(boolValue: true)
        })
        let expected = response.objectView
        let fixture = try HeldReadFixture(responses: [response])
        let result = try await fixture.read { observation in
            #expect(observation.objectView == expected)
            #expect(observation.objectView.details.count == 2)
            #expect(observation.rootDetails.fields["id"]?.stringValue == fixture.objectID)
            return observation.rootDetails.fields["type"]
        }
        let value = try completed(result)
        #expect(value == expected.details[0].details.fields["type"])
        #expect(value?.listValue.values.first?.stringValue == "unqualified-native-type")
    }

    @Test
    func testOwnerRetiredBeforeReadNeverDispatches() async throws {
        let fixture = try HeldReadFixture()
        fixture.session.owner.retire()
        try await expectOwnerRejection(fixture, reason: .retired, requests: 0)
    }

    @Test
    func testAccountChangedBeforeReadNeverDispatches() async throws {
        let fixture = try HeldReadFixture()
        fixture.manager.account = .empty
        try await expectOwnerRejection(fixture, reason: .retired, requests: 0)
    }

    @Test
    func testSourceRetiredBeforeReadNeverDispatches() async throws {
        let fixture = try HeldReadFixture()
        fixture.source.markUnavailable()
        try await expectOwnerRejection(fixture, reason: .retired, requests: 0)
    }

    @Test
    func testDocumentChangedBeforeReadNeverDispatches() async throws {
        let fixture = try HeldReadFixture()
        fixture.document.replaceObjectID("replacement-object")
        try await expectOwnerRejection(fixture, reason: .documentChanged, requests: 0)
    }

    @Test
    func testCancelledBeforeReadNeverDispatches() async throws {
        let fixture = try HeldReadFixture()
        let task = Task { @MainActor in try await fixture.read { _ in 7 } }
        task.cancel()
        do {
            _ = try await task.value
            Issue.record("A cancelled read must not complete.")
        } catch {
            #expect(error is CancellationError)
        }
        #expect(fixture.state.count == 0)
        let records = await fixture.driver.recordedRequests()
        #expect(records.isEmpty)
    }

    @Test
    func testOwnerRetiredDuringRPCRefusesConsumer() async throws {
        let fixture = try HeldReadFixture(paused: true)
        let task = Task { @MainActor in try await fixture.read { _ in 7 } }
        await fixture.driver.began.wait()
        fixture.session.owner.retire()
        await fixture.driver.releaseResponse()
        do {
            _ = try await task.value
            Issue.record("Retirement during ObjectShow must refuse the consumer.")
        } catch {
            #expect(error as? EditorDocumentWriteError == .rejected(.retired))
        }
        #expect(fixture.state.count == 0)
        let records = await fixture.driver.recordedRequests()
        #expect(records.count == 1)
    }

    @Test
    func testAccountChangedDuringRPCRefusesConsumer() async throws {
        let fixture = try HeldReadFixture(paused: true)
        let task = Task { @MainActor in try await fixture.read { _ in 7 } }
        await fixture.driver.began.wait()
        fixture.manager.account = .empty
        await fixture.driver.releaseResponse()
        do {
            _ = try await task.value
            Issue.record("An account generation change must refuse the consumer.")
        } catch {
            #expect(error as? EditorDocumentWriteError == .rejected(.retired))
        }
        #expect(fixture.state.count == 0)
    }

    @Test
    func testSourceRetiredDuringRPCRefusesConsumer() async throws {
        let fixture = try HeldReadFixture(paused: true)
        let task = Task { @MainActor in try await fixture.read { _ in 7 } }
        await fixture.driver.began.wait()
        fixture.source.markUnavailable()
        await fixture.driver.releaseResponse()
        do {
            _ = try await task.value
            Issue.record("A source generation change must refuse the consumer.")
        } catch {
            #expect(error as? EditorDocumentWriteError == .rejected(.retired))
        }
        #expect(fixture.state.count == 0)
    }

    @Test
    func testCancelledDuringRPCRefusesConsumer() async throws {
        let fixture = try HeldReadFixture(paused: true)
        let task = Task { @MainActor in try await fixture.read { _ in 7 } }
        await fixture.driver.began.wait()
        task.cancel()
        await fixture.driver.releaseResponse()
        do {
            _ = try await task.value
            Issue.record("A cancelled suspended read must refuse the consumer.")
        } catch {
            #expect(error is CancellationError)
        }
        #expect(fixture.state.count == 0)
    }

    @Test
    func testRPCFailurePreservesOriginalErrorAndNeverCallsConsumer() async throws {
        let marker = CallbackFailure()
        let fixture = try HeldReadFixture(failure: marker)
        do {
            let _: OriginalAnnotationHeldReadOutcome<Int> = try await fixture.read { _ in 7 }
            Issue.record("The native boundary error must propagate.")
        } catch {
            #expect((error as? CallbackFailure) === marker)
        }
        #expect(fixture.state.count == 0)
        let records = await fixture.driver.recordedRequests()
        #expect(records.count == 1)
    }

    @Test
    func testCallbackErrorPreservedAfterEffectAndRetirement() async throws {
        let fixture = try HeldReadFixture()
        let marker = CallbackFailure()
        do {
            let _: OriginalAnnotationHeldReadOutcome<Int> = try await fixture.read { _ in
                fixture.state.effects += 1
                fixture.session.owner.retire()
                throw marker
            }
            Issue.record("A throwing consumer must preserve its error and uncertainty.")
        } catch {
            #expect((error as? CallbackFailure) === marker)
        }
        #expect(fixture.state.count == 1)
        #expect(fixture.state.effects == 1)
    }

    @Test
    func testCallbackValueRetainedWhenItRetiresOwner() async throws {
        let fixture = try HeldReadFixture()
        let result = try await fixture.read { _ in
            fixture.state.effects += 1
            fixture.session.owner.retire()
            return "callback-completed-only"
        }
        let (value, error) = try late(result)
        #expect(value == "callback-completed-only")
        #expect(error as? EditorDocumentWriteError == .rejected(.retired))
        #expect(fixture.state.count == 1)
        #expect(fixture.state.effects == 1)
    }

    @Test
    func testCallbackValueRetainedWhenItCancelsCurrentTask() async throws {
        let fixture = try HeldReadFixture()
        let task = Task { @MainActor in
            try await fixture.read { _ in
                fixture.state.effects += 1
                withUnsafeCurrentTask { $0?.cancel() }
                return 73
            }
        }
        let (value, error) = try late(try await task.value)
        #expect(value == 73)
        #expect(error is CancellationError)
        #expect(fixture.state.count == 1)
        #expect(fixture.state.effects == 1)
    }

    @Test
    func testReturnedValueSurvivesRetirementWithNativeCompletionPending() async throws {
        let fixture = try HeldReadFixture(retainCompletion: true)
        let task = Task { @MainActor in
            try await fixture.read { _ in
                fixture.state.signal()
                return "observed-value"
            }
        }
        await fixture.state.wait()
        #expect(fixture.session.owner.isCapturing)
        #expect(fixture.session.owner.pendingOperationCount == 1)
        let retained = await fixture.driver.retainedCompletionCount()
        #expect(retained == 1)
        fixture.session.owner.retire()
        let (value, error) = try late(try await task.value)
        #expect(value == "observed-value")
        let ownerError = try #require(error as? EditorDocumentWriteError)
        switch ownerError {
        case .rejected(.retired), .completedWithoutOwnership(.retired): break
        default: Issue.record("The exact observed late rejection must be retirement.")
        }
        #expect(fixture.session.owner.isCapturing)
        #expect(fixture.session.owner.pendingOperationCount == 1)
        await fixture.driver.finishRetainedCompletions()
        await fixture.drained.wait()
        #expect(fixture.session.owner.isDrained)
        #expect(!fixture.session.owner.isCapturing)
    }

    @Test
    func testReturnedValueSurvivesCancellationWithNativeCompletionPending() async throws {
        let fixture = try HeldReadFixture(retainCompletion: true)
        let task = Task { @MainActor in
            try await fixture.read { _ in
                fixture.state.signal()
                return 991
            }
        }
        await fixture.state.wait()
        #expect(fixture.session.owner.isCapturing)
        #expect(fixture.session.owner.pendingOperationCount == 1)
        task.cancel()
        let (value, error) = try late(try await task.value)
        #expect(value == 991)
        if let ownerError = error as? EditorDocumentWriteError {
            #expect(ownerError == .completedWithoutOwnership(.cancelled))
        } else {
            #expect(error is CancellationError)
        }
        #expect(fixture.session.owner.isCapturing)
        #expect(fixture.session.owner.pendingOperationCount == 1)
        fixture.session.owner.retire()
        await fixture.driver.finishRetainedCompletions()
        await fixture.drained.wait()
        #expect(fixture.session.owner.isDrained)
        #expect(!fixture.session.owner.isCapturing)
    }

    @Test
    func testDefaultMutationChildRejectedInsideHeldRead() async throws {
        let fixture = try HeldReadFixture()
        let result = try await fixture.read { _ in
            do {
                _ = try fixture.session.owner.performSynchronousOperation {
                    fixture.state.mutationBodyCount += 1
                    return 7
                }
                Issue.record("A read lineage must not upgrade to mutation.")
            } catch {
                #expect(error as? EditorDocumentWriteError == .rejected(.unqualifiedDispatch))
            }
            return "consumer-finished-with-failed-write"
        }
        let (value, error) = try late(result)
        #expect(value == "consumer-finished-with-failed-write")
        #expect(error as? EditorDocumentWriteError == .rejected(.failedWrite))
        #expect(fixture.state.mutationBodyCount == 0)
        #expect(fixture.state.count == 1)
    }

    @Test
    func testNestedExclusiveReadRefusedWithoutDroppingOuterBarrier() async throws {
        let fixture = try HeldReadFixture()
        let result = try await fixture.session.owner.withExclusiveRead(
            contextId: fixture.objectID, spaceId: fixture.spaceID, rpcNames: ["ObjectShow"]
        ) {
            do {
                _ = try await fixture.read { _ in 7 }
                Issue.record("A nested exclusive read must not open another barrier.")
            } catch {
                #expect(error as? EditorDocumentWriteError == .rejected(.captureInProgress))
            }
            return true
        }
        #expect(result)
        #expect(fixture.state.count == 0)
        let records = await fixture.driver.recordedRequests()
        #expect(records.isEmpty)
        #expect(fixture.session.owner.isDrained)
        #expect(!fixture.session.owner.isCapturing)
    }

    @Test
    func testChangedBasicAccountScopeRefusesRead() async throws {
        let fixture = try HeldReadFixture()
        fixture.basic.usersId = "another-account"
        do {
            let _: OriginalAnnotationHeldReadOutcome<Int> = try await fixture.read { _ in 7 }
            Issue.record("A mismatched original basic-user account must refuse the read.")
        } catch {
            #expect(error as? OriginalAnnotationObjectReadbackError == .wrongAccount)
        }
        #expect(fixture.state.count == 0)
        let records = await fixture.driver.recordedRequests()
        #expect(records.isEmpty)
    }

    @Test
    func testSecondReadObservesSecondActualResponseWithoutCache() async throws {
        let first = try HeldReadFixture.response(text: "first native response")
        let second = try HeldReadFixture.response(text: "changed native response")
        let fixture = try HeldReadFixture(responses: [first, second])
        let firstResult = try completed(try await fixture.read { $0.objectView.blocks[0].text.text })
        let secondResult = try completed(try await fixture.read { $0.objectView.blocks[0].text.text })
        #expect(firstResult == "first native response")
        #expect(secondResult == "changed native response")
        #expect(fixture.state.count == 2)
        let records = await fixture.driver.recordedRequests()
        #expect(records.count == 2)
        #expect(records[0].bindingIdentity != records[1].bindingIdentity)
        #expect(fixture.session.owner.isDrained)
        #expect(!fixture.session.owner.isCapturing)
    }
}
