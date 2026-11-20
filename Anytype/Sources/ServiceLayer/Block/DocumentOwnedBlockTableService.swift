import Foundation
import Services

/// The original table service, bound to one prepared document's existing owner.
/// An admitted native effect keeps the owner's explicit late-completion semantics.
final class DocumentOwnedBlockTableService: BlockTableServiceProtocol {
    private let owner: EditorDocumentWriteOwner
    private let service: any BlockTableServiceProtocol

    init(owner: EditorDocumentWriteOwner, service: any BlockTableServiceProtocol) {
        self.owner = owner
        self.service = service
    }

    func createTable(contextId: String, targetId: String, position: BlockPosition, rowsCount: Int, columnsCount: Int) async throws -> String {
        try await owner.performMutation(contextId: contextId) { [service] in
            try await service.createTable(contextId: contextId, targetId: targetId, position: position, rowsCount: rowsCount, columnsCount: columnsCount)
        }
    }

    func rowListFill(contextId: String, targetIds: [String]) async throws {
        try await owner.performMutation(contextId: contextId) { [service] in
            try await service.rowListFill(contextId: contextId, targetIds: targetIds)
        }
    }

    func insertColumn(contextId: String, targetId: String, position: BlockPosition) async throws {
        try await owner.performMutation(contextId: contextId) { [service] in
            try await service.insertColumn(contextId: contextId, targetId: targetId, position: position)
        }
    }

    func deleteColumn(contextId: String, targetId: String) async throws {
        try await owner.performMutation(contextId: contextId) { [service] in
            try await service.deleteColumn(contextId: contextId, targetId: targetId)
        }
    }

    func columnDuplicate(contextId: String, targetId: String) async throws {
        try await owner.performMutation(contextId: contextId) { [service] in
            try await service.columnDuplicate(contextId: contextId, targetId: targetId)
        }
    }

    func columnSort(contextId: String, columnId: String, blocksSortType: BlocksSortType) async throws {
        try await owner.performMutation(contextId: contextId) { [service] in
            try await service.columnSort(contextId: contextId, columnId: columnId, blocksSortType: blocksSortType)
        }
    }

    func columnMove(contextId: String, targetId: String, dropTargetID: String, position: BlockPosition) async throws {
        try await owner.performMutation(contextId: contextId) { [service] in
            try await service.columnMove(contextId: contextId, targetId: targetId, dropTargetID: dropTargetID, position: position)
        }
    }

    func insertRow(contextId: String, targetId: String, position: BlockPosition) async throws {
        try await owner.performMutation(contextId: contextId) { [service] in
            try await service.insertRow(contextId: contextId, targetId: targetId, position: position)
        }
    }

    func deleteRow(contextId: String, targetId: String) async throws {
        try await owner.performMutation(contextId: contextId) { [service] in
            try await service.deleteRow(contextId: contextId, targetId: targetId)
        }
    }

    func rowDuplicate(contextId: String, targetId: String) async throws {
        try await owner.performMutation(contextId: contextId) { [service] in
            try await service.rowDuplicate(contextId: contextId, targetId: targetId)
        }
    }

    func rowMove(contextId: String, targetId: String, dropTargetID: String, position: BlockPosition) async throws {
        try await owner.performMutation(contextId: contextId) { [service] in
            try await service.rowMove(contextId: contextId, targetId: targetId, dropTargetID: dropTargetID, position: position)
        }
    }

    func clearContents(contextId: String, blockIds: [String]) async throws {
        try await owner.performMutation(contextId: contextId) { [service] in
            try await service.clearContents(contextId: contextId, blockIds: blockIds)
        }
    }

    func clearStyle(contextId: String, blocksIds: [String]) async throws {
        try await owner.performMutation(contextId: contextId) { [service] in
            try await service.clearStyle(contextId: contextId, blocksIds: blocksIds)
        }
    }
}
