import SwiftUI


struct TypePropertiesDropDelegate: DropDelegate {
    let destinationRow: TypePropertiesRow
    let document: any BaseDocumentProtocol
    
    @Binding var draggedRow: TypePropertiesRow?
    @Binding var allRows: [TypePropertiesRow]
    var originalEditorScope: OriginalEditorPropertyScope? = nil
    
    private let moveHandler = TypePropertiesMoveHandler()
    
    func dropUpdated(info: DropInfo) -> DropProposal? {
        return DropProposal(operation: .move)
    }
    
    func performDrop(info: DropInfo) -> Bool {
        draggedRow = nil
        return true
    }
    
    func dropEntered(info: DropInfo) {
        guard let draggedRow else { return }
        guard let fromIndex = allRows.firstIndex(of: draggedRow) else { return }
        guard let toIndex = allRows.firstIndex(of: destinationRow) else { return }

        if let originalEditorScope {
            // SwiftUI invokes the native drop callback on the UI thread. Do
            // not enqueue a mutation to obtain actor isolation after the fact.
            guard Thread.isMainThread else { return }
            let rows = allRows
            let handler = TypePropertiesMoveHandler(originalEditorScope: originalEditorScope)
            MainActor.assumeIsolated {
                originalEditorScope.schedule(requiredPermissions: OriginalEditorPropertyScope.listPermissions) {
                    try await handler.onMove(
                        from: fromIndex, to: toIndex, relationRows: rows, document: document
                    )
                }
            }
            return
        }
        
        Task {
            try await moveHandler.onMove(
                from: fromIndex,
                to: toIndex,
                relationRows: allRows,
                document: document
            )
        }
    }

}
