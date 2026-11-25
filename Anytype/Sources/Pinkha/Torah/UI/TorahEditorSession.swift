import Foundation
import PinkhaKit
import PinkhaTorahPresentation
#if PINKHA_NATIVE_T2_AUTHORIZED_READ_V1 && PINKHA_NATIVE_SEMANTIC_ANCHOR_PAGE154_V1
import ProtobufMessages
#endif

typealias TorahEditorSession = PinkhaTorahPresentation.TorahEditorSession
typealias TorahAssociationContext = PinkhaTorahPresentation.TorahAssociationContext
typealias TorahAssociationDisplayFormatter = PinkhaTorahPresentation.TorahAssociationDisplayFormatter
typealias TorahSourceInsertionAction = PinkhaTorahPresentation.TorahSourceInsertionAction

@MainActor
extension PinkhaTorahPresentation.TorahEditorSession {
    convenience init(spaceId: String, objectId: String) throws {
        self.init(spaceId: spaceId, objectId: objectId,
                  workspace: try AnytypeTorahWorkspace.sefaria(),
                  associations: AnytypeTorahAssociationRepository())
    }

    convenience init(spaceId: String, objectId: String, workspace: AnytypeTorahWorkspace,
                     associations: any AnytypeTorahAssociationSnapshotRepository) {
        self.init(spaceId: spaceId, objectId: objectId, workspace: workspace,
                  associations: associations,
                  notesService: AnytypeTorahNotesService(spaceId: spaceId, objectId: objectId,
                                                         associations: associations))
        #if PINKHA_NATIVE_T2_AUTHORIZED_READ_V1 && PINKHA_NATIVE_SEMANTIC_ANCHOR_PAGE154_V1
        if let lease = try? PinkhaNativeReadLifetime.shared.lease(forOpenedSpaceID: spaceId) {
            let anchors = AnytypeHeartSemanticAnchorService()
            installSemanticAnchorResolver { anchor in
                try await anchors.resolve(anchor, lease: lease)
            }
        }
        #endif
    }
}
