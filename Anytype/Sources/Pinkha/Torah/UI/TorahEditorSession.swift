import Foundation
import PinkhaKit
import PinkhaTorahPresentation

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
    }
}
