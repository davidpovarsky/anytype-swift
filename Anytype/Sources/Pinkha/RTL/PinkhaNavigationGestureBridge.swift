import SwiftUI
import UIKit
import PinkhaKit

@MainActor
enum PinkhaNavigationGestureBridge {
    private final class Entry {
        weak var controller: FullScreenSwipeNavigationController?
        var topObjectId: String?
        var layoutDirection: PinkhaLayoutDirection = .leftToRight
        let originalInteractivePopEdges: UIRectEdge?
        var originalLayoutDirection: PinkhaLayoutDirection?
        var didOverrideInteractivePopEdge = false

        init(controller: FullScreenSwipeNavigationController) {
            self.controller = controller
            originalInteractivePopEdges = (
                controller.interactivePopGestureRecognizer as? UIScreenEdgePanGestureRecognizer
            )?.edges
        }
    }

    private static var entries = [ObjectIdentifier: Entry]()
    private static var pinkhaWritingDocumentIds = Set<String>()

    static func setPinkhaWritingDocument(id: String, isPinkhaWritingDocument: Bool) {
        let changed: Bool
        if isPinkhaWritingDocument {
            changed = pinkhaWritingDocumentIds.insert(id).inserted
        } else {
            changed = pinkhaWritingDocumentIds.remove(id) != nil
        }
        guard changed else { return }
        updateConnectedControllers()
    }

    static func update(
        controller: FullScreenSwipeNavigationController,
        topNavigationItem: AnyHashable?,
        layoutDirection: LayoutDirection
    ) {
        let key = ObjectIdentifier(controller)
        let entry = entries[key] ?? Entry(controller: controller)
        entry.topObjectId = (topNavigationItem?.base as? EditorScreenData)?.objectId
        let effectiveDirection: PinkhaLayoutDirection = layoutDirection == .rightToLeft
            ? .rightToLeft
            : .leftToRight
        if entry.originalLayoutDirection == nil {
            entry.originalLayoutDirection = effectiveDirection
        }
        entry.layoutDirection = effectiveDirection
        entries[key] = entry
        applySemanticDirection(to: entry)
    }

    static func requiresPublicEdgePop(
        controller: FullScreenSwipeNavigationController
    ) -> Bool {
        guard let entry = entries[ObjectIdentifier(controller)] else { return false }
        return requiresPublicEdgePop(entry)
    }

    static func normalizedProgress(
        controller: FullScreenSwipeNavigationController,
        translationX: CGFloat,
        containerWidth: CGFloat
    ) -> CGFloat {
        guard let entry = entries[ObjectIdentifier(controller)],
              requiresPublicEdgePop(entry) else {
            // Preserve the original Anytype progress behavior byte-for-byte outside the
            // exact Pinkha RTL gate.
            return translationX / containerWidth
        }
        return CGFloat(PinkhaNavigationDirectionPolicy.normalizedBackProgress(
            translationX: Double(translationX),
            containerWidth: Double(containerWidth),
            layoutDirection: entry.layoutDirection
        ))
    }

    private static func requiresPublicEdgePop(_ entry: Entry) -> Bool {
        guard entry.layoutDirection == .rightToLeft,
              let objectId = entry.topObjectId else {
            return false
        }
        return pinkhaWritingDocumentIds.contains(objectId)
    }

    private static func updateConnectedControllers() {
        entries = entries.filter { _, entry in
            guard entry.controller != nil else { return false }
            applySemanticDirection(to: entry)
            return true
        }
    }

    private static func applySemanticDirection(to entry: Entry) {
        guard let controller = entry.controller else { return }
        let usesRTLPublicEdge = requiresPublicEdgePop(entry)
        controller.view.semanticContentAttribute = usesRTLPublicEdge ? .forceRightToLeft : .unspecified
        if let edgeRecognizer = controller.interactivePopGestureRecognizer as? UIScreenEdgePanGestureRecognizer {
            if usesRTLPublicEdge {
                edgeRecognizer.edges = .right
                entry.didOverrideInteractivePopEdge = true
            } else if entry.didOverrideInteractivePopEdge {
                if entry.layoutDirection == entry.originalLayoutDirection,
                   let originalEdges = entry.originalInteractivePopEdges {
                    edgeRecognizer.edges = originalEdges
                } else {
                    edgeRecognizer.edges = entry.layoutDirection == .rightToLeft ? .right : .left
                }
                entry.didOverrideInteractivePopEdge = false
            }
        }
    }
}
