import Logger
import PinkhaKit
import ProtobufMessages
import Services
import SwiftProtobuf

@MainActor
enum PinkhaTextDirectionPersistence {
    private static let log = EventLogger(category: "Pinkha")
    private static var sessionExplicitAlignments = [String: PinkhaParagraphAlignment]()

    static func sessionExplicitAlignment(blockId: String) -> PinkhaParagraphAlignment? {
        sessionExplicitAlignments[blockId]
    }

    /// Called only after the host has committed a real user alignment command. The marker
    /// disambiguates that explicit choice on future launches; language/layout rendering never
    /// enters this path. It applies uniformly to ordinary Note/Page and Pinkha documents.
    static func markExplicitAlignmentIfNeeded(
        document: some BaseDocumentProtocol,
        blockIds: [String],
        alignment: LayoutAlignment,
        blockService: some BlockServiceProtocol
    ) async throws {
        guard let pinkhaAlignment = alignment.pinkhaMarkerAlignment else { return }

        let marker = PinkhaTextDirectionMarker.explicit(pinkhaAlignment)
        for blockId in blockIds {
            sessionExplicitAlignments[blockId] = pinkhaAlignment
            guard let info = document.infoContainer.get(id: blockId) else { continue }
            var fields = info.fields
            fields[PinkhaSchemaRoles.blockTextDirectionField] = Google_Protobuf_Value(
                stringValue: marker.storedValue
            )
            do {
                try await blockService.setFields(
                    objectId: document.objectId,
                    blockId: blockId,
                    fields: fields
                )
            } catch {
                // The host alignment already succeeded. Metadata is best-effort and must not
                // roll back or fail the explicit formatting command.
                log.error("Failed to persist explicit alignment marker for block \(blockId): \(error)")
            }
        }
    }

    static func resetForTesting() {
        sessionExplicitAlignments.removeAll()
    }
}

private extension LayoutAlignment {
    var pinkhaMarkerAlignment: PinkhaParagraphAlignment? {
        switch self {
        case .left: .left
        case .center: .center
        case .right: .right
        case .justify: .justified
        case .UNRECOGNIZED: nil
        }
    }
}
