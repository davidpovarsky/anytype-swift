import Foundation
import PinkhaAnyEngine
import PinkhaAnyIntegration

public enum AnyHeartNativeSourceCaptureCoordinatorError: Error, Equatable, Sendable {
    case invalidSession, invalidRequest, invalidLifecycle, inactiveCapture, sourceBinding
}

/// This value is deliberately not Codable. A native session token is never
/// written to the captured bundle, migration journal or presentation model.
public struct AnyHeartNativeSourceSession: Sendable, CustomStringConvertible, CustomDebugStringConvertible {
    public let accountID: String
    public let spaceID: String
    fileprivate let token: String

    public init(sessionToken: String, accountID: String, spaceID: String) throws {
        guard !sessionToken.isEmpty, sessionToken.utf8.count <= 16_384, !sessionToken.contains("\0"),
              [accountID, spaceID].allSatisfy({ !$0.isEmpty && $0.utf8.count <= 4096 && !$0.contains("\0") }) else {
            throw AnyHeartNativeSourceCaptureCoordinatorError.invalidSession
        }
        self.token = sessionToken; self.accountID = accountID; self.spaceID = spaceID
    }

    public var description: String { "AnyHeartNativeSourceSession(redacted)" }
    public var debugDescription: String { description }
}

/// The shipping app injects its actual ServicePinkha* exports. Blocking Go
/// calls must run away from the main actor. No second native library is linked
/// by this shared module; cancellation/release use the same loaded runtime.
public struct AnyHeartNativeSourceBridge: Sendable {
    public typealias Capture = @Sendable (
        _ sessionToken: String, _ accountID: String, _ spaceID: String,
        _ privateDirectory: String, _ requestID: String
    ) async throws -> Data
    public typealias Validate = @Sendable (
        _ sessionToken: String, _ requestID: String, _ manifestSHA256: String
    ) async throws -> Void
    public typealias Control = @Sendable (_ sessionToken: String, _ requestID: String) -> Bool

    fileprivate let capture: Capture
    fileprivate let validate: Validate
    fileprivate let cancel: Control
    fileprivate let release: Control

    public init(capture: @escaping Capture, validate: @escaping Validate,
                cancel: @escaping Control, release: @escaping Control) {
        self.capture = capture; self.validate = validate
        self.cancel = cancel; self.release = release
    }
}

/// A review of the complete captured census. Successful capture and current
/// authorization do not turn a semantic draft into permission to migrate.
public struct AnyHeartNativeSourceCaptureReview: Sendable {
    public struct UnmappedObject: Sendable {
        public let sourceObjectID: String
        public let nativeType: Int64
        public let reason: String
    }

    public let descriptor: AnyHeartNativeCaptureDescriptor
    public let bundle: AnyHeartNativeSpaceBundle
    public let definitionPlan: AnyHeartNativeDefinitionPlan
    public let currentPagePlans: [AnyHeartNativePageComposition]
    public let unmappedObjects: [UnmappedObject]
    public var permitsDestinationWrites: Bool { false }

    fileprivate init(descriptor: AnyHeartNativeCaptureDescriptor, bundle: AnyHeartNativeSpaceBundle) throws {
        self.descriptor = descriptor; self.bundle = bundle
        let definitions = try AnyHeartNativeDefinitionPlan(catalog: .init(bundle: bundle))
        definitionPlan = definitions
        let candidates = bundle.objects.filter {
            $0.nativeType == 16 && $0.objectTypes.count == 1 &&
            definitions.type(sourceURL: $0.objectTypes[0])?.definition.recommendedLayout == 0
        }
        let bindings = candidates.map {
            AnyHeartNativeDefinitionPlan.ObjectBinding(sourceObjectID: $0.sourceObjectID,
                destinationSourceKey: AnyHeartNativePageComposition.objectSourceKey(
                    spaceID: bundle.sourceSpaceID, objectID: $0.sourceObjectID))
        }
        var pages: [AnyHeartNativePageComposition] = [], unmapped: [UnmappedObject] = []
        let definitionIDs = Set((definitions.catalog.types.map(\.objectID) +
            definitions.catalog.relations.map(\.objectID) + definitions.catalog.options.map(\.objectID)).map { Data($0.utf8) })
        for object in bundle.objects where !definitionIDs.contains(Data(object.sourceObjectID.utf8)) {
            try Task.checkCancellation()
            guard candidates.contains(where: { Data($0.sourceObjectID.utf8) == Data(object.sourceObjectID.utf8) }) else {
                unmapped.append(.init(sourceObjectID: object.sourceObjectID, nativeType: object.nativeType,
                    reason: "native-object-kind-or-layout-has-no-qualified-current-page-map"))
                continue
            }
            do {
                pages.append(try .init(bundle: bundle, sourceObjectID: object.sourceObjectID,
                                       definitions: definitions, objects: bindings))
            } catch {
                unmapped.append(.init(sourceObjectID: object.sourceObjectID, nativeType: object.nativeType,
                                      reason: String(describing: error)))
            }
        }
        currentPagePlans = pages; unmappedObjects = unmapped
    }

    /// Bind a future full semantic plan to this exact original source census.
    /// This creates no destination plan and bypasses no semantic coverage gate.
    public func sourceBinding(semanticPlanSHA256: String) throws -> AnyDestinationSourceBinding {
        try .init(bundle: bundle, semanticPlanSHA256: semanticPlanSHA256,
                  sourceObjectIDs: bundle.objects.map(\.sourceObjectID))
    }

