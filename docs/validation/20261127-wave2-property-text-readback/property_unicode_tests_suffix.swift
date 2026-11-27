
// These are typed Host receipt fixtures, not native transport or mounted UI proof.
extension NativePropertyStoreTests {
    private func unicodePropertySnapshot(key: AnyNativePropertyKey, kind: String,
                                         value: AnyJSON?, sequence: Int64) throws -> AnyNativePropertySnapshot {
        let original = try snapshot()
        var raw = try XCTUnwrap(original.raw.object)
        var namespace = try XCTUnwrap(raw[key.ownerID]?.object)
        namespace[key.propertyID] = value
        raw[key.ownerID] = .object(namespace)
        raw["_applySeq"] = .integer(sequence)
        var definitions = original.rows.map(\.definition).filter { $0.key != key }
        definitions.append(try definition(key.ownerID, key.propertyID, kind: kind))
        return try AnyNativePropertyStore.materialize(raw: .object(raw), objectID: original.objectID,
            catalog: original.catalog, definitions: definitions, policy: policy(), canWrite: true)
    }

    private func unicodePropertyReceipt(key: AnyNativePropertyKey, kind: String,
                                        before: AnyJSON, requested: AnyJSON,
                                        actual: AnyJSON?) throws -> (AnyPreparedPropertyEdit, AnyPropertyEditReceipt) {
        let subject = try store()
        let initial = try unicodePropertySnapshot(key: key, kind: kind, value: before, sequence: 17)
        let edit = try subject.prepareSetValue(initial, key: key, value: requested)
        let accepted = try AnyNativePropertyStore.acceptedFence(.object([
            "engineStartedAt": .string(initial.engineStartedAt),
            "propertiesVersion": initial.nativeVersion, "applySeq": .integer(18)
        ]), original: edit.fence)
        let readback = try unicodePropertySnapshot(key: key, kind: kind, value: actual, sequence: 18)
        XCTAssertEqual(readback.fence, accepted)
        XCTAssertEqual(try AnyHostCanonical.bytes(try XCTUnwrap(edit.patch[key.propertyID])),
                       try AnyHostCanonical.bytes(requested))
        return (edit, subject.receipt(for: edit, accepted: accepted, readback: readback))
    }

    private func requireUnverifiedUnicodeReceipt(_ receipt: AnyPropertyEditReceipt,
                                                 file: StaticString = #filePath, line: UInt = #line) {
        XCTAssertEqual(receipt.readback, .nativeAcceptedButCurrentStateUnverified, file: file, line: line)
        XCTAssertNil(receipt.snapshot, file: file, line: line)
        XCTAssertNil(receipt.undo, file: file, line: line)
    }

    private func requireVerifiedUnicodeReceipt(_ receipt: AnyPropertyEditReceipt,
                                               key: AnyNativePropertyKey, before: AnyJSON,
                                               actual: AnyJSON?, file: StaticString = #filePath,
                                               line: UInt = #line) throws {
        XCTAssertEqual(receipt.readback, .verifiedCurrent, file: file, line: line)
        let current = try XCTUnwrap(receipt.snapshot, file: file, line: line)
        if let actual {
            XCTAssertEqual(try AnyHostCanonical.bytes(try XCTUnwrap(current.raw[key.ownerID]?[key.propertyID])),
                           try AnyHostCanonical.bytes(actual), file: file, line: line)
        } else {
            XCTAssertNil(current.raw[key.ownerID]?[key.propertyID], file: file, line: line)
        }
        let inverse = try XCTUnwrap(receipt.undo, file: file, line: line)
        XCTAssertEqual(inverse.fence, current.fence, file: file, line: line)
        XCTAssertEqual(try AnyHostCanonical.bytes(try XCTUnwrap(inverse.patch[key.propertyID])),
                       try AnyHostCanonical.bytes(before), file: file, line: line)
    }

    func testStringReadbackRequiresExactUTF8BeforeCreatingUndo() throws {
        let name = try AnyNativePropertyKey(ownerID: "any", propertyID: "name")
        // The second owner is a typed fixture for a mapped string URL value.
        // This test does not claim native imported-Type mapping or URL-open proof.
        let url = try AnyNativePropertyKey(ownerID: "collection-a", propertyID: "mapped-url-fixture")
        let pairs: [(AnyNativePropertyKey, String, String)] = [
            (name, "Caf\u{00E9}", "Cafe\u{0301}"),
            (name, "\u{05E9}\u{05C1}\u{05B0}", "\u{05E9}\u{05B0}\u{05C1}"),
            (url, "https://example.invalid/Caf\u{00E9}", "https://example.invalid/Cafe\u{0301}")
        ]
        for (key, before, requested) in pairs {
            XCTAssertEqual(before, requested) // Establish the old canonical-equality counterexample.
            XCTAssertFalse(before.utf8.elementsEqual(requested.utf8))
            let (edit, wrong) = try unicodePropertyReceipt(key: key, kind: "string",
                before: .string(before), requested: .string(requested), actual: .string(before))
            XCTAssertEqual(try AnyHostCanonical.bytes(try XCTUnwrap(edit.inversePatch[key.propertyID])),
                           try AnyHostCanonical.bytes(.string(before)))
            requireUnverifiedUnicodeReceipt(wrong)
            let (_, exact) = try unicodePropertyReceipt(key: key, kind: "string",
                before: .string(before), requested: .string(requested), actual: .string(requested))
            try requireVerifiedUnicodeReceipt(exact, key: key, before: .string(before), actual: .string(requested))
        }
    }

