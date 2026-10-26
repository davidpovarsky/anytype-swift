import UIKit
import Factory
import Logger
import PinkhaKit
import ProtobufMessages
import Services
import SwiftProtobuf

@MainActor
enum PinkhaTextDirectionPersistence {
    private static let log = EventLogger(category: "Pinkha")
    private static var pendingTasks = [String: Task<Void, Never>]()
    private static var generations = [String: UInt]()
    private static var sessionExplicitAlignments = [String: PinkhaParagraphAlignment]()

    static func sessionExplicitAlignment(blockId: String) -> PinkhaParagraphAlignment? {
        sessionExplicitAlignments[blockId]
    }

    static func scheduleAutomaticDirectionIfNeeded(
        document: some BaseDocumentProtocol,
        info: BlockInformation,
        attributedText: NSAttributedString,
        selectedRange: NSRange
    ) {
        guard PinkhaTextDirectionGate.isWritingDocument(document) else { return }
        let text = attributedText.string
        let attributedDirection = PinkhaTextDirectionUIKitAdapter.attributedDirection(
            in: attributedText
        )

        // The range is deliberately captured only as evidence of the input snapshot. This
        // coordinator never writes it back and never accesses the UITextView.
        _ = selectedRange

        scheduleAutomaticDirection(
            document: document,
            info: info,
            text: text,
            fallbackDirection: attributedDirection
        )
    }

    static func scheduleInitialDirectionIfNeeded(
        document: some BaseDocumentProtocol,
        info: BlockInformation,
        text: String
    ) {
        guard PinkhaTextDirectionGate.isWritingDocument(document), !text.isEmpty else { return }
        scheduleAutomaticDirection(
            document: document,
            info: info,
            text: text,
            fallbackDirection: nil
        )
    }

    private static func scheduleAutomaticDirection(
        document: some BaseDocumentProtocol,
        info: BlockInformation,
        text: String,
        fallbackDirection: PinkhaLayoutDirection?
    ) {
        let initialMarker = PinkhaTextDirectionUIKitAdapter.marker(from: info.fields)
        if case .explicit = initialMarker { return }
        if !PinkhaAutomaticDirectionEligibility.markerMatchesStoredAlignment(
            marker: initialMarker,
            storedAlignment: info.horizontalAlignment.pinkhaMarkerAlignment ?? .left
        ) {
            return
        }
        guard sessionExplicitAlignments[info.id] == nil else { return }
        guard initialMarker != nil
                || SessionCreatedBlockIdsStorage.shared.contains(info.id)
                || PinkhaTextDirectionUIKitAdapter.isLocallyFabricatedUnlinkedBlock(
                    document: document,
                    info: info
                ) else {
            // A linked, marker-less host block is legacy-ambiguous. Do not even enqueue a
            // persistence task merely because its text changed.
            return
        }

        let taskKey = "\(document.objectId):\(info.id)"
        pendingTasks[taskKey]?.cancel()
        let generation = (generations[taskKey] ?? 0) &+ 1
        generations[taskKey] = generation

        pendingTasks[taskKey] = Task { @MainActor in
            do {
                try await Task.sleep(nanoseconds: 250_000_000)
            } catch {
                return
            }
            guard !Task.isCancelled, generations[taskKey] == generation else { return }
            guard sessionExplicitAlignments[info.id] == nil else { return }
            defer {
                if generations[taskKey] == generation {
                    pendingTasks[taskKey] = nil
                    generations[taskKey] = nil
                }
            }

            var currentInfo = document.infoContainer.get(id: info.id) ?? info
            var marker = PinkhaTextDirectionUIKitAdapter.marker(from: currentInfo.fields)
            if marker == nil, !SessionCreatedBlockIdsStorage.shared.contains(info.id) {
                // Virtual materialization and empty-block replacement register only after
                // their create/replace RPC succeeds. Briefly wait for that proof rather than
                // guessing from an edit; a legacy id never becomes eligible.
                for _ in 0..<4 {
                    do {
                        try await Task.sleep(nanoseconds: 250_000_000)
                    } catch {
                        return
                    }
                    guard !Task.isCancelled, generations[taskKey] == generation else { return }
                    currentInfo = document.infoContainer.get(id: info.id) ?? info
                    marker = PinkhaTextDirectionUIKitAdapter.marker(from: currentInfo.fields)
                    if marker != nil || SessionCreatedBlockIdsStorage.shared.contains(info.id) {
                        break
                    }
                }
            }
            // A marker-less block is eligible only if an existing host registry proves it
            // was created in this app session. Editing an old block never creates metadata.
            guard PinkhaAutomaticDirectionEligibility.shouldPersist(
                marker: marker,
                isSessionCreatedBlock: SessionCreatedBlockIdsStorage.shared.contains(info.id)
            ) else {
                return
            }
            if !PinkhaAutomaticDirectionEligibility.markerMatchesStoredAlignment(
                marker: marker,
                storedAlignment: currentInfo.horizontalAlignment.pinkhaMarkerAlignment ?? .left
            ) {
                return
            }

            let interfaceDirection: PinkhaLayoutDirection = fallbackDirection
                ?? (currentInfo.horizontalAlignment == .right ? .rightToLeft : .leftToRight)
            let direction = PinkhaTextDirectionUIKitAdapter.detectedDirection(
                for: text,
                fallback: interfaceDirection
            ) ?? interfaceDirection
            await persistAutomaticDirection(
                direction,
                document: document,
                info: currentInfo
            )
        }
    }

    static func markExplicitAlignmentIfNeeded(
        document: some BaseDocumentProtocol,
        blockIds: [String],
        alignment: LayoutAlignment,
        blockService: some BlockServiceProtocol
    ) async throws {
        guard PinkhaTextDirectionGate.isWritingDocument(document),
              let pinkhaAlignment = alignment.pinkhaMarkerAlignment else {
            return
        }

        let marker = PinkhaTextDirectionMarker.explicit(pinkhaAlignment)
        for blockId in blockIds {
            // This session-local intent also closes the gap if the metadata RPC fails. A
            // cold reopen safely falls back to the persisted host alignment.
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
                // Alignment is already committed by the host before this best-effort marker.
                // Do not roll it back or surface this as an alignment failure.
                log.error("Failed to persist explicit Pinkha alignment marker for block \(blockId): \(error)")
            }
        }
    }

    private static func persistAutomaticDirection(
        _ direction: PinkhaLayoutDirection,
        document: some BaseDocumentProtocol,
        info: BlockInformation
    ) async {
        let marker = PinkhaTextDirectionMarker.automatic(direction)

        do {
            let alignment = direction.automaticLayoutAlignment
            if info.horizontalAlignment != alignment {
                try await Container.shared.blockService().setAlign(
                    objectId: document.objectId,
                    blockIds: [info.id],
                    alignment: alignment
                )
            }

            var fields = document.infoContainer.get(id: info.id)?.fields ?? info.fields
            fields[PinkhaSchemaRoles.blockTextDirectionField] = Google_Protobuf_Value(
                stringValue: marker.storedValue
            )
            try await Container.shared.blockService().setFields(
                objectId: document.objectId,
                blockId: info.id,
                fields: fields
            )
        } catch {
            log.error("Failed to persist automatic Pinkha direction for block \(info.id): \(error)")
        }
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

private extension PinkhaLayoutDirection {
    var automaticLayoutAlignment: LayoutAlignment {
        self == .rightToLeft ? .right : .left
    }
}
