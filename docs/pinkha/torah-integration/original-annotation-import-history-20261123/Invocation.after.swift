import Foundation
import Combine
import SwiftProtobuf

// ORIGINAL_PUBLISHING_STATUS_ABSENCE_BEGIN
// The pinned original publishing service uses this one exact response for an
// unpublished object. Code zero alone also carries transport/server failures.
// Keep this a closed concrete-response rule, never a caller-provided exemption.
private func isOriginalPublishingStatusAbsence<Response>(
    messageName: String, response: Response
) -> Bool {
    guard messageName == "PublishingGetStatus",
          let status = response as? Anytype_Rpc.Publishing.GetStatus.Response else { return false }
    return status.hasError && status.error.code == .null
        && status.error.description_p == "not found" && !status.hasPublish
        && status.unknownFields.data.isEmpty && status.error.unknownFields.data.isEmpty
}
// ORIGINAL_PUBLISHING_STATUS_ABSENCE_END

private enum InvocationResponsePolicy: Sendable, Equatable {
    case original
    case publishingStatusAbsence
}

public struct Invocation<Request, Response>: Sendable where Request: Message & Sendable,
                                                  Response: ResultWithError & Message & Sendable {
    
    private let messageName: String
    private let request: Request
    private let invokeTask: @Sendable (Request) throws -> Response
    private let nativeResponseObservation: (@Sendable (Response) -> Void)?
    
    private init(
        messageName: String, request: Request,
        invokeTask: @escaping @Sendable (Request) throws -> Response,
        nativeResponseObservation: (@Sendable (Response) -> Void)?
    ) {
        self.messageName = messageName
        self.request = request
        self.invokeTask = invokeTask
        self.nativeResponseObservation = nativeResponseObservation
    }

    init(messageName: String, request: Request, invokeTask: @escaping @Sendable (Request) throws -> Response) {
        self.init(messageName: messageName, request: request, invokeTask: invokeTask,
                  nativeResponseObservation: nil)
    }
    
    @discardableResult
    public func invoke(
        requestMask: (@Sendable (inout Request) -> Void)? = nil,
        responseMask: (@Sendable (inout Response) -> Void)? = nil,
        qos: DispatchQoS.QoSClass = .default,
        file: StaticString = #file,
        function: String = #function,
        line: UInt = #line,
        ignoreLogErrors: Response.Error.ErrorCode...
    ) async throws -> Response {
        try await invokeResponse(
            requestMask: requestMask, responseMask: responseMask, qos: qos,
            file: file, function: function, line: line,
            ignoreLogErrors: ignoreLogErrors, responsePolicy: .original
        )
    }

    private func invokeResponse(
        requestMask: (@Sendable (inout Request) -> Void)?,
        responseMask: (@Sendable (inout Response) -> Void)?,
        qos: DispatchQoS.QoSClass,
        file: StaticString, function: String, line: UInt,
        ignoreLogErrors: [Response.Error.ErrorCode],
        responsePolicy: InvocationResponsePolicy
    ) async throws -> Response {
        let dispatchBinding = InvocationDispatchContext.binding
        do {
            return try await withUncancellableHandler {
                try await internalInvoke(requestMask: requestMask, responseMask: responseMask, qos: qos,
                                         dispatchBinding: dispatchBinding, responsePolicy: responsePolicy)
            }
        } catch let error as CancellationError {
            // Ignore try Task.checkCancellation()
            throw error
        } catch let error as Response.Error where ignoreLogErrors.map(\.rawValue).contains(error.code.rawValue) {
            // Ignore some specific errors
            throw error
        } catch {
            InvocationSettings.handler?.assertationHandler(message: error.localizedDescription, domain: "Middle.\(messageName)", info: [:], file: file, function: function, line: line)
            throw error
        }
    }
    
    // MARK: - Private
    
    private func internalInvoke(
        requestMask: ((inout Request) -> Void)?,
        responseMask: ((inout Response) -> Void)?,
        qos: DispatchQoS.QoSClass,
        dispatchBinding: InvocationDispatchBinding?,
        responsePolicy: InvocationResponsePolicy
    ) async throws -> Response {
        
        let result: Response
        
        let logEnabled = InvocationSettings.handler?.isLogEnabled ?? false
        let requestId = logEnabled ? await RequestIdStorage.shared.createId() : 0

        if logEnabled {
            var requestForLog = request
            requestMask?(&requestForLog)
            log(message: messageName, requestId: requestId, data: requestForLog)
        }
        
        try Task.checkCancellation()
        let dispatchPermit = try await dispatchBinding?.prepare(messageName: messageName)
        
        do {
            result = try await withCheckedThrowingContinuation { (cont: CheckedContinuation<Response, Error>) in
                DispatchQueue.global(qos: qos).async {
                    do {
                        let completion = try dispatchPermit?.begin()
                        var succeeded = false
                        defer {
                            if !succeeded { completion?.markFailed() }
                            completion?.finish()
                        }
                        let response = try invokeTask(request)
                        nativeResponseObservation?(response)
                        succeeded = response.error.isNull
                            || isOriginalPublishingStatusAbsence(messageName: messageName, response: response)
                        cont.resume(returning: response)
                    } catch {
                        cont.resume(throwing: error)
                    }
                }
            }
        } catch {
            log(message: messageName, requestId: requestId, data: nil, error: error)
            throw error
        }
        
        if logEnabled {
            var resultForLog = result
            responseMask?(&resultForLog)
            let errorForLog = result.error.isNull ? nil : result.error
            log(message: messageName, requestId: requestId, data: resultForLog, error: errorForLog)
        }
        
        if !result.error.isNull {
            guard responsePolicy == .publishingStatusAbsence,
                  isOriginalPublishingStatusAbsence(messageName: messageName, response: result) else {
                // Generic invoke keeps throwing the exact original error,
                // including the expected absence consumed by legacy callers.
                throw result.error
            }
        }
        
        if result.hasEvent {
            if let dispatchBinding {
                await InvocationDispatchContext.$binding.withValue(dispatchBinding.bindingForCommittedEvents()) {
                    await InvocationSettings.handler?.eventHandler(event: result.event)
                }
            } else {
                await InvocationSettings.handler?.eventHandler(event: result.event)
            }
        }
        
        try Task.checkCancellation()
        
        return result
    }
    
    private func log(message: String, requestId: Int, data: Request?) {
        guard let handler = InvocationSettings.handler, handler.isLogEnabled else { return }
        let message = InvocationMessage(
            name: "\(message)-Request-\(requestId)",
            requestJsonData: nil,
            responseJsonData: try? data?.jsonUTF8Data(),
            responseError: nil
        )
        handler.logHandler(message: message)
    }

    private func log(message: String, requestId: Int, data: Response?, error: Error?) {
        guard let handler = InvocationSettings.handler, handler.isLogEnabled else { return }

        let name: String
        if let data, !data.event.messages.isEmpty {
            let messageNames = (try? data.event.jsonUTF8Data())?.parseMessages() ?? ""
            name = "\(message)-Events:\(messageNames)"
        } else {
            name = message
        }
        
        let message = InvocationMessage(
            name: "\(name)-Response-\(requestId)",
            requestJsonData: nil,
            responseJsonData: try? data?.jsonUTF8Data(),
            responseError: error
        )
        handler.logHandler(message: message)
    }
}

