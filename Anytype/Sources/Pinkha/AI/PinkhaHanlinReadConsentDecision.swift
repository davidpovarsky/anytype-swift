import Foundation

/// The actual prompt's single completion state; revocation cannot be undone by a late Allow action.
@MainActor
final class PinkhaHanlinReadConsentDecision {
    private(set) var authorized = false
    private(set) var revoked = false
    private var completion: ((Bool) -> Void)?
    var isPending: Bool { completion != nil }

    func begin(_ completion: @escaping (Bool) -> Void) -> Bool {
        guard !revoked, self.completion == nil else { return false }
        self.completion = completion
        return true
    }

    func resolve(_ allowed: Bool) {
        guard let completion else { return }
        self.completion = nil
        authorized = allowed && !revoked
        completion(authorized)
    }

    func revoke() {
        revoked = true
        authorized = false
        resolve(false)
    }
}