    func testNestedStringAndKeyReadbackRequiresExactUTF8BeforeCreatingUndo() throws {
        let key = try AnyNativePropertyKey(ownerID: "collection-a", propertyID: "unicode-structure-fixture")
        let nfc = "Caf\u{00E9}", nfd = "Cafe\u{0301}"
        let pairs: [(String, AnyJSON, AnyJSON)] = [
            ("array", .array([.object(["text": .string(nfc)])]),
                      .array([.object(["text": .string(nfd)])])),
            ("object", .object(["text": .array([.string(nfc)])]),
                       .object(["text": .array([.string(nfd)])])),
            ("object", .object([nfc: .integer(7)]), .object([nfd: .integer(7)]))
        ]
        for (kind, before, requested) in pairs {
            XCTAssertEqual(before, requested) // Includes canonical equality of dictionary keys.
            XCTAssertNotEqual(try AnyHostCanonical.bytes(before), try AnyHostCanonical.bytes(requested))
            let (_, wrong) = try unicodePropertyReceipt(key: key, kind: kind,
                before: before, requested: requested, actual: before)
            requireUnverifiedUnicodeReceipt(wrong)
            let (_, exact) = try unicodePropertyReceipt(key: key, kind: kind,
                before: before, requested: requested, actual: requested)
            try requireVerifiedUnicodeReceipt(exact, key: key, before: before, actual: requested)
        }
    }

    func testPropertyReceiptRetainsDocumentedNativeNormalizationAndUnsetRules() throws {
        let key = try AnyNativePropertyKey(ownerID: "collection-a", propertyID: "native-representation-fixture")
        let dateBefore: AnyJSON = .object(["$date": .string("2026-11-18T10:00:00.000Z")])
        let pairs: [(String, AnyJSON, AnyJSON, AnyJSON?)] = [
            ("number", .integer(3), .number(4.0), .integer(4)),
            ("number", .integer(3), .integer(4), .number(4.0)),
            ("number", .number(1.0), .number(-0.0), .number(0.0)),
            ("datetime", dateBefore,
                .object(["$date": .string("2026-11-19T12:00:00.123999+02:00")]),
                .object(["$date": .string("2026-11-19T10:00:00.123Z")])),
            ("string", .string("original"), .null, nil)
        ]
        for (kind, before, requested, actual) in pairs {
            let (_, receipt) = try unicodePropertyReceipt(key: key, kind: kind,
                before: before, requested: requested, actual: actual)
            try requireVerifiedUnicodeReceipt(receipt, key: key, before: before, actual: actual)
        }
        // An explicit stored null is not the native absent-property result of unset.
        let (_, storedNull) = try unicodePropertyReceipt(key: key, kind: "string",
            before: .string("original"), requested: .null, actual: .null)
        requireUnverifiedUnicodeReceipt(storedNull)
    }

    func testPropertyValueComparisonUsesTheExistingCanonicalDepthLimit() throws {
        func nested(_ depth: Int) -> AnyJSON {
            (0..<depth).reduce(AnyJSON.string("exact")) { value, _ in .array([value]) }
        }
        let atLimit = nested(32), pastLimit = nested(33)
        XCTAssertNoThrow(try AnyHostCanonical.bytes(atLimit))
        XCTAssertTrue(AnyNativePropertyStore.nativeValueMatches(atLimit, requested: atLimit))
        XCTAssertThrowsError(try AnyHostCanonical.bytes(pastLimit))
        XCTAssertFalse(AnyNativePropertyStore.nativeValueMatches(pastLimit, requested: pastLimit))
        let key = try AnyNativePropertyKey(ownerID: "collection-a", propertyID: "depth-fixture")
        let captured = try unicodePropertySnapshot(key: key, kind: "array", value: .array([]), sequence: 17)
        XCTAssertThrowsError(try store().prepareSetValue(captured, key: key, value: pastLimit))
        // Raw native records include their namespace containers in the same bound.
        XCTAssertThrowsError(try unicodePropertySnapshot(key: key, kind: "array", value: pastLimit, sequence: 18))
    }
}
