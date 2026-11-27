#if os(iOS)
import Foundation
import XCTest
import AnytypeCore
import Services
import ProtobufMessages
import SwiftProtobuf
import HanlinHostContracts
import HanlinPlatformContracts
import PinkhaHanlinCore
import PinkhaHanlinUI
@testable import Anytype

/// Original parser/converter + synthetic native protobuf fixtures only. These
/// cases do not call middleware, grant native consent, or qualify a real save.
@MainActor
final class PinkhaHanlinHeartSaveBodyTests: XCTestCase {
    func testOriginalHeartConverterPreservesStylesHebrewMarksListsAndCode() async throws {
        let body = try await fixture("# כותרת\n\n**שלום** _עולם_ ~~ישן~~ `x` [קישור](https://example.test/path) 👩🏽‍💻\n\n> quote\n\n- bullet\n\n1. first\n2. second\n\n- [x] checked\n\n```swift\nlet x = 1\n```\n")
        let view = try nativeView(body)
        let snapshot = try read(view)
        let receipt = try snapshot.verifiedBody(body)
        XCTAssertEqual(receipt.nativeReadbackSHA256, body.manifest.expectedBodyReadbackSHA256)
        XCTAssertEqual(receipt.blockReferences, body.blocks.indices.map { "native-body-\($0)" })
        XCTAssertNil(receipt.nativeVersionSHA256)
        XCTAssertEqual(try snapshot.blockReadbackSHA256(at: 1, plan: body), body.manifest.blockSHA256[1])
    }

    func testEmptyCodeDoesNotInventCharactersOrFailNativeAttributeSegmentation() throws {
        let request = try plan("```\n```")
        let document = try PinkhaHanlinSaveMessageDocument(title: request.title,
            blocks: [.init(kind: .code, text: .plain("", code: true))])
        let body = try PinkhaHanlinHeartSaveBody(plan: request, document: document)
        let snapshot = try read(nativeView(body))
        XCTAssertEqual(snapshot.body[0].text.text, "")
        XCTAssertTrue(snapshot.body[0].text.marks.marks.isEmpty)
        XCTAssertEqual(try snapshot.verifiedBody(body).nativeReadbackSHA256,
                       body.manifest.expectedBodyReadbackSHA256)
    }

    func testNativeEquivalentMarkSegmentationPassesButSurrogateSplitFails() async throws {
        let body = try await fixture("**😀שלום**")
        var view = try nativeView(body)
        let original = try XCTUnwrap(view.blocks[3].text.marks.marks.first)
        var first = original; first.range.to = 2
        var second = original; second.range.from = 2
        view.blocks[3].text.marks.marks = [first, second]
        XCTAssertNoThrow(try read(view).verifiedBody(body))
        first.range.to = 1; second.range.from = 1
        view.blocks[3].text.marks.marks = [first, second]
        XCTAssertThrowsError(try read(view).verifiedBody(body))
    }

    func testActualChangedTextStyleMarksAndTitleCannotBecomeSuccessfulReceipt() async throws {
        let body = try await fixture("**body**")
        let original = try nativeView(body)
        var changed = original; changed.blocks[3].text.text = "different"
        XCTAssertThrowsError(try read(changed).verifiedBody(body))
        changed = original; changed.blocks[3].text.style = .quote
        XCTAssertThrowsError(try read(changed).verifiedBody(body))
        changed = original; changed.blocks[3].text.marks.marks = []
        XCTAssertThrowsError(try read(changed).verifiedBody(body))
        changed = original; changed.details[0].details.fields["name"] = "newer title".protobufValue
        XCTAssertThrowsError(try read(changed).verifiedBody(body))
    }

    func testUnknownNativeFormattingForeignMarkerAndDifferentCodeLanguageRefuse() async throws {
        let body = try await fixture("```swift\nlet x = 1\n```\n")
        let original = try nativeView(body)
        var changed = original; changed.blocks[3].text.color = "red"
        XCTAssertThrowsError(try read(changed).verifiedBody(body))
        changed = original; changed.blocks[3].fields.fields["new-format"] = true.protobufValue
        XCTAssertThrowsError(try read(changed).verifiedBody(body))
        changed = original; changed.blocks[3].fields.fields[PinkhaHanlinHeartSaveBody.markerField] = "foreign".protobufValue
        XCTAssertThrowsError(try read(changed).verifiedBody(body))
        changed = original; changed.blocks[3].fields.fields["lang"] = "python".protobufValue
        XCTAssertThrowsError(try read(changed).verifiedBody(body))
    }

    func testNativeRootSpaceTypeAndSmartBlockKindRemainExact() async throws {
        let body = try await fixture("body")
        let original = try nativeView(body)
        var changed = original; changed.rootID = "another-page"
        XCTAssertThrowsError(try read(changed))
        changed = original; changed.details[0].details.fields["spaceId"] = "other-space".protobufValue
        XCTAssertThrowsError(try read(changed))
        changed = original; changed.details[0].details.fields["type"] = "other-type".protobufValue
        XCTAssertThrowsError(try read(changed))
        changed = original; changed.type = .archive
        XCTAssertThrowsError(try read(changed))
        changed = original; changed.details[0].details.fields["spaceId"] = "é".protobufValue
        XCTAssertThrowsError(try PinkhaHanlinHeartSaveReadback(view: changed,
            objectID: "native-page", spaceID: "e\u{301}", typeID: "native-page-type"))
    }

