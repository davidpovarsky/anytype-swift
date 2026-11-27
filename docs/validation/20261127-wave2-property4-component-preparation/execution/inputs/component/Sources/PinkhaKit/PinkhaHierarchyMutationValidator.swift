import Foundation

/// Validates hierarchy mutations to strictly prevent cycles, self-parenting, or invalid parent assignments.
public enum PinkhaHierarchyMutationValidator {

    /// Validates a proposed move of `objectId` to `newParentId`.
    /// Throws `PinkhaHierarchyError` if the move is invalid or would create a cycle.
    public static func validateMove(
        objectId: String,
        newParentId: String?,
        in snapshot: PinkhaHierarchySnapshot
    ) throws {
        guard let node = snapshot.node(for: objectId) else {
            throw PinkhaHierarchyError.nodeNotFound(objectId: objectId)
        }

        // Move to root is always cycle-safe
        guard let targetParentId = newParentId else {
            return
        }

        // Self-parenting check
        if targetParentId == objectId {
            throw PinkhaHierarchyError.selfParent(objectId: objectId)
        }

        // Target parent existence check
        guard snapshot.node(for: targetParentId) != nil else {
            throw PinkhaHierarchyError.parentNotFound(parentId: targetParentId)
        }

        // Descendant cycle check (direct and deep)
        let descendants = snapshot.descendantIds(of: node.objectId)
        if descendants.contains(targetParentId) {
            throw PinkhaHierarchyError.cycleDetected(objectId: objectId, targetParentId: targetParentId)
        }
    }

    /// Returns whether moving `objectId` to `newParentId` is allowed.
    public static func canMove(
        objectId: String,
        to newParentId: String?,
        in snapshot: PinkhaHierarchySnapshot
    ) -> Bool {
        do {
            try validateMove(objectId: objectId, newParentId: newParentId, in: snapshot)
            return true
        } catch {
            return false
        }
    }
}
