import Foundation
import Testing
@testable import PinkhaAnyUI

@Suite("Native document navigation waits for owned presentation dismissal")
struct AnyNativeDocumentNavigationTests {
    private let route = AnyNativeDocumentRoute(objectID: "note-1", blockID: "source-line")

    @Test func productionPlannerDismissesRelatedResultsBeforeTheirPropertiesParent() {
        let order = AnyNativeDocumentNavigation.dismissalOrder(inspectorHost: nil, searchHost: nil,
            showsProperties: true, showsSourceDocuments: true)
        #expect(order == [.sourceDocuments, .properties])
        let owner = UUID()
        var value = AnyNativeDocumentNavigation()
        value.begin(ownerID: owner, route: route, dismissals: order)
        let acceptedDismissal1 = value.didDismiss(.properties, ownerID: owner)
        #expect(!acceptedDismissal1)
        let acceptedDismissal2 = value.didDismiss(.sourceDocuments, ownerID: owner)
        #expect(acceptedDismissal2)
        let dispatchedRoute1 = value.take(ownerID: owner)
        #expect(dispatchedRoute1 == nil)
        let acceptedDismissal3 = value.didDismiss(.properties, ownerID: owner)
        #expect(acceptedDismissal3)
        let dispatchedRoute2 = value.take(ownerID: owner)
        #expect(dispatchedRoute2 == route)
    }

