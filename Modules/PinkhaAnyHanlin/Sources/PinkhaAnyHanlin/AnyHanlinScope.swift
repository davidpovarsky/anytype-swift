import Foundation
import HanlinHostContracts
import PinkhaAnyHost

/// Validated scope values only. Live native and mounted presentation checks
/// remain necessary at every read/confirmation/dispatch boundary.
enum AnyHanlinScope {
    static func makeSession(
        accountID: String, spaceID: String, sceneID: UUID,
        conversationID: UUID, snapshot: AnyEditorSnapshot?, selection: [String],
        locale: Locale
    ) throws -> HanlinHostSession {
        guard locale.identifier.utf8.count <= 64, selection.count <= 64,
              Set(selection.map { Data($0.utf8) }).count == selection.count,
              selection.allSatisfy({ !$0.isEmpty && $0.utf8.count <= 256 }) else {
            throw HanlinHostError.invalidContext
        }
        if let snapshot {
            guard snapshot.spaceID.utf8.elementsEqual(spaceID.utf8),
                  snapshot.objectID.utf8.count <= 256, snapshot.revision.utf8.count <= 256,
                  Set(selection).isSubset(of: Set(snapshot.depthFirstIDs)) else {
                throw HanlinHostError.invalidContext
            }
        } else {
            guard selection.isEmpty else { throw HanlinHostError.invalidContext }
        }
        let namespace = try HanlinConversationNamespace(
            app: "anytype", account: accountID, workspace: spaceID, space: spaceID)
        return HanlinHostSession(conversationID: conversationID, context: .init(
            namespace: namespace, sceneID: sceneID, generation: UUID(),
            objectReference: snapshot?.objectID, selectionReferences: selection,
            sourceRevision: snapshot?.revision, localeIdentifier: locale.identifier))
    }
}
