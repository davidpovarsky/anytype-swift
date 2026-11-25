#if DEBUG && canImport(UIKit)
import Foundation
import UIKit
import CryptoKit
import PinkhaKit
import PinkhaAnyHost

/// A bounded, explicitly opted-in observer for the owned UI acceptance account.
/// It reads the actual native snapshot and rendered attributed text only. It
/// never calls the engine, changes selection, supplies ACKs, or performs edits.
@MainActor
final class AnySemanticAnchorObservation {
    struct RenderedBlock {
        let id: String
        let text: NSAttributedString
        let selection: NSRange
        let isFirstResponder: Bool
    }

    private struct Mark: Codable, Equatable {
        let identitySHA256: String
        let location: Int
        let length: Int
        let textSHA256: String
    }

    let label: UILabel

    static func makeIfEnabled() -> AnySemanticAnchorObservation? {
        let process = ProcessInfo.processInfo
        let arguments = process.arguments
        guard process.environment["PINKHA_NATIVE_ANCHOR_OBSERVATION"] == "1",
              arguments.contains("--native-ui-tests"),
              let index = arguments.firstIndex(of: "--native-ui-test-scope"),
              index + 1 < arguments.count, UUID(uuidString: arguments[index + 1]) != nil else { return nil }
        return AnySemanticAnchorObservation()
    }

    private init() {
        label = UILabel()
        label.font = .systemFont(ofSize: 8)
        label.textColor = .secondaryLabel
        label.text = "Semantic anchor observation"
        label.isAccessibilityElement = true
        label.accessibilityIdentifier = "any-native-semantic-anchor-observation"
        label.accessibilityValue = #"{"state":"WAITING"}"#
    }

    func update(_ presentation: AnyDocumentPresentation, rendered: [RenderedBlock]) {
        var result: [String: Any] = [
            "schema": "any-semantic-anchor-native-rendered/v1",
            "mode": "read-only", "pid": ProcessInfo.processInfo.processIdentifier,
            "state": "WAITING", "nativeReadOrigin": "AnyDocumentPresentation.read",
            "engineCalls": 0, "mutations": 0, "selectionChanges": 0
        ]
        defer {
            if let data = try? JSONSerialization.data(withJSONObject: result, options: [.sortedKeys]),
               data.count <= 24_576, let value = String(data: data, encoding: .utf8) {
                label.accessibilityValue = value
            } else {
                label.accessibilityValue = #"{"state":"REFUSED_BOUNDS"}"#
            }
        }
        guard presentation.isMounted, !presentation.isLoading, !presentation.hasPendingEdits,
              !presentation.isCreatingTextAnchor, let read = presentation.read else { return }
        let native = read.snapshot
        result["spaceSHA256"] = Self.hash(native.spaceID)
        result["objectSHA256"] = Self.hash(native.objectID)
        result["nativeVersionSHA256"] = Self.hash(read.nativeVersion)
        result["generation"] = read.generation.uuidString
        guard native.blocks.count <= 64, rendered.count <= 64,
              native.unreachableIDs.isEmpty,
              Set(rendered.map(\.id)).count == rendered.count,
              Set(native.depthFirstIDs) == Set(rendered.map(\.id)) else {
            result["state"] = "PARTIAL_RENDER"; return
        }
        let byID = Dictionary(uniqueKeysWithValues: rendered.map { ($0.id, $0) })
        var blocks: [[String: Any]] = []
        var nativeCount = 0, renderedCount = 0
        do {
            for id in native.depthFirstIDs {
                guard let block = native.blocks.first(where: { $0.id == id }), let actual = byID[id],
                      actual.text.length <= 65_536 else {
                    result["state"] = "REFUSED_BOUNDS"; return
                }
                let projection = block.type == "code"
                    ? AnyInlineMarkdown(literal: block.text) : AnyInlineMarkdown(block.text)
                let expected = try projection.semanticText()
                var observedMarks: [PinkhaSemanticText.Mark] = []
                var invalidMarker = false
                actual.text.enumerateAttribute(.link, in: NSRange(location: 0, length: actual.text.length)) { value, range, _ in
                    let string = (value as? URL)?.absoluteString ?? (value as? String)
                    guard let string, let url = URL(string: string),
                          PinkhaSemanticTextAnchor.isReservedMarkerURL(url) else { return }
                    guard let anchor = try? PinkhaSemanticTextAnchor(markerURL: url) else {
                        invalidMarker = true; return
                    }
                    observedMarks.append(.init(anchor: anchor, range: range))
                }
                guard !invalidMarker, observedMarks.count <= 128 else {
                    result["state"] = "INVALID_RENDERED_MARKER"; return
                }
                let observed = try PinkhaSemanticText(text: actual.text.string, marks: observedMarks)
                let expectedMarks = Self.marks(expected), actualMarks = Self.marks(observed)
                guard expected == observed, expectedMarks == actualMarks else {
                    result["state"] = "NATIVE_RENDER_MISMATCH"; return
                }
                nativeCount += expectedMarks.count; renderedCount += actualMarks.count
                let expectedJSON = try JSONSerialization.jsonObject(with: JSONEncoder().encode(expectedMarks))
                let actualJSON = try JSONSerialization.jsonObject(with: JSONEncoder().encode(actualMarks))
                blocks.append([
                    "blockSHA256": Self.hash(id), "textSHA256": Self.hash(actual.text.string),
                    "sourceSHA256": Self.hash(block.text), "utf16Length": actual.text.length,
                    "nativeMarks": expectedJSON, "renderedMarks": actualJSON,
                    "selectionLocation": actual.selection.location, "selectionLength": actual.selection.length,
                    "isFirstResponder": actual.isFirstResponder
                ])
            }
            result["state"] = "MATCHED"
            result["nativeMarkCount"] = nativeCount
            result["renderedMarkCount"] = renderedCount
            result["blocks"] = blocks
        } catch {
            result["state"] = "REFUSED_INVALID_SNAPSHOT"
        }
    }

    private static func marks(_ text: PinkhaSemanticText) -> [Mark] {
        text.marks.map { mark in
            Mark(identitySHA256: hash(mark.anchor.markerString),
                 location: mark.range.location, length: mark.range.length,
                 textSHA256: hash((text.text as NSString).substring(with: mark.range)))
        }
    }

    private static func hash(_ value: String) -> String {
        SHA256.hash(data: Data(value.utf8)).map { String(format: "%02x", $0) }.joined()
    }
}
#endif
