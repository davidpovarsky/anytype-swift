import Foundation

/// Retains a locally authenticated callback until its original engine/account can
/// navigate. This queue grants navigation only; native writes and ACKs still use
/// the adapter's current document lease and durable result journal.
@MainActor
public final class PinkhaMiniAppsReturnQueue {
    public struct Target: Sendable, Equatable {
        public let requestID: UUID
        public let engineID: String
        public let accountID: String
        public let spaceID: String
        public let documentID: String
        public let sceneID: String?

        public init(requestID: UUID, engineID: String, accountID: String,
                    spaceID: String, documentID: String, sceneID: String?) {
            self.requestID = requestID
            self.engineID = engineID
            self.accountID = accountID
            self.spaceID = spaceID
            self.documentID = documentID
            self.sceneID = sceneID
        }

        public static func == (lhs: Self, rhs: Self) -> Bool {
            lhs.requestID == rhs.requestID
                && exact(lhs.engineID, rhs.engineID)
                && exact(lhs.accountID, rhs.accountID)
                && exact(lhs.spaceID, rhs.spaceID)
                && exact(lhs.documentID, rhs.documentID)
                && ((lhs.sceneID == nil && rhs.sceneID == nil)
                    || (lhs.sceneID != nil && rhs.sceneID != nil
                        && exact(lhs.sceneID!, rhs.sceneID!)))
        }

        public func matches(engineID: String, accountID: String,
                            spaceID: String, documentID: String) -> Bool {
            Self.exact(self.engineID, engineID) && Self.exact(self.accountID, accountID)
                && Self.exact(self.spaceID, spaceID) && Self.exact(self.documentID, documentID)
        }

        fileprivate static func exact(_ lhs: String, _ rhs: String) -> Bool {
            lhs.utf8.elementsEqual(rhs.utf8)
        }

        fileprivate var isValid: Bool {
            [engineID, accountID, spaceID, documentID].allSatisfy {
                !$0.isEmpty && !$0.utf8.contains(0)
            }
        }
    }

    private var order: [UUID] = []
    private var targets: [UUID: Target] = [:]
    private var navigating = Set<UUID>()

    public init() {}

    /// A repeated URL cannot replace an already authenticated request's identity.
    @discardableResult
    public func retain(_ target: Target) -> Bool {
        guard target.isValid else { return false }
        if let existing = targets[target.requestID] { return existing == target }
        order.append(target.requestID)
        targets[target.requestID] = target
        return true
    }

    public func pending(engineID: String, accountID: String) -> [Target] {
        guard !accountID.isEmpty else { return [] }
        return order.compactMap { targets[$0] }.filter {
            Target.exact($0.engineID, engineID) && Target.exact($0.accountID, accountID)
        }
    }

    /// The first navigation must reach its editor before a second callback can
    /// replace the app's one queued object route.
    public func nextNavigation(engineID: String, accountID: String,
                               ready: Bool) -> Target? {
        guard ready, let first = pending(engineID: engineID, accountID: accountID).first,
              !navigating.contains(first.requestID) else { return nil }
        return first
    }

    @discardableResult
    public func beginNavigation(_ target: Target) -> Bool {
        guard targets[target.requestID] == target else { return false }
        return navigating.insert(target.requestID).inserted
    }

    /// Completion means the matching editor is mounted, never that a result was
    /// written or acknowledged. The bridge remains the durable result owner.
    @discardableResult
    public func didReachEditor(_ target: Target) -> Bool {
        guard targets[target.requestID] == target else { return false }
        targets.removeValue(forKey: target.requestID)
        navigating.remove(target.requestID)
        order.removeAll { $0 == target.requestID }
        return true
    }

    /// An account/engine transition revokes the queued navigation, while keeping
    /// each callback for its exact original account if that account is reopened.
    public func suspendNavigation() {
        navigating.removeAll()
    }
}
