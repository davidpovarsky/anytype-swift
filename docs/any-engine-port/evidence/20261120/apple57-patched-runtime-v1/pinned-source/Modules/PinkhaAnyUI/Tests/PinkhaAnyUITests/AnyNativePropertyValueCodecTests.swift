import Foundation
import Testing
import PinkhaAnyEngine
import PinkhaAnyHost
import PinkhaAnyIntegration
@testable import PinkhaAnyUI

@Suite("Native property text preserves typed and unknown values")
struct AnyNativePropertyValueCodecTests {
    @Test func stringValuesRemainLiteralIncludingHebrewAndJSONLookingText() throws {
        let source = "{\"שלום\":9007199254740993} 😀"
        let value = try AnyNativePropertyValueCodec.parse(source, kind: .string)
        #expect(value == .string(source))
        #expect(try AnyNativePropertyValueCodec.text(value, kind: .string) == source)
    }
    @Test func exactSignedIntegerIsNotFirstRoundedThroughDouble() throws {
        let value = try AnyNativePropertyValueCodec.parse("9007199254740993", kind: .number)
        #expect(value == .integer(9_007_199_254_740_993))
    }
    @Test func unknownNestedPreciseNumberAndDuplicateKeysAreRefused() throws {
        for value in [
            #"{"future":{"decimal":0.123456789012345678901234567890}}"#,
            #"{"future":1,"future":2}"#,
            #"{"value":18446744073709551617}"#
        ] {
            #expect(throws: (any Error).self) {
                try AnyNativePropertyValueCodec.parse(value, kind: .object)
            }
        }
    }
    @Test func wrongNativeKindsCannotBeCoercedByTheEditor() throws {
        for (text, kind) in [("true", AnyNativePropertyDefinition.Kind.number),
                             ("1", .boolean), ("{}", .array), ("[]", .object)] {
            #expect(throws: (any Error).self) {
                try AnyNativePropertyValueCodec.parse(text, kind: kind)
            }
        }
    }
    @Test func structuredFutureFieldsKeepTheirTypeAndNestedValues() throws {
        let value = try AnyNativePropertyValueCodec.parse(
            #"[{"future":{"label":"שָׁלוֹם","exact":9007199254740993}},null,true]"#, kind: .array)
        #expect(value.array?[0]["future"]?["exact"] == .integer(9_007_199_254_740_993))
        #expect(value.array?[0]["future"]?["label"]?.string == "שָׁלוֹם")
        #expect(try AnyNativePropertyValueCodec.parse(
            AnyNativePropertyValueCodec.text(value, kind: .array), kind: .array) == value)
    }
    @Test func nativeDateWrapperAndExplicitTimezoneAreRequired() throws {
        #expect(try AnyNativePropertyValueCodec.parse("2026-11-19T10:20:30Z", kind: .datetime) ==
                .object(["$date": .string("2026-11-19T10:20:30Z")]))
        #expect(try AnyNativePropertyValueCodec.parse(#"{"$date":1234567890000}"#, kind: .datetime) ==
                .object(["$date": .integer(1_234_567_890_000)]))
        #expect(throws: (any Error).self) {
            try AnyNativePropertyValueCodec.parse("2026-11-19", kind: .datetime)
        }
        #expect(throws: (any Error).self) {
            try AnyNativePropertyValueCodec.parse(#"{"$date":"2026-11-19T10:20:30Z","unknown":1}"#, kind: .datetime)
        }
    }
    @Test func unknownKindAndOversizedInputRemainExplicitlyUnsupported() throws {
        #expect(throws: (any Error).self) {
            try AnyNativePropertyValueCodec.parse("null", kind: nil)
        }
        #expect(throws: (any Error).self) {
            try AnyNativePropertyValueCodec.parse(String(repeating: "א", count: 65_537), kind: .string)
        }
    }
}
