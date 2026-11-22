import Foundation
import SwiftProtobuf

// Explicit disposable document values. These controls do not open an account,
// publish remotely, call Lib, mount an editor, or emulate a protobuf message.
private final class PublishingDocumentProbe: BaseDocumentProtocol, EditorDocumentWriteLifetimeProviding, Sendable {
    let objectId = "owned"
    let spaceId = "owned-space"
    let mode = DocumentMode.handling
    let isOpened = true, isLocked = false
    let editorWriteLifetime = EditorDocumentWriteLifetime()
    let permissions: ObjectPermissions = {
        var value = ObjectPermissions()
        value.canPublish = true
        value.canEditBlocks = true
        return value
    }()
}

private enum ExplicitTransportFailure: Error, Equatable { case refused }

@main
private struct PublishingStatusControls {
    typealias Status = Anytype_Rpc.Publishing.GetStatus.Response
    @MainActor private static var passed: [String] = []

    private static func absent() -> Status {
        .with { $0.error = .with { $0.code = .null; $0.description_p = "not found" } }
    }

    private static func present() -> Status {
        .with {
            $0.error = .init()
            $0.publish = .with {
                $0.spaceID = "owned-space"; $0.objectID = "owned"; $0.uri = "real-response-path"
            }
        }
    }

    @MainActor private static func owner() throws -> EditorDocumentWriteOwner {
        let document = PublishingDocumentProbe()
        return try .init(data: .init(objectId: document.objectId, spaceId: document.spaceId, mode: document.mode),
                         lifetimeDocument: document,
                         sourceBinding: .init(lifetime: .init(), accountLifetime: .init(), isCurrent: { true }))
    }

    // The request and response are actual generated messages. Only the effect
    // body is an explicit disposable GCD probe, not the real publishing service.
    private static func originalWrite() async throws {
        let request = Anytype_Rpc.Publishing.Remove.Request.with {
            $0.spaceID = "owned-space"; $0.objectID = "owned"
        }
        let _: Anytype_Rpc.Publishing.Remove.Response = try await invokeOriginalAdmissionProbe(
            messageName: "PublishingRemove", request: request, responsePolicy: .original
        ) { request in
            precondition(request.objectID == "owned" && request.spaceID == "owned-space")
            return .init()
        }
    }

    private static func strictStatus(
        name: String = "PublishingGetStatus",
        body: @escaping @Sendable (Anytype_Rpc.Publishing.GetStatus.Request) throws -> Status
    ) async throws -> Status? {
        let request = Anytype_Rpc.Publishing.GetStatus.Request.with {
            $0.spaceID = "owned-space"; $0.objectID = "owned"
        }
        let response: Status = try await invokeOriginalAdmissionProbe(
            messageName: name, request: request, responsePolicy: .publishingStatusAbsence, invokeTask: body
        )
        return isOriginalPublishingStatusAbsence(messageName: name, response: response) ? nil : response
    }

    @MainActor private static func save(_ owner: EditorDocumentWriteOwner) async throws {
        let value = try await owner.withExclusiveRead(
            contextId: "owned", spaceId: "owned-space", rpcNames: ["ObjectListExport"]
        ) { "explicit-export-result-probe" }
        precondition(value == "explicit-export-result-probe" && owner.isDrained)
    }

    @MainActor private static func saveMustFail(_ owner: EditorDocumentWriteOwner) async {
        do { try await save(owner); preconditionFailure("a failed native response lost the original write latch") }
        catch { precondition(error as? EditorDocumentWriteError == .rejected(.failedWrite)) }
    }

    @MainActor private static func runScheduled(
        _ owner: EditorDocumentWriteOwner,
        _ operation: @escaping @Sendable () async throws -> Void
    ) async throws {
        let scheduled = try owner.scheduleDocumentAction(contextId: "owned", requiredPermissions: [.publish])
        precondition(!owner.isDrained)
        try await scheduled.run {
            try await owner.performDocumentAction(contextId: "owned", requiredPermissions: [.publish], operation: operation)
        }
        // The real GCD completion may finish just after resuming its waiter.
        // The original exclusive save admission below must perform that drain;
        // an immediate MainActor snapshot is not a completion oracle.
    }

