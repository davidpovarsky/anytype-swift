
import PinkhaTorahPresentation

/// G02 observes the three original writing Objects after real Properties UI.
/// It never creates, restores or selects an account, provisions schema, or calls
/// an association/property mutation. Files written here are test evidence only.
@Suite("G02 original writing Properties readback", .serialized,
       .enabled(if: ProcessInfo.processInfo.environment["PINKHA_G02_NATIVE_READBACK"] == "1"))
struct TorahWritingPropertiesReadbackTests {
    @MainActor
    @Test("Read the actual baseline or verify exactly one document Word unlink per writing Object")
    func observeOriginalWritingProperties() async throws {
        try await G02WritingPropertiesReadback.observe()
    }
}

private enum G02WritingPropertiesReadback {
    static let roles = ["chiddush", "article", "research"]
    static let controllerKeys = [
        "SOURCE_SHA", "RUN_ID", "RUN_ATTEMPT", "TOKEN", "SIMULATOR_UDID", "LANE",
        "ADMISSION_SHA256", "PREPARATION_SHA256", "INVOCATION_SHA256",
        "OWNED_SIMULATOR_SHA256", "FIXTURE_SHA256"
    ]
    // These clocks can change during ordinary opening and the confirmed unlink.
    // Their original/current values remain in the full snapshots and receipt.
    static let clockKeys: Set<String> = ["lastModifiedDate", "lastOpenedDate", "lastUsedDate"]
    // Exact8ac core/pinkha/torahindex/index.go derives this from canonical bytes.
    static let canonicalHashKey = "_pinkhaTorahCanonicalHash"
    static let maximumReceiptBytes = 4 * 1_024 * 1_024

    struct Fixture: Decodable {
        struct ReservedTypeSubject: Decodable { let objectId: String }
        let spaceId: String
        let documents: [String: String]
        let names: [String: String]
        let types: [String: String]
        let sourceLabel: String
        let topicLabel: String
        let typeSwitch: ReservedTypeSubject
    }

    struct Seed: Decodable {
        struct Document: Decodable {
            let objectID: String
            let typeID: String
            let name: String
            let sourceLabel: String
            let topicLabel: String
            let wordLabel: String
            let tagPropertyName: String
            let tagName: String
        }
        let schema: String
        let phase: String
        let spaceID: String
        let controller: [String: String]
        let documents: [String: Document]
    }

    struct Unlink: Decodable {
        struct Document: Decodable {
            let objectID: String
            let typeID: String
            let name: String
            let wordRecordIDFromNativeBaseline: String
            let wordIdentityFromNativeBaseline: String
            let tagIDFromNativeBaseline: String
            let previousPID: Int32
            let appPID: Int32
        }
        let schema: String
        let phase: String
        let spaceID: String
        let controller: [String: String]
        let nativeBaselineSHA256: String
        let seedUIReceiptSHA256: String
        let nativePersistencePostflightRequired: Bool
        let documents: [String: Document]
    }

    struct NativeObject: Codable {
        let objectID: String
        let spaceID: String
        let typeID: String
        let name: String
        let fields: [String: TorahJSONValue]
        let protobufDetailsJSON: String
        let protobufDetailsSHA256: String
    }

    struct Document: Codable {
        let native: NativeObject
        let canonicalRaw: String
        let canonicalSHA256: String
        let projections: [String: [String]]
        let tag: NativeObject
    }

    struct State: Codable {
        let accountID: String
        let spaceID: String
        let canonicalPropertyKey: String
        let canonicalPropertyID: String
        let tagProperty: NativeObject
        let documents: [String: Document]
    }

    struct Receipt: Codable {
        let schema: String
        let status: String
        let phase: String
        let controller: [String: String]
        let fixtureSHA256: String
        let seedUIReceiptSHA256: String
        let nativeBaselineSHA256: String?
        let unlinkUIReceiptSHA256: String?
        let processID: Int32
        let directories: NativeTypePreservation.Directories
        let verifierCallsMutationAPI: Bool
        let scope: String
        let permittedClockKeys: [String]
        let state: State
    }

