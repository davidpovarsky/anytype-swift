import Foundation
import Testing
import PinkhaAnyEngine
import PinkhaAnyHost
@testable import PinkhaAnyUI

@Suite("Native list markers reflect exact persisted style")
struct AnyNativeBlockMarkerTests {
    private func block(_ type: String, _ style: [String: AnyJSON] = [:]) throws -> AnyEditorBlock {
        try .init(native: .object(["id": .string("block"), "type": .string(type), "text": .string("text"),
            "nav": .object(["parentId": .string(""), "pos": .string("PPPP")]),
            "style": .object(style), "_ver": .object(["text": .string("v1")])]))
    }
    @Test func checkedAndUncheckedTasksUseNativeBooleans() throws {
        #expect(AnyNativeBlockMarkerPolicy.marker(for: try block("check_list_item", ["checked": .bool(true)])) == "☑")
        #expect(AnyNativeBlockMarkerPolicy.marker(for: try block("check_list_item", ["checked": .bool(false)])) == "☐")
        #expect(AnyNativeBlockMarkerPolicy.marker(for: try block("check_list_item", ["checked": .string("true")])) == "☐")
    }
    @Test func orderedListsAcceptZeroCustomStartAndMaximum() throws {
        for value in [Int64(0), 7, 999_999_999] {
            #expect(AnyNativeBlockMarkerPolicy.marker(for: try block("list_item", [
                "ordered": .bool(true), "number": .integer(value)])) == "\(value).")
        }
        #expect(AnyNativeBlockMarkerPolicy.marker(for: try block("list_item", ["ordered": .bool(true)])) == "1.")
    }
    @Test func fractionalJSONNumbersFollowNativeTruncationBeforeBounds() throws {
        #expect(AnyNativeBlockMarkerPolicy.marker(for: try block("list_item", [
            "ordered": .bool(true), "number": .number(2.75)])) == "2.")
        #expect(AnyNativeBlockMarkerPolicy.marker(for: try block("list_item", [
            "ordered": .bool(true), "number": .number(-0.5)])) == "0.")
    }
    @Test func invalidNumbersDefaultAndUnorderedIgnoresNumber() throws {
        for value in [AnyJSON.integer(-1), .integer(1_000_000_000), .string("9"), .null] {
            #expect(AnyNativeBlockMarkerPolicy.marker(for: try block("list_item", [
                "ordered": .bool(true), "number": value])) == "1.")
        }
        #expect(AnyNativeBlockMarkerPolicy.marker(for: try block("list_item", ["number": .integer(9)])) == "•")
    }
    @Test func unknownMetadataAndOtherMarkersAreRetained() throws {
        let value = try block("quote", ["future": .object(["n": .integer(9_007_199_254_740_993)])])
        let original = value.native
        #expect(AnyNativeBlockMarkerPolicy.marker(for: value) == "❝")
        #expect(value.native == original)
        #expect(AnyNativeBlockMarkerPolicy.marker(for: try block("paragraph")) == "")
    }
}