    @MainActor static func main() async throws {
        let exact = absent()
        precondition(isOriginalPublishingStatusAbsence(messageName: "PublishingGetStatus", response: exact))
        precondition(!exact.error.isNull)
        precondition(present().error.isNull)
        passed.append("exact original absent response is distinct from ordinary successful code-zero response")

        do {
            var value = exact; value.publish = present().publish
            precondition(!isOriginalPublishingStatusAbsence(messageName: "PublishingGetStatus", response: value))
            passed.append("an absent error with an actual publish payload is rejected")
        }
        do {
            var bytes = try exact.serializedData(); bytes.append(contentsOf: [0xa0, 0x06, 0x01])
            let value = try Status(serializedBytes: bytes)
            precondition(!value.unknownFields.data.isEmpty)
            precondition(!isOriginalPublishingStatusAbsence(messageName: "PublishingGetStatus", response: value))
            passed.append("real decoded unknown response fields cannot hide behind the absent sentinel")
        }
        do {
            var bytes = try exact.error.serializedData(); bytes.append(contentsOf: [0xa0, 0x06, 0x01])
            var value = exact; value.error = try Status.Error(serializedBytes: bytes)
            precondition(!value.error.unknownFields.data.isEmpty)
            precondition(!isOriginalPublishingStatusAbsence(messageName: "PublishingGetStatus", response: value))
            passed.append("real decoded unknown error fields cannot hide behind the absent sentinel")
        }
        do {
            precondition(!isOriginalPublishingStatusAbsence(messageName: "PublishingRemove", response: exact))
            precondition(!isOriginalPublishingStatusAbsence(messageName: "publishingGetStatus", response: exact))
            let other = Anytype_Rpc.Publishing.Remove.Response.with {
                $0.error = .with { $0.code = .null; $0.description_p = "not found" }
            }
            precondition(!isOriginalPublishingStatusAbsence(messageName: "PublishingGetStatus", response: other))
            passed.append("wrong RPC spelling or concrete response type receives no exception")
        }
        do {
            var value = exact; value.error.code = .unknownError
            precondition(!isOriginalPublishingStatusAbsence(messageName: "PublishingGetStatus", response: value))
            for text in ["Not found", "not found ", "rpc: not found", "access denied", ""] {
                value = exact; value.error.description_p = text
                precondition(!isOriginalPublishingStatusAbsence(messageName: "PublishingGetStatus", response: value))
            }
            passed.append("wrong code, prefixes, casing, whitespace and other descriptions are not absence")
        }
        do {
            let owner = try owner()
            try await runScheduled(owner) {
                try await originalWrite()
                do {
                    let _: Status = try await invokeOriginalAdmissionProbe(
                        messageName: "PublishingGetStatus", request: Anytype_Rpc.Publishing.GetStatus.Request(),
                        responsePolicy: .original
                    ) { _ in exact }
                    preconditionFailure("generic invoke must still throw the original native error")
                } catch let error as Status.Error {
                    precondition(error == exact.error)
                }
            }
            try await save(owner)
            passed.append("generic invoke preserves the exact thrown response error and handled absence does not poison save")
        }
        do {
            let owner = try owner()
            try await runScheduled(owner) {
                try await originalWrite()
                let result = try await strictStatus { request in
                    precondition(request.objectID == "owned" && request.spaceID == "owned-space")
                    return exact
                }
                precondition(result == nil)
            }
            try await save(owner)
            passed.append("registered successful write followed by exact absent status reaches original save admission")
        }
        do {
            let owner = try owner(), response = present()
            try await runScheduled(owner) {
                try await originalWrite()
                let result = try await strictStatus { _ in response }
                precondition(result == response)
            }
            try await save(owner)
            passed.append("ordinary successful present status retains actual payload and original save admission")
        }
        do {
            let owner = try owner()
            var response = exact; response.error.description_p = "access denied"
            let denied = response
            try await runScheduled(owner) {
                try await originalWrite()
                do {
                    _ = try await strictStatus { _ in denied }
                    preconditionFailure("non-absence code-zero error must not become nil")
                } catch let error as Status.Error { precondition(error == denied.error) }
            }
            await saveMustFail(owner)
            passed.append("caught code-zero access failure propagates exact error and keeps original failed-save latch")
        }
        do {
            let owner = try owner()
            try await runScheduled(owner) {
                try await originalWrite()
                do {
                    _ = try await strictStatus { _ in throw ExplicitTransportFailure.refused }
                    preconditionFailure("transport failure must escape")
                } catch { precondition(error as? ExplicitTransportFailure == .refused) }
            }
            await saveMustFail(owner)
            passed.append("a thrown transport-body failure still marks actual admission failed and blocks save")
        }
        do {
            let owner = try owner()
            try await runScheduled(owner) {
                try await originalWrite()
                do {
                    _ = try await strictStatus { _ in try Status(serializedBytes: Data([0x0a, 0x80])) }
                    preconditionFailure("real protobuf decoding failure must escape")
                } catch { precondition(!(error is Status.Error)) }
            }
            await saveMustFail(owner)
            passed.append("actual SwiftProtobuf malformed-byte decoding error keeps original failed-save latch")
        }
        do {
            let owner = try owner()
            var value = exact; value.publish = present().publish
            let ambiguous = value
            try await runScheduled(owner) {
                try await originalWrite()
                do {
                    _ = try await strictStatus { _ in ambiguous }
                    preconditionFailure("ambiguous absent payload must not become nil")
                } catch let error as Status.Error { precondition(error == ambiguous.error) }
            }
            await saveMustFail(owner)
            passed.append("ambiguous publish payload remains original error and keeps the failed-save latch")
        }
        do {
            let owner = try owner()
            try await runScheduled(owner) {
                try await originalWrite()
                do {
                    _ = try await strictStatus(name: "PublishingRemove") { _ in exact }
                    preconditionFailure("wrong named RPC must retain failure")
                } catch let error as Status.Error { precondition(error == exact.error) }
            }
            await saveMustFail(owner)
            passed.append("same sentinel on a different named RPC remains failed native work")
        }
        precondition(passed.count == 14)
        let report: [String: Any] = ["status": "PASS_NEW_PUBLISHING_RESPONSE_CONTROLS", "executed": passed.count,
            "passed": passed.count, "controls": passed, "native_lib_calls": 0, "publishing_network_calls": 0,
            "scope": "Real generated protobuf types and cached actual SwiftProtobuf; exact production classifier and GCD admission/result-policy blocks; unchanged actual Owner/lifetime/operation/binding with explicit document and effect inputs. Full Invocation logging/event/cancellation plumbing is not executed by these controls.",
            "apple_native": "NOT_RUN", "prior_suites_rerun": false]
        print(String(data: try JSONSerialization.data(withJSONObject: report, options: [.sortedKeys]), encoding: .utf8)!)
    }
}
