#if PINKHA_DUAL_ENGINE_RUNTIME
import Foundation
import SwiftUI
import PinkhaAnyNative
import PinkhaAnyUI
import PinkhaAnyHost
import PinkhaAnyEngine

/// The application's public boundary owns the real underlying Any actor.
/// Private native modules stay linked by this facade, without exposing their
/// type metadata as unlinked transitive API in the original application.
public final class PinkhaEmbeddedAnyApplication: Sendable {
    fileprivate let application: AnyNativeApplication

    public init(dataDirectory: URL, credentialService: String) throws {
        application = try AnyNativeApplication(dataDirectory: dataDirectory,
                                              credentialService: credentialService)
    }
}

public struct PinkhaEmbeddedAnyLaunchConfiguration: Sendable {
    public let dataDirectory: URL
    public let credentialService: String

    public static func current() throws -> Self {
        let configuration = try AnyNativeLaunchConfiguration.current()
        return Self(dataDirectory: configuration.dataDirectory,
                    credentialService: configuration.credentialService)
    }
}

/// Non-authority routing metadata from the currently mounted native owner.
/// An empty displayName means that no current cached title was available;
/// destination selection and execution always use the exact opaque IDs.
public struct PinkhaEmbeddedAnyDestinationSelection: Sendable {
    public let accountID: String
    public let spaceID: String
    public let displayName: String
    public let networkID: String
    public var grantsNativeAuthority: Bool { false }
}

/// Lifecycle methods forward to the same original native presentation owner.
@MainActor
public final class PinkhaEmbeddedAnyPresentation {
    fileprivate let session: AnyNativePresentationSession

    public init(application: PinkhaEmbeddedAnyApplication) {
        session = AnyNativePresentationSession(application: application.application)
    }

    public func resume() { session.resume() }

    public func selectedDestination() async throws -> PinkhaEmbeddedAnyDestinationSelection {
        let selected = try await session.selectedDestination()
        return .init(accountID: selected.accountID, spaceID: selected.spaceID,
            displayName: selected.displayName, networkID: selected.networkID)
    }

    /// Forwards into the same presentation owner used by the mounted Any view.
    public func performDestinationOperation<Value: Sendable>(
        expectedAccountID: String, expectedSpaceID: String,
        _ operation: @escaping @Sendable (
            AnyHTTPClient, AnyApplicationSession, AnyHostLease
        ) async throws -> Value
    ) async throws -> Value {
        try await session.performDestinationOperation(
            expectedAccountID: expectedAccountID, expectedSpaceID: expectedSpaceID,
            operation)
    }

    public func suspendAndWait() async { await session.suspendAndWait() }
}

@MainActor
public struct PinkhaEmbeddedAnyRootView: View {
    private let content: AnyView

    public init(session: PinkhaEmbeddedAnyPresentation) {
        content = AnyView(AnyNativeRootView(session: session.session))
    }

    public var body: some View { content }
}

@MainActor
public final class PinkhaEmbeddedAnyMiniAppsReturnRouter {
    public static let shared = PinkhaEmbeddedAnyMiniAppsReturnRouter()
    private init() {}

    @discardableResult
    public func receive(_ url: URL) -> Bool {
        AnyMiniAppsReturnRouter.shared.receive(url)
    }
}

// The native capture protocol is also a direct, explicit pure-Swift dependency
// of the original app; its source controller uses these public models itself.
public typealias PinkhaEmbeddedHeartSourceReview = AnyHeartNativeSourceCaptureReview

@MainActor
public struct PinkhaEmbeddedHeartSourceReviewView: View {
    private let content: AnyView

    public init(review: PinkhaEmbeddedHeartSourceReview, spaceName: String = "") {
        content = AnyView(AnyHeartNativeSourceReviewView(review: review, spaceName: spaceName))
    }

    public var body: some View { content }
}
#else
/// Legacy validation builds retain their original single Heart native graph.
public enum PinkhaEngineHostNotConfigured {}
#endif