    struct UIBaseline: Encodable {
        struct Document: Encodable {
            let objectID: String
            let typeID: String
            let name: String
            let sourceLabel: String
            let topicLabel: String
            let wordRecordID: String
            let wordIdentity: String
            let wordLabel: String
            let tagPropertyName: String
            let tagID: String
            let tagName: String
        }
        let schema: String
        let nativeBaselineSHA256: String
        let seedUIReceiptSHA256: String
        let controller: [String: String]
        let spaceID: String
        let documents: [String: Document]
    }

    static func sha256(_ data: Data) -> String { NativeTypePreservation.sha256(data) }

    static func input(_ name: String, maximum: Int = 262_144) throws -> Data {
        let raw = try #require(ProcessInfo.processInfo.environment[name])
        let data = Data(raw.utf8)
        try #require(!data.isEmpty && data.count <= maximum)
        return data
    }

    static func hashedInput(_ name: String) throws -> Data {
        let data = try input(name)
        try #require(sha256(data) == ProcessInfo.processInfo.environment[name.replacingOccurrences(of: "_JSON", with: "_SHA256")])
        return data
    }

    static func controller() throws -> [String: String] {
        let env = ProcessInfo.processInfo.environment
        var result = [String: String]()
        for key in controllerKeys {
            let value = try #require(env["PINKHA_UI27_STARTUP_" + key])
            try #require(!value.isEmpty)
            result[key] = value
        }
        let source = try #require(result["SOURCE_SHA"])
        let token = try #require(result["TOKEN"])
        let udid = try #require(result["SIMULATOR_UDID"])
        try #require(source.count == 40 && source.allSatisfy(\.isHexDigit))
        try #require(token.count == 32 && token.allSatisfy(\.isHexDigit))
        try #require(UUID(uuidString: udid) != nil && env["SIMULATOR_UDID"] == udid)
        try #require(result["LANE"] == "properties")
        for key in ["RUN_ID", "RUN_ATTEMPT"] {
            let value = try #require(result[key])
            try #require(value.allSatisfy(\.isNumber))
        }
        for key in controllerKeys where key.hasSuffix("SHA256") {
            let value = try #require(result[key])
            try #require(value.count == 64 && value.allSatisfy(\.isHexDigit))
        }
        return result
    }

