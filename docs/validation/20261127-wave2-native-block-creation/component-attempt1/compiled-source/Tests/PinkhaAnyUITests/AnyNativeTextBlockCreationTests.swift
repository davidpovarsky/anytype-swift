import Foundation
import Testing
import PinkhaAnyEngine
import PinkhaAnyHost
import PinkhaAnyIntegration
import PinkhaKit
@testable import PinkhaAnyUI

@Suite("Native block choices use existing creation and rendering contracts")
struct AnyNativeTextBlockCreationTests {
    @Test func existingParagraphAndInspectorQuoteKeepTheirOriginalStyleCarrier() {
        for kind in [AnyNativeTextBlockKind.paragraph, .quote] {
            for direction in [AnyWritingDirection.natural, .leftToRight, .rightToLeft] {
                // This is the exact original createBlock style, before the UI
                // gained other choices. Inspector direction stays authoritative.
                let original: AnyJSON = .object([
                    "pinkhaWritingDirection": .string(direction.rawValue),
                    "pinkhaTextAlignment": .string("natural")
                ])
                #expect(kind.initialNativeStyle(direction: direction) == original)
            }
        }
    }

    @Test func distinctChoicesRoundTripThroughNativeIntentAndExistingDisplayPolicies() throws {
        let workspace = try AnyTorahWorkspace(accountID: "account", spaceID: "space")
        var fingerprints = Set<String>()
        let markerKinds: [AnyNativeTextBlockKind: String] = [
            .bulletedList: "•", .numberedList: "1.", .checklist: "☐", .quote: "❝"
        ]
        for kind in AnyNativeTextBlockKind.allCases {
            let intent = try AnyNativeBlockCreationIntent(workspace: workspace,
                mutationID: String(repeating: "1", count: 32), objectID: "document",
                type: kind.nativeType, text: "", style: kind.initialNativeStyle(direction: .rightToLeft),
                parentID: "parent", position: "PPPP")
            let restored = try JSONDecoder().decode(AnyNativeBlockCreationIntent.self,
                                                     from: JSONEncoder().encode(intent))
            #expect(restored == intent)
            let distinct = fingerprints.insert(restored.fingerprint).inserted
            #expect(distinct,
                    "Different creation choices must not share one protected journal intent.")
            #expect(restored.workspace == workspace && restored.objectID == "document")
            #expect(restored.parentID == "parent" && restored.position == "PPPP")

            // Native omits exactly empty text. The ordinary reader, marker and
            // writing policy must accept the same carrier before the first key.
            let native: AnyJSON = .object([
                "id": .string("new-block"), "type": .string(restored.type),
                "style": restored.style, "nav": .object([
                    "parentId": .string(restored.parentID), "pos": .string(restored.position)
                ]), "_ver": .object(["style": .string("native-version")]),
                "unrelatedMetadata": .object(["retained": .bool(true)])
            ])
            let block = try AnyEditorBlock(native: native)
            #expect(block.id == "new-block" && block.native == native)
            #expect(AnyNativeBlockMarkerPolicy.marker(for: block) == markerKinds[kind, default: ""])
            let writing = AnyNativeWritingPolicy.resolve(block: block, visibleText: "",
                interfaceDirection: .leftToRight, detectedTextDirection: nil)
            #expect(writing.baseWritingDirection == .rightToLeft,
                    "New type metadata must not replace the explicit native direction.")
            #expect(writing.alignment == .left,
                    "Automatic visual alignment still follows the existing app-language policy.")
        }
        #expect(fingerprints.count == AnyNativeTextBlockKind.allCases.count)
    }
}
