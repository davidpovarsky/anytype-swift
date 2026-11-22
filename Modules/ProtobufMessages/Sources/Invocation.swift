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
    
    init(messageName: String, request: Request, invokeTask: @escaping @Sendable (Request) throws -> Response) {
        self.messageName = messageName
        self.request = request
        self.invokeTask = invokeTask
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
