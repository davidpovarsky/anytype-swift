import Foundation
@_spi(OriginalEditor) import ProtobufMessages

/// An owned historical response copied after this operation's original native
/// admissions have drained. No constructor accepts a caller-created response.
/// A nil response is unobserved history and does not prove that nothing wrote.
struct OriginalAnnotationSchemaCallHistory: Sendable {
    let response: Anytype_Rpc.Annotation.Schema.Register.Response?
    let copyError: String?

    fileprivate init(call: OriginalAnnotationSchemaRegistrationCall) {
        do {
            response = try call.copyObservedNativeResponse()
            copyError = nil
        } catch {
            response = nil
            copyError = String(describing: error)
        }
    }
}

@MainActor
extension EditorDocumentWriteSourceBinding {
    /// Uses the caller's actual original selected-source binding and opaque
    /// current subscription permissions. It creates no replacement lifetime,
    /// identity-is-current closure, document owner or write authorization.
    /// The original RPC error still escapes; onDrained separately retains any
    /// actual response even after native failure or late caller cancellation.
    func performOriginalAnnotationSchemaRegistration(
        expectedAccountID: String,
        spaceID: String,
        participant: OriginalParticipantEditPermission,
        spaceView: OriginalSpaceViewPermission,
        onDrained: @escaping @MainActor @Sendable (OriginalAnnotationSchemaCallHistory) -> Void
    ) async throws -> Anytype_Rpc.Annotation.Schema.Register.Response {
        let qualified = try requiringSpaceEditPermission(
            participant: participant, spaceView: spaceView, spaceId: spaceID
        )
        var request = Anytype_Rpc.Annotation.Schema.Register.Request()
        request.expectedAccountID = expectedAccountID
        request.spaceID = spaceID
        request.schemaProtocol = OriginalAnnotationNativeMetadata.protocolValue
        let call = ClientCommands.annotationSchemaRegister(request)
            .retainingOriginalAnnotationSchemaHistory()
        return try await qualified.performOperation(
            rpcNames: ["AnnotationSchemaRegister"],
            onDrained: { onDrained(OriginalAnnotationSchemaCallHistory(call: call)) },
            operation: { try await call.invoke() }
        )
    }
}