public extension Invocation where Request == Anytype_Rpc.Publishing.GetStatus.Request,
                                  Response == Anytype_Rpc.Publishing.GetStatus.Response {
    /// Exact original GetStatus response policy for source-owned callers. Uses
    /// the same request, native invocation, cancellation and dispatch admission.
    /// A genuine absent result becomes nil; every other original error escapes.
    func invokePublishingGetStatus(
        file: StaticString = #file, function: String = #function, line: UInt = #line
    ) async throws -> Response? {
        let response = try await invokeResponse(
            requestMask: nil, responseMask: nil, qos: .default,
            file: file, function: function, line: line,
            ignoreLogErrors: [.badInput, .noSuchObject, .noSuchSpace, .null],
            responsePolicy: .publishingStatusAbsence
        )
        return isOriginalPublishingStatusAbsence(messageName: messageName, response: response)
            ? nil : response
    }
}

// This is a closed history copyout for the one generated schema RPC. Ordinary
// Invocation callers have no response observer, and failed native responses
// continue through the original error decoding and admission-failure path.
fileprivate final class OriginalAnnotationSchemaResponseHistory: @unchecked Sendable {
    private enum State {
        case unobserved
        case copied(Data)
        case copyFailed(String)
    }

    private let lock = NSLock()
    private var invoked = false
    private var state = State.unobserved

    func beginInvocation() throws {
        lock.lock()
        defer { lock.unlock() }
        guard !invoked else {
            throw OriginalAnnotationSchemaHistoryError.callAlreadyInvoked
        }
        invoked = true
    }

    // Runs synchronously on the original RPC queue before completion.finish.
    // Serializing the complete response retains actual error and phase fields,
    // unknown fields included, without giving a caller mutable native storage.
    func receive(_ response: Anytype_Rpc.Annotation.Schema.Register.Response) {
        let captured: State
        do {
            captured = .copied(try response.serializedData())
        } catch {
            captured = .copyFailed(String(describing: error))
        }
        lock.lock()
        defer { lock.unlock() }
        state = captured
    }

    func copyResponse() throws -> Anytype_Rpc.Annotation.Schema.Register.Response? {
        lock.lock()
        let captured = state
        lock.unlock()
        switch captured {
        case .unobserved:
            return nil
        case .copied(let bytes):
            return try Anytype_Rpc.Annotation.Schema.Register.Response(serializedBytes: bytes)
        case .copyFailed(let reason):
            throw OriginalAnnotationSchemaHistoryError.copyFailed(reason)
        }
    }
}

