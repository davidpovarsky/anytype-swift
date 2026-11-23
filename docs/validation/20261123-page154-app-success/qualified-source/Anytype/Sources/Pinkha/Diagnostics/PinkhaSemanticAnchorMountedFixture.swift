#if DEBUG && targetEnvironment(simulator) && PINKHA_NATIVE_T2_AUTHORIZED_READ_V1 && PINKHA_NATIVE_SEMANTIC_ANCHOR_PAGE154_V1
import Foundation
import CryptoKit
import SwiftProtobuf
import ProtobufMessages

/// Synthetic data only. Wallet recovery material never enters this fixture.
struct PinkhaSemanticAnchorMountedFixture: Codable, Sendable {
    static let fileName = "pinkha-semantic-page154-mounted-fixture.json"
    static let captureFileName = "pinkha-semantic-page154-mounted-capture.json"
    static let reopenFileName = "pinkha-semantic-page154-mounted-reopen.json"
    let sourceSHA: String
    let runID: String
    let runAttempt: String
    let nonce: String
    let createdAt: Date
    let preparationProcessID: Int32
    let accountID: String
    let spaceID: String
    let objectID: String
    let blockID: String
    let excludedBlockID: String
    let text: String
    let excludedText: String
    let beforeBlockBase64: String
    let excludedBlockBase64: String

    static func fileURL(_ name: String) throws -> URL {
        try FileManager.default.url(for: .applicationSupportDirectory, in: .userDomainMask,
            appropriateFor: nil, create: true).appendingPathComponent(name)
    }

    static func binding(_ env: [String: String]) throws -> [String: String] {
        var result: [String: String] = [:]
        for (name, suffix, pattern) in [
            ("sourceSHA", "SOURCE_SHA", "^[0-9a-f]{40}$"),
            ("runID", "RUN_ID", "^[1-9][0-9]*$"),
            ("runAttempt", "RUN_ATTEMPT", "^[1-9][0-9]*$"),
            ("nonce", "NONCE", "^[0-9a-f]{32}$")
        ] {
            let value = env["PINKHA_SEMANTIC_MOUNTED_" + suffix] ?? ""
            try require(value.range(of: pattern, options: .regularExpression) != nil, "invalid-binding-" + name)
            result[name] = value
        }
        return result
    }

    static func loadForUI() throws -> Self {
        let env = ProcessInfo.processInfo.environment
        try require(env["PINKHA_SEMANTIC_MOUNTED_UI"] == "1"
            && env["PINKHA_SIMULATOR_UI_DISPOSABLE"] == "1", "explicit-owned-ui-required")
        let binding = try binding(env)
        let data = try Data(contentsOf: fileURL(fileName))
        try require(data.count <= 65_536, "fixture-too-large")
        let fixture = try JSONDecoder().decode(Self.self, from: data)
        try require(fixture.sourceSHA == binding["sourceSHA"] && fixture.runID == binding["runID"]
            && fixture.runAttempt == binding["runAttempt"] && fixture.nonce == binding["nonce"], "fixture-binding-differs")
        try require(Date().timeIntervalSince(fixture.createdAt) >= 0
            && Date().timeIntervalSince(fixture.createdAt) < 7_200, "fixture-expired")
        try require(fixture.preparationProcessID > 0 && fixture.text == "Anchor"
            && fixture.excludedText == "Unselected " + fixture.nonce, "fixture-shape-differs")
        try require([fixture.accountID, fixture.spaceID, fixture.objectID, fixture.blockID, fixture.excludedBlockID]
            .allSatisfy { !$0.isEmpty && $0.utf8.count <= 1_024 && !$0.utf8.contains(0) }, "fixture-identity-invalid")
        try require(fixture.blockID != fixture.excludedBlockID, "fixture-blocks-not-distinct")
        _ = try fixture.beforeBlock()
        _ = try fixture.excludedBlock()
        return fixture
    }

    func beforeBlock() throws -> Anytype_Model_Block { try decode(beforeBlockBase64, blockID: blockID, text: text) }
    func excludedBlock() throws -> Anytype_Model_Block {
        try decode(excludedBlockBase64, blockID: excludedBlockID, text: excludedText)
    }
    private func decode(_ base64: String, blockID: String, text: String) throws -> Anytype_Model_Block {
        guard let data = Data(base64Encoded: base64), data.base64EncodedString() == base64,
              data.count <= 16_384 else { throw SemanticAnchorMountedError.invariant("invalid-fixture-protobuf") }
        let block = try Anytype_Model_Block(serializedBytes: data)
        try Self.require(block.id == blockID && Data(block.text.text.utf8) == Data(text.utf8)
            && block.hasRestrictions && block.restrictions == .init(), "fixture-native-block-differs")
        try Self.require(try Self.bytes(block) == data, "fixture-protobuf-not-deterministic")
        return block
    }

    static func bytes<M: SwiftProtobuf.Message>(_ value: M) throws -> Data {
        var options = BinaryEncodingOptions()
        options.useDeterministicOrdering = true
        return try value.serializedData(options: options)
    }

    static func digest(_ data: Data) -> String { SHA256.hash(data: data).map { String(format: "%02x", $0) }.joined() }

    static func require(_ value: Bool, _ label: String) throws {
        if !value { throw SemanticAnchorMountedError.invariant(label) }
    }
}

enum SemanticAnchorMountedError: Error { case invariant(String) }
#endif