    @Test func productionPlannerPreservesTheOwningInspectorAndSearchHost() {
        #expect(AnyNativeDocumentNavigation.canBeginOwnedPresentation(isReserved: false,
            hasInspector: false, hasSearch: false, hasNativeChild: false, isNavigating: false))
        // The actual sheet may still be dismissing after its binding clears.
        #expect(!AnyNativeDocumentNavigation.canBeginOwnedPresentation(isReserved: true,
            hasInspector: false, hasSearch: false, hasNativeChild: false, isNavigating: false))
        #expect(!AnyNativeDocumentNavigation.canBeginOwnedPresentation(isReserved: false,
            hasInspector: true, hasSearch: false, hasNativeChild: false, isNavigating: false))
        #expect(!AnyNativeDocumentNavigation.canBeginOwnedPresentation(isReserved: false,
            hasInspector: false, hasSearch: true, hasNativeChild: false, isNavigating: false))
        #expect(!AnyNativeDocumentNavigation.canBeginOwnedPresentation(isReserved: false,
            hasInspector: false, hasSearch: false, hasNativeChild: true, isNavigating: false))
        #expect(!AnyNativeDocumentNavigation.canBeginOwnedPresentation(isReserved: false,
            hasInspector: false, hasSearch: false, hasNativeChild: false, isNavigating: true))
        #expect(AnyNativeDocumentNavigation.dismissalOrder(inspectorHost: .properties, searchHost: nil,
            showsProperties: true, showsSourceDocuments: false) == [.propertyInspector, .properties])
        #expect(AnyNativeDocumentNavigation.dismissalOrder(inspectorHost: nil, searchHost: .editor,
            showsProperties: false, showsSourceDocuments: false) == [.editorSearch])
        #expect(AnyNativeDocumentNavigation.dismissalOrder(inspectorHost: .editor, searchHost: nil,
            showsProperties: false, showsSourceDocuments: false) == [.editorInspector])
    }

    @Test func nestedInspectorAndPropertiesDismissInOrder() {
        let owner = UUID()
        var value = AnyNativeDocumentNavigation()
        let acceptedRequest1 = value.begin(ownerID: owner, route: route, dismissals: [.propertyInspector, .properties])
        #expect(acceptedRequest1)
        #expect(value.nextDismissal == .propertyInspector)
        let dispatchedRoute1 = value.take(ownerID: owner)
        #expect(dispatchedRoute1 == nil)
        let acceptedDismissal1 = value.didDismiss(.properties, ownerID: owner)
        #expect(!acceptedDismissal1)
        let acceptedDismissal2 = value.didDismiss(.propertyInspector, ownerID: owner)
        #expect(acceptedDismissal2)
        #expect(value.nextDismissal == .properties)
        let dispatchedRoute2 = value.take(ownerID: owner)
        #expect(dispatchedRoute2 == nil)
        let acceptedDismissal3 = value.didDismiss(.properties, ownerID: owner)
        #expect(acceptedDismissal3)
        let dispatchedRoute3 = value.take(ownerID: owner)
        #expect(dispatchedRoute3 == route)
    }

    @Test func anOldMountedOwnerCannotReleaseTheRoute() {
        let owner = UUID(), stale = UUID()
        var value = AnyNativeDocumentNavigation()
        value.begin(ownerID: owner, route: route, dismissals: [.editorInspector])
        let acceptedDismissal1 = value.didDismiss(.editorInspector, ownerID: stale)
        #expect(!acceptedDismissal1)
        #expect(value.nextDismissal == .editorInspector)
        let dispatchedRoute1 = value.take(ownerID: stale)
        #expect(dispatchedRoute1 == nil)
        let acceptedDismissal2 = value.didDismiss(.editorInspector, ownerID: owner)
        #expect(acceptedDismissal2)
        let dispatchedRoute2 = value.take(ownerID: owner)
        #expect(dispatchedRoute2 == route)
    }

    @Test func duplicateDismissalCannotDispatchTwice() {
        let owner = UUID()
        var value = AnyNativeDocumentNavigation()
        value.begin(ownerID: owner, route: route, dismissals: [.editorInspector])
        let acceptedDismissal1 = value.didDismiss(.editorInspector, ownerID: owner)
        #expect(acceptedDismissal1)
        let acceptedDismissal2 = value.didDismiss(.editorInspector, ownerID: owner)
        #expect(!acceptedDismissal2)
        let dispatchedRoute1 = value.take(ownerID: owner)
        #expect(dispatchedRoute1 == route)
        let dispatchedRoute2 = value.take(ownerID: owner)
        #expect(dispatchedRoute2 == nil)
        #expect(!value.isPending)
    }

    @Test func aSecondRequestDoesNotReplaceThePendingDestination() {
        let owner = UUID()
        var value = AnyNativeDocumentNavigation()
        value.begin(ownerID: owner, route: route, dismissals: [.editorSearch])
        let acceptedRequest1 = value.begin(ownerID: owner, route: .init(objectID: "other", blockID: nil), dismissals: [])
        #expect(!acceptedRequest1)
        #expect(value.nextDismissal == .editorSearch)
        let acceptedDismissal1 = value.didDismiss(.editorSearch, ownerID: owner)
        #expect(acceptedDismissal1)
        let dispatchedRoute1 = value.take(ownerID: owner)
        #expect(dispatchedRoute1 == route)
    }

    @Test func lifetimeRevocationDropsTheRouteWithoutReplay() {
        let oldOwner = UUID(), reopenedOwner = UUID()
        var value = AnyNativeDocumentNavigation()
        value.begin(ownerID: oldOwner, route: route, dismissals: [.editorInspector])
        value.cancel()
        let acceptedDismissal1 = value.didDismiss(.editorInspector, ownerID: oldOwner)
        #expect(!acceptedDismissal1)
        let dispatchedRoute1 = value.take(ownerID: reopenedOwner)
        #expect(dispatchedRoute1 == nil)
        value.begin(ownerID: reopenedOwner, route: route, dismissals: [.sourceDocuments])
        #expect(!value.isOwned(by: oldOwner))
        #expect(value.isOwned(by: reopenedOwner))
        let acceptedDismissal2 = value.didDismiss(.sourceDocuments, ownerID: oldOwner)
        #expect(!acceptedDismissal2)
        let acceptedDismissal3 = value.didDismiss(.sourceDocuments, ownerID: reopenedOwner)
        #expect(acceptedDismissal3)
        let dispatchedRoute2 = value.take(ownerID: reopenedOwner)
        #expect(dispatchedRoute2 == route)
    }

    @Test func anUncoveredDocumentRoutesOnceWithoutASyntheticDismissal() {
        let owner = UUID()
        var value = AnyNativeDocumentNavigation()
        value.begin(ownerID: owner, route: route, dismissals: [])
        #expect(value.nextDismissal == nil)
        let dispatchedRoute1 = value.take(ownerID: owner)
        #expect(dispatchedRoute1 == route)
        let dispatchedRoute2 = value.take(ownerID: owner)
        #expect(dispatchedRoute2 == nil)
    }
}