@_spi(OriginalEditor)
public enum OriginalAnnotationSchemaHistoryError: Error, Sendable {
    case callAlreadyInvoked
    case copyFailed(String)
}

/// A single original native invocation and its copied historical response.
/// This owns no selected-Space/account permission or lifecycle lease. Original
/// composition must retain this call through SourceBinding.performOperation's
/// onDrained callback. An early nil copy means unobserved, never no native write.
@_spi(OriginalEditor)
public final class OriginalAnnotationSchemaRegistrationCall: Sendable {
    private let invocation: Invocation<Anytype_Rpc.Annotation.Schema.Register.Request,
                                       Anytype_Rpc.Annotation.Schema.Register.Response>
    private let history: OriginalAnnotationSchemaResponseHistory

    fileprivate init(
        invocation: Invocation<Anytype_Rpc.Annotation.Schema.Register.Request,
                               Anytype_Rpc.Annotation.Schema.Register.Response>,
        history: OriginalAnnotationSchemaResponseHistory
    ) {
        self.invocation = invocation
        self.history = history
    }

    /// Same original native error/cancellation behavior as Invocation.invoke.
    /// A failed caller await does not discard a later admitted native response.
    public func invoke() async throws -> Anytype_Rpc.Annotation.Schema.Register.Response {
        try history.beginInvocation()
        return try await invocation.invoke()
    }

    /// Returns a new decoded value copy of the response actually received. This
    /// getter does not assert drain, current account, schema readiness or ACK.
    public func copyObservedNativeResponse() throws -> Anytype_Rpc.Annotation.Schema.Register.Response? {
        try history.copyResponse()
    }
}

extension Invocation where Request == Anytype_Rpc.Annotation.Schema.Register.Request,
                           Response == Anytype_Rpc.Annotation.Schema.Register.Response {
    /// The only entry to the private response copyout. No generic public
    /// callback, native-error exemption, or caller-created response is accepted.
    @_spi(OriginalEditor)
    public func retainingOriginalAnnotationSchemaHistory() -> OriginalAnnotationSchemaRegistrationCall {
        let history = OriginalAnnotationSchemaResponseHistory()
        let observed = Self(
            messageName: messageName, request: request, invokeTask: invokeTask,
            nativeResponseObservation: { response in history.receive(response) }
        )
        return OriginalAnnotationSchemaRegistrationCall(invocation: observed, history: history)
    }
}

// ORIGINAL_ANNOTATION_IMPORT_HISTORY_BEGIN
// Closed history copyout for the two generated annotation import commands.
// All original invocation, error, admission and completion behavior above stays
// unchanged. These records are historical data, never native or Host authority.
fileprivate enum OriginalAnnotationImportHistoryPolicy {
    static let maximumResponseBytes = 2 * 1_024 * 1_024
}

@_spi(OriginalEditor)
public enum OriginalAnnotationImportHistoryError: Error, Sendable, Equatable {
    case callAlreadyInvoked
    case copyFailed
    case responseTooLarge
    case duplicateNativeResponse
}

fileprivate final class OriginalAnnotationImportResponseHistory<Response: Message & Sendable>: @unchecked Sendable {
    private enum State {
        case unobserved
        case copied(Data)
        case failed(OriginalAnnotationImportHistoryError)
    }

    private let lock = NSLock()
    private var invoked = false
    private var state = State.unobserved

    func beginInvocation() throws {
        lock.lock()
        defer { lock.unlock() }
        guard !invoked else {
            throw OriginalAnnotationImportHistoryError.callAlreadyInvoked
        }
        invoked = true
    }

    // Called only by the unchanged synchronous native response observation,
    // before Invocation's actual completion.finish. Retain the whole generated
    // response, including native errors and unknown fields, after early waiter
    // cancellation as well. The native endpoint independently bounds its output.
    func receive(_ response: Response) {
        let captured: State
        do {
            let bytes = try response.serializedData()
            captured = bytes.count <= OriginalAnnotationImportHistoryPolicy.maximumResponseBytes
                ? .copied(bytes) : .failed(.responseTooLarge)
        } catch {
            captured = .failed(.copyFailed)
        }
        lock.lock()
        defer { lock.unlock() }
        guard case .unobserved = state else {
            state = .failed(.duplicateNativeResponse)
            return
        }
        state = captured
    }

    func copyResponse() throws -> Response? {
        lock.lock()
        let captured = state
        lock.unlock()
        switch captured {
        case .unobserved:
            return nil
        case .copied(let bytes):
            do {
                return try Response(serializedBytes: bytes)
            } catch {
                throw OriginalAnnotationImportHistoryError.copyFailed
            }
        case .failed(let reason):
            throw reason
        }
    }
}

