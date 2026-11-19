import Foundation

/// A route waits for the actual owned-sheet dismissal callbacks. It carries no
/// native write authority and never replaces a still-pending user navigation.
enum AnyNativeNavigationDismissal: Equatable, Sendable {
    case editorInspector, propertyInspector, editorSearch, propertySearch
    case properties, sourceDocuments
}

enum AnyNativeNavigationHost: Equatable, Sendable { case editor, properties }

struct AnyNativeDocumentRoute: Equatable, Sendable {
    let objectID: String
    let blockID: String?
}

struct AnyNativeDocumentNavigation: Sendable {
    private struct Request: Sendable {
        let ownerID: UUID
        let route: AnyNativeDocumentRoute
        var dismissals: [AnyNativeNavigationDismissal]
    }
    private var request: Request?
    var isPending: Bool { request != nil }
    var nextDismissal: AnyNativeNavigationDismissal? { request?.dismissals.first }
    func isOwned(by ownerID: UUID) -> Bool { request?.ownerID == ownerID }

    /// A sheet's binding can clear before its actual dismissal callback. The
    /// reservation keeps a second property child from starting in that gap.
    static func canBeginOwnedPresentation(isReserved: Bool, hasInspector: Bool,
                                              hasSearch: Bool, hasNativeChild: Bool,
                                              isNavigating: Bool) -> Bool {
        !isReserved && !hasInspector && !hasSearch && !hasNativeChild && !isNavigating
    }

    static func dismissalOrder(inspectorHost: AnyNativeNavigationHost?,
                               searchHost: AnyNativeNavigationHost?,
                               showsProperties: Bool,
                               showsSourceDocuments: Bool) -> [AnyNativeNavigationDismissal] {
        var result: [AnyNativeNavigationDismissal] = []
        if let inspectorHost {
            result.append(inspectorHost == .properties ? .propertyInspector : .editorInspector)
        }
        if let searchHost {
            result.append(searchHost == .properties ? .propertySearch : .editorSearch)
        }
        // Related-document results are presented by the properties panel.
        // Dismissing their parent first can consume the child's sole callback.
        if showsSourceDocuments { result.append(.sourceDocuments) }
        if showsProperties { result.append(.properties) }
        return result
    }

    @discardableResult
    mutating func begin(ownerID: UUID, route: AnyNativeDocumentRoute,
                        dismissals: [AnyNativeNavigationDismissal]) -> Bool {
        guard request == nil else { return false }
        request = .init(ownerID: ownerID, route: route, dismissals: dismissals)
        return true
    }

    @discardableResult
    mutating func didDismiss(_ sheet: AnyNativeNavigationDismissal, ownerID: UUID) -> Bool {
        guard request?.ownerID == ownerID, request?.dismissals.first == sheet else { return false }
        request?.dismissals.removeFirst()
        return true
    }

    mutating func take(ownerID: UUID) -> AnyNativeDocumentRoute? {
        guard let current = request, current.ownerID == ownerID, current.dismissals.isEmpty else { return nil }
        request = nil
        return current.route
    }

    mutating func cancel() { request = nil }
}
