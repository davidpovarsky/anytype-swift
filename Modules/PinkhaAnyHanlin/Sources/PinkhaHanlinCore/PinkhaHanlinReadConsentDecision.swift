import Foundation

/// The actual prompt's single completion state; revocation cannot be undone by a late Allow action.
@MainActor
public final class PinkhaHanlinReadConsentDecision {
    public init() {}
    public private(set) var authorized = false
    public private(set) var revoked = false
    private var completion: ((Bool) -> Void)?
    public var isPending: Bool { completion != nil }

    public func begin(_ completion: @escaping (Bool) -> Void) -> Bool {
        guard !revoked, self.completion == nil else { return false }
        self.completion = completion
        return true
    }

    public func resolve(_ allowed: Bool) {
        guard let completion else { return }
        self.completion = nil
        authorized = allowed && !revoked
        completion(authorized)
    }

    /// Invoked by the explicit native Allow button before its owned sheet is
    /// dismissed. The exact pending request must still have a current owner.
    public func resolveAllow(validating validate: @MainActor () throws -> Void) {
        guard !revoked, isPending else { return }
        do {
            try validate()
            resolve(true)
        } catch {
            resolve(false)
        }
    }

    public func revoke() {
        revoked = true
        authorized = false
        resolve(false)
    }
}