    static func write<T: Encodable>(_ value: T, to url: URL) throws -> Data {
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.sortedKeys, .withoutEscapingSlashes]
        let data = try encoder.encode(value)
        try #require(!data.isEmpty && data.count <= maximumReceiptBytes)
        try #require(!FileManager.default.fileExists(atPath: url.path))
        try data.write(to: url, options: .atomic)
        return data
    }

    static func payload(_ document: Document) throws -> TorahCanonicalAssociationsPayload {
        let data = Data(document.canonicalRaw.utf8)
        try #require(!data.isEmpty && data.count <= 1_048_576 && sha256(data) == document.canonicalSHA256)
        let envelope = try JSONDecoder().decode([String: TorahJSONValue].self, from: data)
        try #require(envelope["version"] == .number(2))
        let location = TorahAssociationLocation(spaceId: document.native.spaceID,
            target: .object(objectId: document.native.objectID))
        let value = try TorahAssociationPayloadCodec().decodeCanonicalDocument(data, legacyLocation: location)
        try #require(value.records.count <= 1_000 && Set(value.records.map { $0.item.id }).count == value.records.count)
        try #require(value.records.allSatisfy {
            $0.spaceId == document.native.spaceID && $0.objectId == document.native.objectID &&
            !$0.item.id.isEmpty && ($0.blockId == nil || $0.blockId?.isEmpty == false)
        })
        return value
    }

    static func documentItems(_ document: Document) throws -> [TorahAssociationItem] {
        try payload(document).records.filter { $0.blockId == nil }.map(\.item)
    }

    static func item(_ kind: TorahAssociationKind, in document: Document) throws -> TorahAssociationItem {
        let values = try documentItems(document).filter { $0.kind == kind }
        try #require(values.count == 1)
        let value = try #require(values.first)
        try #require(value.providerID == "sefaria" && value.createdAt != nil)
        return value
    }

    static func labels(_ document: Document) throws -> [String: TorahJSONValue] {
        let raw = try #require(document.native.fields[TorahNativePropertyDefinition.labelsKey])
        guard case .string(let json) = raw else {
            throw NativeAcceptanceError.conditionTimeout("G02 native derived label JSON string")
        }
        return try JSONDecoder().decode([String: TorahJSONValue].self, from: Data(json.utf8))
    }

    static func stableFields(_ object: NativeObject, excluding keys: Set<String> = []) throws -> [String: TorahJSONValue] {
        let data = Data(object.protobufDetailsJSON.utf8)
        try #require(sha256(data) == object.protobufDetailsSHA256)
        let decoded = try JSONDecoder().decode([String: TorahJSONValue].self, from: data)
        try #require(decoded == object.fields)
        for key in clockKeys {
            switch object.fields[key] {
            case nil, .null?: break
            case .number(let value)?: try #require(value.isFinite && value >= 0)
            default: throw NativeAcceptanceError.conditionTimeout("G02 malformed native clock: " + key)
            }
        }
        return object.fields.filter { !clockKeys.contains($0.key) && !keys.contains($0.key) }
    }

    @MainActor
    static func readObject(_ objectID: String, spaceID: String) async throws -> (NativeObject, ObjectDetails) {
        let response = try await ClientCommands.objectShow(.with {
            $0.contextID = objectID; $0.objectID = objectID; $0.spaceID = spaceID
        }).invoke()
        let rows = response.objectView.details.filter { $0.id == objectID }
        try #require(rows.count == 1)
        let row = try #require(rows.first)
        let details = try ObjectDetails(protobufStruct: row.details)
        try #require(details.id == objectID && details.spaceId == spaceID)
        let raw = try row.details.jsonUTF8Data()
        try #require(!raw.isEmpty && raw.count <= 1_048_576)
        let fields = try JSONDecoder().decode([String: TorahJSONValue].self, from: raw)
        let text = try #require(String(data: raw, encoding: .utf8))
        return (.init(objectID: details.id, spaceID: details.spaceId, typeID: details.type,
                      name: details.name, fields: fields, protobufDetailsJSON: text,
                      protobufDetailsSHA256: sha256(raw)), details)
    }

    @MainActor
    static func readState(fixture: Fixture) async throws -> State {
        let accountID = Container.shared.accountManager().account.id
        try #require(!accountID.isEmpty)
        let loadedManifest = try await PinkhaSpaceManifestStore().loadManifest(spaceId: fixture.spaceId)
        let manifest = try #require(loadedManifest)
        try #require(manifest.spaceId == fixture.spaceId && manifest.isFullyProvisioned)
        try #require(roles.allSatisfy { manifest.registeredDocumentTypes[$0] == fixture.types[$0] })
        let descriptorValue = try await AnytypeTorahNativePropertyProvisioningStore().property(key: "tag", spaceId: fixture.spaceId)
        let descriptor = try #require(descriptorValue)
        let (tagProperty, propertyDetails) = try await readObject(descriptor.id, spaceID: fixture.spaceId)
        try #require(propertyDetails.stringValue(for: "relationKey") == "tag")
        var documents = [String: Document]()
        for role in roles {
            let objectID = try #require(fixture.documents[role])
            let (native, details) = try await readObject(objectID, spaceID: fixture.spaceId)
            let tags = details.stringArrayValue(for: "tag")
            try #require(tags.count == 1)
            let tagID = try #require(tags.first)
            let (tag, tagDetails) = try await readObject(tagID, spaceID: fixture.spaceId)
            try #require(tagDetails.stringValue(for: "relationKey") == "tag")
            let canonicalRaw = details.stringValue(for: manifest.documentAssociationsPropertyKey)
            let projections = Dictionary(uniqueKeysWithValues: TorahNativePropertyDefinition.all.map {
                ($0.key, details.stringArrayValue(for: $0.key))
            })
            documents[role] = .init(native: native, canonicalRaw: canonicalRaw,
                canonicalSHA256: sha256(Data(canonicalRaw.utf8)), projections: projections, tag: tag)
        }
        try #require(Container.shared.accountManager().account.id == accountID)
        return .init(accountID: accountID, spaceID: fixture.spaceId,
            canonicalPropertyKey: manifest.documentAssociationsPropertyKey,
            canonicalPropertyID: manifest.documentAssociationsPropertyId,
            tagProperty: tagProperty, documents: documents)
    }

    static func validate(_ state: State, fixture: Fixture, seed: Seed, phase: String) throws {
        try #require(Set(state.documents.keys) == Set(roles) && state.spaceID == fixture.spaceId)
        try #require(!state.canonicalPropertyKey.isEmpty && !state.canonicalPropertyID.isEmpty)
        try #require(Set(state.documents.values.map { $0.tag.objectID }).count == roles.count)
        for role in roles {
            let document = try #require(state.documents[role])
            let observed = try #require(seed.documents[role])
            let native = document.native
            try #require(native.objectID == observed.objectID && native.spaceID == fixture.spaceId &&
                         native.typeID == observed.typeID && native.name == observed.name)
            try #require(document.tag.name == observed.tagName && state.tagProperty.name == observed.tagPropertyName)
            try #require(native.fields["tag"] == .array([.string(document.tag.objectID)]))
            try #require(native.fields[state.canonicalPropertyKey] == .string(document.canonicalRaw))
            _ = try stableFields(native)
            _ = try stableFields(document.tag)
            let source = try item(.ref, in: document)
            let topic = try item(.topic, in: document)
            try #require(source.canonicalKey == "Genesis 1:1" && topic.canonicalKey == "creation")
            try #require(TorahAssociationDisplayFormatter.label(for: source, locale: Locale(identifier: "en")) == observed.sourceLabel)
            try #require(TorahAssociationDisplayFormatter.label(for: topic, locale: Locale(identifier: "en")) == observed.topicLabel)
            let values = try documentItems(document)
            try #require(values.count == (phase == "baseline" ? 3 : 2))
            try #require(values.allSatisfy { $0.role == .context })
            try #require(native.fields[canonicalHashKey] == .string(document.canonicalSHA256))
            try #require(native.fields[TorahNativePropertyDefinition.readinessKey] == .bool(true) &&
                         native.fields[TorahNativePropertyDefinition.statusKey] == .string("READY") &&
                         native.fields[TorahNativePropertyDefinition.engineVersionKey] == .number(1))
            if phase == "baseline" {
                let word = try item(.word, in: document)
                try #require(TorahAssociationDisplayFormatter.label(for: word, locale: Locale(identifier: "en")) == observed.wordLabel)
            } else {
                try #require(!values.contains { $0.kind == .word })
            }
            for definition in TorahNativePropertyDefinition.all {
                let expected = values.filter { $0.kind == definition.kind }.map(TorahDerivedQueryProjection.identity).sorted()
                try #require(document.projections[definition.key] == expected)
                let raw = native.fields[definition.key]
                if expected.isEmpty {
                    // Exact8ac clears absent projection keys; the original
                    // smartblock adapter reinserts null for attached Properties.
                    try #require(raw == nil || raw == .null || raw == .array([]))
                } else {
                    try #require(raw == .array(expected.map { .string($0) }))
                }
            }
            _ = try labels(document)
        }
        _ = try stableFields(state.tagProperty)
    }

    static func uiBaseline(_ receipt: Receipt, hash: String) throws -> UIBaseline {
        var documents = [String: UIBaseline.Document]()
        for role in roles {
            let value = try #require(receipt.state.documents[role])
            let source = try item(.ref, in: value)
            let topic = try item(.topic, in: value)
            let word = try item(.word, in: value)
            let locale = Locale(identifier: "en")
            documents[role] = .init(objectID: value.native.objectID, typeID: value.native.typeID, name: value.native.name,
                sourceLabel: TorahAssociationDisplayFormatter.label(for: source, locale: locale),
                topicLabel: TorahAssociationDisplayFormatter.label(for: topic, locale: locale),
                wordRecordID: word.id, wordIdentity: TorahDerivedQueryProjection.identity(word),
                wordLabel: TorahAssociationDisplayFormatter.label(for: word, locale: locale),
                tagPropertyName: receipt.state.tagProperty.name, tagID: value.tag.objectID, tagName: value.tag.name)
        }
        return .init(schema: "pinkha-g02-word-native-ui-baseline-v1", nativeBaselineSHA256: hash,
            seedUIReceiptSHA256: receipt.seedUIReceiptSHA256, controller: receipt.controller,
            spaceID: receipt.state.spaceID, documents: documents)
    }

    static func compare(_ baseline: State, _ actual: State, unlink: Unlink) throws {
        try #require(actual.accountID == baseline.accountID && actual.spaceID == baseline.spaceID &&
                     actual.canonicalPropertyKey == baseline.canonicalPropertyKey &&
                     actual.canonicalPropertyID == baseline.canonicalPropertyID)
        let expectedProperty = try stableFields(baseline.tagProperty)
        let actualProperty = try stableFields(actual.tagProperty)
        try #require(expectedProperty == actualProperty)
        let wordDefinition = try #require(TorahNativePropertyDefinition.all.first { $0.kind == .word })
        let changedKeys: Set<String> = [baseline.canonicalPropertyKey, wordDefinition.key,
                                       TorahNativePropertyDefinition.labelsKey, canonicalHashKey]
        for role in roles {
            let before = try #require(baseline.documents[role])
            let after = try #require(actual.documents[role])
            let ui = try #require(unlink.documents[role])
            let word = try item(.word, in: before)
            let identity = TorahDerivedQueryProjection.identity(word)
            try #require(ui.objectID == before.native.objectID && ui.typeID == before.native.typeID &&
                         ui.name == before.native.name && ui.wordRecordIDFromNativeBaseline == word.id &&
                         ui.wordIdentityFromNativeBaseline == identity && ui.tagIDFromNativeBaseline == before.tag.objectID)
            try #require(ui.previousPID > 0 && ui.appPID > 0 && ui.previousPID != ui.appPID)
            try #require(ProcessInfo.processInfo.processIdentifier != ui.previousPID &&
                         ProcessInfo.processInfo.processIdentifier != ui.appPID)
            let beforeFields = try stableFields(before.native, excluding: changedKeys)
            let afterFields = try stableFields(after.native, excluding: changedKeys)
            try #require(beforeFields == afterFields)
            let beforeTag = try stableFields(before.tag)
            let afterTag = try stableFields(after.tag)
            try #require(beforeTag == afterTag && before.tag.objectID == after.tag.objectID)
            let originalPayload = try payload(before)
            let actualPayload = try payload(after)
            let survivors = originalPayload.records.filter { !($0.blockId == nil && $0.item.id == word.id) }
            try #require(survivors.count + 1 == originalPayload.records.count)
            try #require(actualPayload.version == originalPayload.version &&
                         actualPayload.unknownFields == originalPayload.unknownFields && actualPayload.records == survivors)
            // Compare raw JSON values too, retaining every unknown record/item
            // field and timestamp representation outside the removed record.
            var rawExpected = try JSONDecoder().decode([String: TorahJSONValue].self, from: Data(before.canonicalRaw.utf8))
            let rawActual = try JSONDecoder().decode([String: TorahJSONValue].self, from: Data(after.canonicalRaw.utf8))
            guard case .array(let records)? = rawExpected["records"] else {
                throw NativeAcceptanceError.conditionTimeout("G02 canonical records array")
            }
            let retainedRecords = records.filter { record in
                guard case .object(let fields) = record, case .object(let item)? = fields["item"] else { return true }
                return !(item["id"] == .string(word.id) && (fields["blockId"] == nil || fields["blockId"] == .null))
            }
            try #require(retainedRecords.count + 1 == records.count)
            rawExpected["records"] = .array(retainedRecords)
            try #require(rawActual == rawExpected)
            var expectedLabels = try labels(before)
            try #require(expectedLabels.removeValue(forKey: identity) != nil)
            let actualLabels = try labels(after)
            try #require(actualLabels == expectedLabels)
        }
    }

    @MainActor
    static func observe() async throws {
        let env = ProcessInfo.processInfo.environment
        try #require(NativeTypePreservation.disabledFlags.allSatisfy { env[$0] == "0" })
        try #require(env["PINKHA_TYPE_PRESERVATION_POSTFLIGHT"] == "0")
        let phase = try #require(env["PINKHA_G02_NATIVE_PHASE"])
        try #require(["baseline", "postflight"].contains(phase))
        let controller = try controller()
        let token = try #require(controller["TOKEN"])
        let fixtureData = try input("PINKHA_NATIVE_UI_FIXTURE_JSON", maximum: 65_536)
        try #require(sha256(fixtureData) == controller["FIXTURE_SHA256"])
        let fixture = try JSONDecoder().decode(Fixture.self, from: fixtureData)
        try #require(!fixture.spaceId.isEmpty && Set(fixture.documents.keys) == Set(roles) &&
                     Set(fixture.documents.values).count == roles.count &&
                     Set(roles.compactMap { fixture.types[$0] }).count == roles.count)
        try #require(!fixture.documents.values.contains("") && !roles.contains { fixture.types[$0]?.isEmpty != false })
        try #require(!fixture.typeSwitch.objectId.isEmpty && !fixture.documents.values.contains(fixture.typeSwitch.objectId))
        let seedData = try hashedInput("PINKHA_G02_SEED_UI_JSON")
        let seed = try JSONDecoder().decode(Seed.self, from: seedData)
        try #require(seed.schema == "pinkha-g02-word-ui-observation-v1" && seed.phase == "seed-complete" &&
                     seed.spaceID == fixture.spaceId && seed.controller == controller && Set(seed.documents.keys) == Set(roles))
        for role in roles {
            let value = try #require(seed.documents[role])
            try #require(value.objectID == fixture.documents[role] && value.typeID == fixture.types[role] &&
                         value.name == fixture.names[value.objectID] && value.sourceLabel == fixture.sourceLabel &&
                         value.topicLabel == fixture.topicLabel && !value.wordLabel.isEmpty &&
                         ["Tag", "Tags"].contains(value.tagPropertyName) &&
                         value.tagName == "G02 " + role + " " + String(token.prefix(8)))
        }
        let support = try NativeTypePreservation.supportURL()
        let installedFixture = try Data(contentsOf: support.appendingPathComponent("pinkha-native-derived-ui-fixture.json"))
        try #require(installedFixture == fixtureData)
        let beforeDirectories = try NativeTypePreservation.directories()
        let directories = NativeTypePreservation.Directories(container: beforeDirectories.0, middleware: beforeDirectories.1)
        let clock = ContinuousClock()
        let deadline = clock.now.advanced(by: .seconds(45))
        while Container.shared.accountManager().account.id.isEmpty && clock.now < deadline {
            try await Task.sleep(for: .milliseconds(100))
        }
        let state = try await readState(fixture: fixture)
        let baselineURL = support.appendingPathComponent("pinkha-g02-word-native-baseline-" + token + ".json")
        let baselineSHA = phase == "postflight" ? env["PINKHA_G02_BASELINE_SHA256"] : nil
        let unlinkData: Data?
        if phase == "postflight" { unlinkData = try hashedInput("PINKHA_G02_UNLINK_UI_JSON") }
        else { unlinkData = nil }
        func receipt(status: String) -> Receipt {
            .init(schema: "pinkha-g02-word-native-readback-v1", status: status, phase: phase,
                controller: controller, fixtureSHA256: sha256(fixtureData), seedUIReceiptSHA256: sha256(seedData),
                nativeBaselineSHA256: baselineSHA, unlinkUIReceiptSHA256: unlinkData.map(sha256),
                processID: ProcessInfo.processInfo.processIdentifier, directories: directories,
                verifierCallsMutationAPI: false, scope: "THREE_WRITING_OBJECTS_PROPERTIES_NOT_WHOLE_STORE_BYTES",
                permittedClockKeys: clockKeys.sorted(), state: state)
        }
        // Preserve the actual observations even when a following comparison fails.
        _ = try write(receipt(status: "OBSERVED_NATIVE_STATE_NOT_ACCEPTANCE"),
            to: support.appendingPathComponent("pinkha-g02-word-native-" + phase + "-observed-" + token + ".json"))
        try validate(state, fixture: fixture, seed: seed, phase: phase)
        let afterDirectories = try NativeTypePreservation.directories()
        try #require(afterDirectories.0 == beforeDirectories.0 && afterDirectories.1 == beforeDirectories.1)
        let finalFixture = try Data(contentsOf: support.appendingPathComponent("pinkha-native-derived-ui-fixture.json"))
        try #require(finalFixture == fixtureData)
        if phase == "baseline" {
            let baseline = receipt(status: "PASS_BASELINE_READ_ONLY")
            let data = try write(baseline, to: baselineURL)
            let ui = try uiBaseline(baseline, hash: sha256(data))
            _ = try write(ui, to: support.appendingPathComponent("pinkha-g02-word-ui-baseline-" + token + ".json"))
        } else {
            let originalData = try Data(contentsOf: baselineURL)
            try #require(!originalData.isEmpty && originalData.count <= maximumReceiptBytes && sha256(originalData) == baselineSHA)
            let baseline = try JSONDecoder().decode(Receipt.self, from: originalData)
            try #require(baseline.schema == "pinkha-g02-word-native-readback-v1" &&
                         baseline.status == "PASS_BASELINE_READ_ONLY" && baseline.phase == "baseline" &&
                         baseline.controller == controller && baseline.fixtureSHA256 == sha256(fixtureData) &&
                         baseline.seedUIReceiptSHA256 == sha256(seedData) && !baseline.verifierCallsMutationAPI &&
                         baseline.processID > 0 && baseline.processID != ProcessInfo.processInfo.processIdentifier)
            let rawUnlink = try #require(unlinkData)
            let unlink = try JSONDecoder().decode(Unlink.self, from: rawUnlink)
            try #require(unlink.schema == "pinkha-g02-word-ui-observation-v1" && unlink.phase == "unlink-complete" &&
                         unlink.spaceID == fixture.spaceId && unlink.controller == controller &&
                         unlink.nativeBaselineSHA256 == sha256(originalData) && unlink.seedUIReceiptSHA256 == sha256(seedData) &&
                         unlink.nativePersistencePostflightRequired && Set(unlink.documents.keys) == Set(roles))
            try validate(baseline.state, fixture: fixture, seed: seed, phase: "baseline")
            try compare(baseline.state, state, unlink: unlink)
            _ = try write(receipt(status: "PASS_EXACT_DOCUMENT_WORD_UNLINK_NATIVE_READBACK"),
                to: support.appendingPathComponent("pinkha-g02-word-native-postflight-" + token + ".json"))
        }
    }
}
