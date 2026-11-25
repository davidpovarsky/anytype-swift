import Foundation
import Testing
@testable import PinkhaKit

struct TorahSourceJSONGuardTests {
    @Test func equivalentDecimalSpellingsPreserveExactValues() throws {
        try TorahSourceJSONGuard.validateRoundTrip(
            original: Data(#"{"a":1.00e3,"b":-0,"c":0.0001000,"quoted":"9007199254740993","nested":[7,true,null]}"#.utf8),
            encoded: Data(#"{"a":1000,"b":0,"c":1e-4,"quoted":"9007199254740993","nested":[7.0,true,null]}"#.utf8))
    }

    @Test func changedPrecisionKeepsExactJSONPointer() {
        #expect(throws: TorahSourceJSONGuardError.numericPrecisionWouldChange(path: "/a~1b~0c/0")) {
            try TorahSourceJSONGuard.validateRoundTrip(
                original: Data(#"{"a/b~c":[9007199254740993]}"#.utf8),
                encoded: Data(#"{"a/b~c":[9007199254740992]}"#.utf8))
        }
    }

    @Test func escapedDuplicateKeysRefuseEitherInput() {
        let repeated = Data(#"{"future":1,"\u0066uture":2}"#.utf8)
        let unique = Data(#"{"future":1}"#.utf8)
        for (original, encoded) in [(repeated, unique), (unique, repeated)] {
            #expect(throws: TorahSourceJSONGuardError.duplicateJSONKey(path: "/future")) {
                try TorahSourceJSONGuard.validateRoundTrip(original: original, encoded: encoded)
            }
        }
    }

    @Test func canonicalUnknownNumbersCannotLosePrecision() throws {
        let codec = TorahAssociationPayloadCodec()
        let location = TorahAssociationLocation(spaceId: "space", target: .object(objectId: "object"))
        for token in ["9007199254740993", "0.12345678901234567890123456789",
                      "100000000000000000000000000000000000001"] {
            let original = Data("{\"version\":2,\"records\":[],\"futureNumber\":\(token)}".utf8)
            let decoded = try codec.decodeCanonicalDocument(original, legacyLocation: location)
            #expect(throws: TorahSourceJSONGuardError.numericPrecisionWouldChange(path: "/futureNumber")) {
                try TorahSourceJSONGuard.validateCanonicalPayload(original, decoded: decoded)
            }
        }
    }

    @Test func canonicalNumbersRemainSafeAcrossCodecAndGuard() throws {
        let codec = TorahAssociationPayloadCodec()
        let original = Data(#"{"version":2,"records":[],"future":{"a":1.00e3,"b":-0,"c":0.0001000}}"#.utf8)
        let decoded = try codec.decodeCanonicalDocument(original,
            legacyLocation: .init(spaceId: "space", target: .object(objectId: "object")))
        try TorahSourceJSONGuard.validateCanonicalPayload(original, decoded: decoded)
    }

    @Test func malformedJSONNeverBecomesAValidEmptyComparison() {
        for raw in [#"{"a":01}"#, #"{"a":1.}"#, #"{"a":1e}"#, #"{"a":true} trailing"#] {
            #expect(throws: TorahAssociationPayloadCodecError.malformedJSON) {
                try TorahSourceJSONGuard.validateRoundTrip(original: Data(raw.utf8), encoded: Data("{}".utf8))
            }
        }
    }
}
