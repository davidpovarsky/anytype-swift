import Foundation

/// A complete native ObjectShow tree in its actual child order. It contains no
/// saved selection or content-search fallback. Unknown/cyclic/incomplete trees
/// cannot yield a seemingly unique anchor by omitting part of the document.
public struct PinkhaHeartSemanticAnchorDocument: Sendable {
    public struct Block: Sendable {
        public let id: String
        public let text: PinkhaHeartSemanticAnchorSnapshot?
    }
    public let spaceID: String
    public let objectID: String
    public let blocks: [Block]

    public init(response: Anytype_Rpc.Object.Show.Response,
                spaceID: String, objectID: String) throws {
        guard response.error.code == .null, response.hasObjectView,
              heartBytesEqual(response.objectView.rootID, objectID),
              (1...10_000).contains(response.objectView.blocks.count) else {
            throw PinkhaHeartSemanticAnchorError.changedDocument
        }
        let rows = response.objectView.details.filter { heartBytesEqual($0.id, objectID) }
        guard rows.count == 1, let row = rows.first, row.hasDetails,
              case .stringValue(let actualObject)? = row.details.fields["id"]?.kind,
              case .stringValue(let actualSpace)? = row.details.fields["spaceId"]?.kind,
              heartBytesEqual(actualObject, objectID), heartBytesEqual(actualSpace, spaceID) else {
            throw PinkhaHeartSemanticAnchorError.changedDocument
        }
        var byID: [Data: Anytype_Model_Block] = [:]
        for block in response.objectView.blocks {
            guard !block.id.isEmpty, block.id.utf8.count <= 1_024,
                  !block.id.contains("\0"), byID[Data(block.id.utf8)] == nil,
                  block.unknownFields.data.isEmpty else {
                throw PinkhaHeartSemanticAnchorError.changedDocument
            }
            byID[Data(block.id.utf8)] = block
        }
        guard let root = byID[Data(objectID.utf8)], case .smartblock? = root.content else {
            throw PinkhaHeartSemanticAnchorError.changedDocument
        }
        var visited = Set<Data>(), pending = [objectID], ordered: [Block] = []
        while let id = pending.popLast() {
            let key = Data(id.utf8)
            guard visited.insert(key).inserted, let block = byID[key],
                  Set(block.childrenIds.map { Data($0.utf8) }).count == block.childrenIds.count else {
                throw PinkhaHeartSemanticAnchorError.changedDocument
            }
            if !heartBytesEqual(id, objectID) {
                switch block.content {
                case .text?: ordered.append(.init(id: id, text: try .init(nativeBlock: block)))
                case .layout?: break // Structural rows/columns do not add displayed text.
                case nil: throw PinkhaHeartSemanticAnchorError.changedDocument
                default: ordered.append(.init(id: id, text: nil)) // A real nontext separator.
                }
            }
            pending.append(contentsOf: block.childrenIds.reversed())
        }
        guard visited.count == byID.count else { throw PinkhaHeartSemanticAnchorError.changedDocument }
        self.spaceID = spaceID; self.objectID = objectID; self.blocks = ordered
    }
}