    fileprivate func requireSameSource(_ source: AnyDestinationSourceBinding) throws {
        func exact(_ a: String, _ b: String) -> Bool { Data(a.utf8) == Data(b.utf8) }
        guard exact(source.accountID, bundle.sourceAccountID), exact(source.spaceID, bundle.sourceSpaceID),
              source.captureManifestSHA256 == bundle.manifestSHA256,
              source.witnessSHA256 == bundle.sourceWitnessSHA256,
              source.definitionManifestBytes == bundle.manifestBytes,
              Set(source.sourceObjectIDs.map { Data($0.utf8) }) ==
                Set(bundle.objects.map { Data($0.sourceObjectID.utf8) }) else {
            throw AnyHeartNativeSourceCaptureCoordinatorError.sourceBinding
        }
    }
}

/// Owns one capture lifecycle. Create a new coordinator for a new capture,
/// including after process restart. Invalidate it on account or engine switch.
/// Native cancellation is cooperative; a late reply is discarded and released.
public actor AnyHeartNativeSourceCaptureCoordinator {
    public enum InvalidationReason: Equatable, Sendable {
        case accountChanged, engineChanged, userCancelled, released, nativeValidationFailed
    }
    public enum State: Equatable, Sendable {
        case idle, capturing, ready, validating, failed
        case invalidated(InvalidationReason)
    }

    public private(set) var state: State = .idle
    private let bridge: AnyHeartNativeSourceBridge
    private let privateDirectory: URL
    private var session: AnyHeartNativeSourceSession?
    private var requestID: String?
    private var review: AnyHeartNativeSourceCaptureReview?

    public init(bridge: AnyHeartNativeSourceBridge, privateDirectory: URL) throws {
        guard privateDirectory.isFileURL, privateDirectory.path.hasPrefix("/"),
              !privateDirectory.path.contains("\0") else {
            throw AnyHeartNativeCaptureError.privateDirectory
        }
        self.bridge = bridge; self.privateDirectory = privateDirectory
    }

    public func capture(session: AnyHeartNativeSourceSession,
                        requestID: String) async throws -> AnyHeartNativeSourceCaptureReview {
        guard state == .idle else { throw AnyHeartNativeSourceCaptureCoordinatorError.invalidLifecycle }
        guard !requestID.isEmpty, requestID.utf8.count <= 128, requestID.utf8.allSatisfy({
            (48...57).contains($0) || (65...90).contains($0) || (97...122).contains($0) || $0 == 45 || $0 == 95
        }) else { throw AnyHeartNativeSourceCaptureCoordinatorError.invalidRequest }
        try Task.checkCancellation()
        self.session = session; self.requestID = requestID; state = .capturing
        let bridge = self.bridge, parent = privateDirectory
        do {
            let bytes = try await withTaskCancellationHandler {
                try await bridge.capture(session.token, session.accountID, session.spaceID, parent.path, requestID)
            } onCancel: { _ = bridge.cancel(session.token, requestID) }
            try Task.checkCancellation()
            guard state == .capturing else { throw AnyHeartNativeSourceCaptureCoordinatorError.inactiveCapture }
            let read = Task.detached(priority: .userInitiated) {
                let descriptor = try AnyHeartNativeCaptureDescriptor(data: bytes,
                    expectedAccountID: session.accountID, expectedSpaceID: session.spaceID, expectedRequestID: requestID)
                let bundle = try descriptor.loadBundle(under: parent)
                return try AnyHeartNativeSourceCaptureReview(descriptor: descriptor, bundle: bundle)
            }
            let result = try await withTaskCancellationHandler { try await read.value }
                onCancel: { read.cancel(); _ = bridge.cancel(session.token, requestID) }
            try Task.checkCancellation()
            guard state == .capturing else { throw AnyHeartNativeSourceCaptureCoordinatorError.inactiveCapture }
            review = result; state = .ready
            return result
        } catch {
            _ = bridge.release(session.token, requestID)
            if state == .capturing {
                state = error is CancellationError ? .invalidated(.userCancelled) : .failed
            }
            self.session = nil; self.requestID = nil; review = nil
            throw error
        }
    }

    /// Supply this to the executor's verifySource callback. This is a fresh
    /// native authority/checkpoint read, separate from semantic admission and
    /// from the destination's own authorization callback.
    public func revalidate(source: AnyDestinationSourceBinding) async throws {
        guard state == .ready, let session, let requestID, let review else {
            throw AnyHeartNativeSourceCaptureCoordinatorError.inactiveCapture
        }
        try review.requireSameSource(source)
        try Task.checkCancellation()
        state = .validating
        let bridge = self.bridge
        do {
            try await withTaskCancellationHandler {
                try await bridge.validate(session.token, requestID, review.descriptor.manifestSHA256)
            } onCancel: { _ = bridge.cancel(session.token, requestID) }
            try Task.checkCancellation()
            guard state == .validating else { throw AnyHeartNativeSourceCaptureCoordinatorError.inactiveCapture }
            state = .ready
        } catch {
            if state == .validating {
                state = .invalidated(error is CancellationError ? .userCancelled : .nativeValidationFailed)
            }
            _ = bridge.release(session.token, requestID)
            self.session = nil; self.requestID = nil; self.review = nil
            throw error
        }
    }

    /// Releases only native metadata/cancellation slots. Original source
    /// files are retained for review and recovery; no source account is closed.
    public func invalidate(_ reason: InvalidationReason) {
        state = .invalidated(reason)
        if let session, let requestID {
            _ = bridge.cancel(session.token, requestID)
            _ = bridge.release(session.token, requestID)
        }
        session = nil; requestID = nil; review = nil
    }

    public func cancel() { invalidate(.userCancelled) }
    public func release() { invalidate(.released) }
}