/// One generated native Import and its complete copied historical response.
/// A caller must retain this same call through the original source operation's
/// onDrained boundary. A nil history is unobserved; it is never proof of no
/// registration, native effects, cancellation, completion or retry permission.
@_spi(OriginalEditor)
public final class OriginalAnnotationImportCall: Sendable {
    private let invocation: Invocation<Anytype_Rpc.Annotation.Import.Request,
                                       Anytype_Rpc.Annotation.Import.Response>
    private let history: OriginalAnnotationImportResponseHistory<Anytype_Rpc.Annotation.Import.Response>

    fileprivate init(
        invocation: Invocation<Anytype_Rpc.Annotation.Import.Request,
                               Anytype_Rpc.Annotation.Import.Response>,
        history: OriginalAnnotationImportResponseHistory<Anytype_Rpc.Annotation.Import.Response>
    ) {
        self.invocation = invocation
        self.history = history
    }

    /// Native errors still throw and still mark the actual admission failed.
    /// Only the two log copies are emptied; the unchanged native invocation and
    /// the private historical observer receive the complete original messages.
    public func invoke() async throws -> Anytype_Rpc.Annotation.Import.Response {
        try history.beginInvocation()
        return try await invocation.invoke(
            requestMask: { $0 = Anytype_Rpc.Annotation.Import.Request() },
            responseMask: { $0 = Anytype_Rpc.Annotation.Import.Response() }
        )
    }

    public func copyObservedNativeResponse() throws -> Anytype_Rpc.Annotation.Import.Response? {
        try history.copyResponse()
    }
}

/// One cancellation-only generated call. Its response does not replace the
/// original Import history or drain. In particular NOT_OBSERVED is not evidence
/// that a pending Import cannot later register. There is no retry loop here.
@_spi(OriginalEditor)
public final class OriginalAnnotationImportCancellationCall: Sendable {
    private let invocation: Invocation<Anytype_Rpc.Annotation.Import.Cancel.Request,
                                       Anytype_Rpc.Annotation.Import.Cancel.Response>
    private let history: OriginalAnnotationImportResponseHistory<Anytype_Rpc.Annotation.Import.Cancel.Response>

    fileprivate init(
        invocation: Invocation<Anytype_Rpc.Annotation.Import.Cancel.Request,
                               Anytype_Rpc.Annotation.Import.Cancel.Response>,
        history: OriginalAnnotationImportResponseHistory<Anytype_Rpc.Annotation.Import.Cancel.Response>
    ) {
        self.invocation = invocation
        self.history = history
    }

    public func invoke() async throws -> Anytype_Rpc.Annotation.Import.Cancel.Response {
        try history.beginInvocation()
        return try await invocation.invoke(
            requestMask: { $0 = Anytype_Rpc.Annotation.Import.Cancel.Request() },
            responseMask: { $0 = Anytype_Rpc.Annotation.Import.Cancel.Response() }
        )
    }

    public func copyObservedNativeResponse() throws -> Anytype_Rpc.Annotation.Import.Cancel.Response? {
        try history.copyResponse()
    }
}

extension Invocation where Request == Anytype_Rpc.Annotation.Import.Request,
                           Response == Anytype_Rpc.Annotation.Import.Response {
    /// The exact concrete specialization is the only source of this call.
    /// No public generic observer or caller-created response is accepted.
    @_spi(OriginalEditor)
    public func retainingOriginalAnnotationImportHistory() -> OriginalAnnotationImportCall {
        let history = OriginalAnnotationImportResponseHistory<Response>()
        let observed = Self(
            messageName: messageName, request: request, invokeTask: invokeTask,
            nativeResponseObservation: { response in history.receive(response) }
        )
        return OriginalAnnotationImportCall(invocation: observed, history: history)
    }
}

extension Invocation where Request == Anytype_Rpc.Annotation.Import.Cancel.Request,
                           Response == Anytype_Rpc.Annotation.Import.Cancel.Response {
    @_spi(OriginalEditor)
    public func retainingOriginalAnnotationImportCancellationHistory() -> OriginalAnnotationImportCancellationCall {
        let history = OriginalAnnotationImportResponseHistory<Response>()
        let observed = Self(
            messageName: messageName, request: request, invokeTask: invokeTask,
            nativeResponseObservation: { response in history.receive(response) }
        )
        return OriginalAnnotationImportCancellationCall(invocation: observed, history: history)
    }
}
// ORIGINAL_ANNOTATION_IMPORT_HISTORY_END
