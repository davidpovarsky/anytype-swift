import Services
import SwiftUI

@MainActor
@Observable
final class VersionHistoryCoordinatorViewModel:
    VersionHistoryModuleOutput,
    ObjectVersionModuleOutput
{

    var objectVersionData: ObjectVersionData?
    
    let data: VersionHistoryData
    let preparedSession: PreparedEditorPageSession?
    
    private weak var output: (any ObjectVersionModuleOutput)?
    
    init(data: VersionHistoryData, output: (any ObjectVersionModuleOutput)?,
         preparedSession: PreparedEditorPageSession? = nil) {
        self.data = data
        self.output = output
        self.preparedSession = preparedSession
    }
    
    // MARK: VersionHistoryModuleOutput
    
    func onVersionTap(title: String, icon: ObjectIcon?, versionId: String) {
        try? withCurrentSource {
            if preparedSession != nil,
               versionId.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
                throw EditorDocumentWriteError.rejected(.wrongContext)
            }
            objectVersionData = ObjectVersionData(
                title: title,
                icon: icon,
                objectId: data.objectId,
                spaceId: data.spaceId,
                versionId: versionId,
                isListType: data.isListType,
                canRestore: data.canRestore
            )
        }
    }
    
    // MARK: ObjectVersionModuleOutput
    
    func versionRestored(_ text: String) {
        try? withCurrentSource { output?.versionRestored(text) }
    }

    private func withCurrentSource<Value>(_ operation: () throws -> Value) throws -> Value {
        guard let preparedSession else { return try operation() }
        return try preparedSession.owner.performSynchronousOperation(
            contextId: data.objectId, spaceId: data.spaceId, requiresEditing: false
        ) {
            try preparedSession.owner.validateDocument(preparedSession.document)
            return try operation()
        }
    }
}