    func testCompleteBodyRefusesExtraMissingReorderedOrphanAndDuplicateRows() async throws {
        let body = try await fixture("first\n\nsecond")
        let original = try nativeView(body)
        var changed = original; changed.blocks[0].childrenIds.swapAt(1, 2)
        XCTAssertThrowsError(try read(changed).verifiedBody(body))
        changed = original; changed.blocks.removeLast()
        XCTAssertThrowsError(try read(changed))
        changed = original; changed.blocks.append(original.blocks[3])
        XCTAssertThrowsError(try read(changed))
        changed = original
        var orphan = original.blocks[3]; orphan.id = "orphan"
        changed.blocks.append(orphan)
        XCTAssertThrowsError(try read(changed))
        changed = original; changed.blocks[0].childrenIds.append(orphan.id); changed.blocks.append(orphan)
        XCTAssertThrowsError(try read(changed).verifiedBody(body))
    }

    func testFreshPagePreconditionDoesNotHidePlaceholderOrBodyInHeader() async throws {
        let body = try await fixture("body")
        var empty = try nativeView(body)
        empty.blocks = Array(empty.blocks.prefix(3)); empty.blocks[0].childrenIds = ["header"]
        XCTAssertEqual(try read(empty).verifyPrefix(body, count: 0), [])
        XCTAssertThrowsError(try read(empty).verifiedBody(body))
        var placeholder = try nativeView(body)
        placeholder.blocks[3].text.text = ""
        placeholder.blocks[3].fields.fields = [:]
        XCTAssertThrowsError(try read(placeholder).verifyPrefix(body, count: 0))
        var hidden = try nativeView(body)
        hidden.blocks[0].childrenIds = ["header"]
        hidden.blocks[1].childrenIds.append(hidden.blocks[3].id)
        XCTAssertThrowsError(try read(hidden))
    }

    func testUnrepresentableHeartLanguageIsRefusedBeforeAnyNativeDispatch() async throws {
        let request = try plan("```unqualified-language\nbody\n```\n")
        let parsed = try await PinkhaHanlinOriginalMarkdownSavePlanner.convert(request)
        XCTAssertThrowsError(try PinkhaHanlinHeartSaveBody(plan: request, document: parsed.document))
    }

    func testCanonicallyEquivalentButByteDifferentActualTextDoesNotPassReadback() async throws {
        let body = try await fixture("é")
        var changed = try nativeView(body)
        XCTAssertEqual(changed.blocks[3].text.text, "e\u{301}")
        changed.blocks[3].text.text = "e\u{301}"
        XCTAssertThrowsError(try read(changed).verifiedBody(body))
    }

    private func fixture(_ markdown: String) async throws -> PinkhaHanlinHeartSaveBody {
        let request = try plan(markdown)
        let parsed = try await PinkhaHanlinOriginalMarkdownSavePlanner.convert(request)
        return try .init(plan: request, document: parsed.document)
    }

    private func plan(_ markdown: String) throws -> PinkhaHanlinSaveMessagePlan {
        let session = HanlinHostSession(conversationID: UUID(), context: .init(
            namespace: try .init(app: PinkhaHanlinEngineNamespace.heart, account: "disposable-account",
                                 workspace: "disposable-space", space: "disposable-space"),
            sceneID: UUID(), generation: UUID()))
        return try .init(invocation: .init(request: .init(id: .init(validating: UUID().uuidString.lowercased()),
            logicalToolID: .init(providerInstanceID: .init(validating: "anytype.host"),
                                localToolID: .init(validating: "save-message")),
            aliasUsed: PinkhaHanlinSaveMessagePlan.alias, descriptorRevision: .init(1), routingTableRevision: .init(1),
            arguments: .object(["title": .string("TITLE"), "markdown": .string(markdown)]),
            origin: .assistantModel, deadline: .now.addingTimeInterval(20),
            limits: .init(timeoutMilliseconds: 20_000, maximumOutputBytes: 32_768)),
            session: session, runID: UUID(), step: 0, providerCallID: UUID().uuidString,
            writeGuarantee: .independentObjectCreation, expectedRevision: nil))
    }

    private func nativeView(_ body: PinkhaHanlinHeartSaveBody) throws -> Anytype_Model_ObjectView {
        var rows = try body.blocks.enumerated().map { index, info in
            var value = try XCTUnwrap(BlockInformationConverter.convert(information: info))
            value.id = "native-body-\(index)"
            return value
        }
        let root = Anytype_Model_Block.with {
            $0.id = "native-page"; $0.smartblock = .init()
            $0.childrenIds = ["header"] + rows.map(\.id)
        }
        let header = Anytype_Model_Block.with {
            $0.id = "header"; $0.layout = .init(); $0.childrenIds = ["native-title"]
        }
        let title = Anytype_Model_Block.with {
            $0.id = "native-title"; $0.text = .with { $0.style = .title; $0.text = body.document.title }
        }
        rows.insert(contentsOf: [root, header, title], at: 0)
        return .with {
            $0.rootID = "native-page"; $0.type = .page; $0.blocks = rows
            $0.details = [.with {
                $0.id = "native-page"
                $0.details = .with {
                    $0.fields = ["name": body.document.title.protobufValue,
                                 "spaceId": "disposable-space".protobufValue,
                                 "type": "native-page-type".protobufValue,
                                 "resolvedLayout": .with { $0.numberValue = Double(DetailsLayout.basic.rawValue) }]
                }
            }]
        }
    }

    private func read(_ view: Anytype_Model_ObjectView) throws -> PinkhaHanlinHeartSaveReadback {
        try .init(view: view, objectID: "native-page", spaceID: "disposable-space", typeID: "native-page-type")
    }
}
#endif
