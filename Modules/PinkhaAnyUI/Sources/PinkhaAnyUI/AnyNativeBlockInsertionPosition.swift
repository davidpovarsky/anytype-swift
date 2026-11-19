import Foundation
import PinkhaAnyHost
import PinkhaAnyIntegration

public enum AnyNativeBlockInsertionPolicy: Sendable, Equatable {
    case endOfRoot
    case beforeBlock(String)
    case afterLastVisibleBlock
}

/// Quote append follows the last depth-first visible block in its own parent,
/// matching the retained editor. Ordinary new paragraphs still append to root.
public struct AnyNativeBlockInsertionPosition: Sendable, Equatable {
    public let parentID: String
    public let position: String

    public static func resolve(snapshot: AnyEditorSnapshot,
                               policy: AnyNativeBlockInsertionPolicy) throws -> Self {
        let reachable = Set(snapshot.depthFirstIDs)
        let byID = Dictionary(uniqueKeysWithValues: snapshot.blocks.map { ($0.id, $0) })
        let parentID: String, previous: String?, next: String?
        func siblings(_ parent: String) -> [AnyEditorBlock] {
            snapshot.blocks.filter { $0.parentID == parent && reachable.contains($0.id) }.sorted {
                $0.position.utf8.elementsEqual($1.position.utf8) ? $0.id < $1.id :
                    $0.position.utf8.lexicographicallyPrecedes($1.position.utf8)
            }
        }
        switch policy {
        case .beforeBlock(let id):
            guard reachable.contains(id), let target = byID[id] else { throw AnyHostError.invalidSelection }
            parentID = target.parentID
            let rows = siblings(parentID)
            guard let offset = rows.firstIndex(where: { $0.id == id }) else { throw AnyHostError.invalidSelection }
            previous = offset > 0 ? rows[offset - 1].position : nil
            next = target.position
        case .afterLastVisibleBlock where !snapshot.depthFirstIDs.isEmpty:
            guard let id = snapshot.depthFirstIDs.last, let target = byID[id] else {
                throw AnyHostError.invalidSelection
            }
            parentID = target.parentID
            let rows = siblings(parentID)
            guard let offset = rows.firstIndex(where: { $0.id == id }) else { throw AnyHostError.invalidSelection }
            previous = target.position
            next = offset + 1 < rows.count ? rows[offset + 1].position : nil
        case .endOfRoot, .afterLastVisibleBlock:
            parentID = ""; previous = siblings("").last?.position; next = nil
        }
        return .init(parentID: parentID,
                     position: try AnyLexicographicPosition.between(after: previous, before: next))
    }
}
