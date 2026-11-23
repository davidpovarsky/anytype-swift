import Foundation
#if canImport(CryptoKit)
import CryptoKit
#else
import Crypto
#endif

/// Heart plain text and native protobuf marks. This is not an inline-Markdown model.
public enum PinkhaHeartSemanticAnchorError: Error, Equatable, Sendable {
    case invalidRequest
    case limitExceeded
    case selectionAlreadyLinked
    case invalidReply
    case changedDocument
    case retiredOwner
    case unsupportedRuntime
    case unavailablePublication
    case nativeRefusal(PinkhaHeartSemanticAnchorOutcome)
    /// A native mutation may have committed. Re-read; never retry automatically.
    case uncertain
}

public enum PinkhaHeartSemanticAnchorOutcome: String, Decodable, Sendable {
    case applied, invalid, unsupportedVersion, limit, changed, alreadyLinked
    case pendingEdit, permissionDenied, unavailable, uncertain
}

public enum PinkhaHeartSemanticAnchorProfile {
    public static let sourceManifestSHA256 = "2f76212f9fcd749aeb9e806b941e0fd0b54eba17e5cc842adb81c7eb3bae0f38"
    public static let runtimeVersion =
        "pinkha-semantic-anchor-native-page-candidate-v1-" + sourceManifestSHA256
    public static let maximumWireBytes = 4 * 1_024 * 1_024
    public static let maximumEventBytes = 2 * 1_024 * 1_024
}

public struct PinkhaHeartSemanticAnchorMark: Sendable, Equatable {
    public let from: Int32
    public let to: Int32
    public let kind: Int32
    public let param: String

    public init(from: Int32, to: Int32, kind: Int32, param: String) {
        self.from = from; self.to = to; self.kind = kind; self.param = param
    }

    public static func == (left: Self, right: Self) -> Bool {
        left.from == right.from && left.to == right.to && left.kind == right.kind
            && heartBytesEqual(left.param, right.param)
    }

    fileprivate static func less(_ left: Self, _ right: Self) -> Bool {
        if left.from != right.from { return left.from < right.from }
        if left.to != right.to { return left.to < right.to }
        if left.kind != right.kind { return left.kind < right.kind }
        return left.param.utf8.lexicographicallyPrecedes(right.param.utf8)
    }

    fileprivate var canonicalJSON: String {
        "{\"from\":\(from),\"to\":\(to),\"kind\":\(kind),\"param\":\(heartJSONString(param))}"
    }
}

/// Transient CAS input. It intentionally has no Codable conformance.
public struct PinkhaHeartSemanticAnchorSnapshot: Sendable, Equatable {
    public let text: String
    public let marks: [PinkhaHeartSemanticAnchorMark]
    private let scalarBoundaries: Set<Int32>

    public init(text: String, marks: [PinkhaHeartSemanticAnchorMark]) throws {
        guard text.utf8.count <= 65_536, marks.count <= 1_024 else {
            throw PinkhaHeartSemanticAnchorError.limitExceeded
        }
        var boundaries: Set<Int32> = [0]
        var offset: Int32 = 0
        for scalar in text.unicodeScalars {
            offset += scalar.value > 0xffff ? 2 : 1
            boundaries.insert(offset)
        }
        var allParameterBytes = 0
        for mark in marks {
            allParameterBytes += mark.param.utf8.count
            guard mark.param.utf8.count <= 8_192, allParameterBytes <= 262_144 else {
                throw PinkhaHeartSemanticAnchorError.limitExceeded
            }
            guard (0...10).contains(mark.kind), mark.from >= 0, mark.to > mark.from,
                  boundaries.contains(mark.from), boundaries.contains(mark.to) else {
                throw PinkhaHeartSemanticAnchorError.invalidRequest
            }
        }
        self.text = text; self.marks = marks; scalarBoundaries = boundaries
    }

    public static func == (left: Self, right: Self) -> Bool {
        heartBytesEqual(left.text, right.text) && left.marks == right.marks
    }

    public func hasSameMarks(as other: Self) -> Bool {
        heartBytesEqual(text, other.text)
            && marks.sorted(by: PinkhaHeartSemanticAnchorMark.less)
                == other.marks.sorted(by: PinkhaHeartSemanticAnchorMark.less)
    }

    fileprivate func hasScalarRange(from: Int32, to: Int32) -> Bool {
        from >= 0 && to > from && scalarBoundaries.contains(from) && scalarBoundaries.contains(to)
    }

    /// Matches Go encoding/json's fixed Snapshot/Mark field order and escaping.
    /// Mark order is significant; nil and empty native mark slices both encode [].
    var canonicalJSON: String {
        "{\"text\":\(heartJSONString(text)),\"marks\":[\(marks.map(\.canonicalJSON).joined(separator: ","))]}"
    }

    public var digest: String {
        SHA256.hash(data: Data(canonicalJSON.utf8)).map { String(format: "%02x", $0) }.joined()
    }
}

/// One immutable intent. No account, signer, permission, pointer or retry field
/// is accepted at the native byte boundary. Selection offsets are never a receipt.
public struct PinkhaHeartSemanticAnchorRequest: Sendable {
    public let spaceID: String
    public let objectID: String
    public let blockID: String
    public let anchorID: String
    public let from: Int32
    public let to: Int32
    public let expected: PinkhaHeartSemanticAnchorSnapshot
    public let marker: String

    public init(spaceID: String, objectID: String, blockID: String, anchorID: String,
                range: NSRange, expected: PinkhaHeartSemanticAnchorSnapshot) throws {
        guard heartValidIdentity(spaceID), heartValidIdentity(objectID), heartValidIdentity(blockID),
              heartValidAnchorID(anchorID), range.location != NSNotFound, range.length > 0,
              range.location >= 0, range.length >= 0,
              let from = Int32(exactly: range.location),
              range.location <= Int.max - range.length,
              let to = Int32(exactly: range.location + range.length),
              expected.hasScalarRange(from: from, to: to) else {
            throw PinkhaHeartSemanticAnchorError.invalidRequest
        }
        guard expected.marks.count < 1_024 else { throw PinkhaHeartSemanticAnchorError.limitExceeded }
        // The native contract checks scalar ranges. A mounted selection must
        // additionally have extended grapheme boundaries before dispatch.
        var graphemeBoundaries: Set<Int32> = [0]
        var offset: Int32 = 0
        for character in expected.text {
            offset += Int32(String(character).utf16.count)
            graphemeBoundaries.insert(offset)
        }
        guard graphemeBoundaries.contains(from), graphemeBoundaries.contains(to) else {
            throw PinkhaHeartSemanticAnchorError.invalidRequest
        }
        let marker = heartMarker(spaceID: spaceID, objectID: objectID, anchorID: anchorID)
        for mark in expected.marks {
            if heartBytesEqual(mark.param, marker) {
                throw PinkhaHeartSemanticAnchorError.selectionAlreadyLinked
            }
            if mark.from < to && from < mark.to &&
                ([5, 8, 10].contains(mark.kind) || mark.param.lowercased().hasPrefix("pinkha-anchor:")) {
                throw PinkhaHeartSemanticAnchorError.selectionAlreadyLinked
            }
        }
        self.spaceID = spaceID; self.objectID = objectID; self.blockID = blockID
        self.anchorID = anchorID; self.from = from; self.to = to
        self.expected = expected; self.marker = marker
    }

    public func encodedRequest() throws -> Data {
        let raw = Data(("{\"protocolVersion\":1,\"spaceID\":\(heartJSONString(spaceID)),"
            + "\"objectID\":\(heartJSONString(objectID)),\"blockID\":\(heartJSONString(blockID)),"
            + "\"anchorID\":\(heartJSONString(anchorID)),\"from\":\(from),\"to\":\(to),"
            + "\"expected\":\(expected.canonicalJSON)}").utf8)
        guard raw.count <= PinkhaHeartSemanticAnchorProfile.maximumWireBytes else {
            throw PinkhaHeartSemanticAnchorError.limitExceeded
        }
        return raw
    }

    public func plannedSnapshot() throws -> PinkhaHeartSemanticAnchorSnapshot {
        try .init(text: expected.text, marks: expected.marks + [.init(from: from, to: to, kind: 5, param: marker)])
    }
}

/// Native durable witness only. Construction outside validated wire decoding is
/// unavailable. Verified application acceptance additionally requires readback.
public struct PinkhaHeartSemanticAnchorReceipt: Sendable, Decodable {
    public let version: UInt32
    public let spaceID: String
    public let objectID: String
    public let blockID: String
    public let anchorID: String
    public let marker: String
    public let changeID: String
    public let nativeChangeSHA256: String
    public let beforeTextMarksSHA256: String
    public let afterTextMarksSHA256: String

    public init(from decoder: Decoder) throws {
        let values = try decoder.container(keyedBy: HeartWireKey.self)
        try heartExactKeys(values, ["version", "spaceID", "objectID", "blockID", "anchorID",
            "marker", "changeID", "nativeChangeSHA256", "beforeTextMarksSHA256", "afterTextMarksSHA256"])
        version = try values.decode(UInt32.self, forKey: .init("version"))
        spaceID = try values.decode(String.self, forKey: .init("spaceID"))
        objectID = try values.decode(String.self, forKey: .init("objectID"))
        blockID = try values.decode(String.self, forKey: .init("blockID"))
        anchorID = try values.decode(String.self, forKey: .init("anchorID"))
        marker = try values.decode(String.self, forKey: .init("marker"))
        changeID = try values.decode(String.self, forKey: .init("changeID"))
        nativeChangeSHA256 = try values.decode(String.self, forKey: .init("nativeChangeSHA256"))
        beforeTextMarksSHA256 = try values.decode(String.self, forKey: .init("beforeTextMarksSHA256"))
        afterTextMarksSHA256 = try values.decode(String.self, forKey: .init("afterTextMarksSHA256"))
        guard version == 1, heartValidIdentity(spaceID), heartValidIdentity(objectID),
              heartValidIdentity(blockID), heartValidIdentity(changeID), heartValidAnchorID(anchorID),
              heartBytesEqual(marker, heartMarker(spaceID: spaceID, objectID: objectID, anchorID: anchorID)),
              heartValidDigest(nativeChangeSHA256), heartValidDigest(beforeTextMarksSHA256),
              heartValidDigest(afterTextMarksSHA256), beforeTextMarksSHA256 != afterTextMarksSHA256 else {
            throw PinkhaHeartSemanticAnchorError.invalidReply
        }
    }

    func validate(for request: PinkhaHeartSemanticAnchorRequest) throws {
        guard heartBytesEqual(spaceID, request.spaceID), heartBytesEqual(objectID, request.objectID),
              heartBytesEqual(blockID, request.blockID), heartBytesEqual(anchorID, request.anchorID),
              heartBytesEqual(marker, request.marker), beforeTextMarksSHA256 == request.expected.digest else {
            throw PinkhaHeartSemanticAnchorError.invalidReply
        }
    }
}

struct PinkhaHeartSemanticAnchorAppliedReply: Sendable {
    let receipt: PinkhaHeartSemanticAnchorReceipt
    let responseEvent: Data

    static func decode(_ raw: Data, request: PinkhaHeartSemanticAnchorRequest) throws -> Self {
        do {
            try HeartSemanticJSON.validate(raw, maximumBytes: PinkhaHeartSemanticAnchorProfile.maximumWireBytes)
            let envelope = try JSONDecoder().decode(HeartCaptureEnvelope.self, from: raw)
            guard envelope.outcome == .applied else {
                throw PinkhaHeartSemanticAnchorError.nativeRefusal(envelope.outcome)
            }
            guard let receipt = envelope.receipt, let event = envelope.responseEvent else {
                throw PinkhaHeartSemanticAnchorError.invalidReply
            }
            try receipt.validate(for: request)
            return .init(receipt: receipt, responseEvent: event)
        } catch let error as PinkhaHeartSemanticAnchorError {
            throw error
        } catch {
            throw PinkhaHeartSemanticAnchorError.invalidReply
        }
    }
}

private struct HeartCaptureEnvelope: Decodable {
    let outcome: PinkhaHeartSemanticAnchorOutcome
    let receipt: PinkhaHeartSemanticAnchorReceipt?
    let responseEvent: Data?

    init(from decoder: Decoder) throws {
        let values = try decoder.container(keyedBy: HeartWireKey.self)
        guard try values.decode(UInt32.self, forKey: .init("protocolVersion")) == 1 else {
            throw PinkhaHeartSemanticAnchorError.invalidReply
        }
        outcome = try values.decode(PinkhaHeartSemanticAnchorOutcome.self, forKey: .init("outcome"))
        if outcome == .applied {
            try heartExactKeys(values, ["protocolVersion", "outcome", "receipt", "responseEvent"])
            receipt = try values.decode(PinkhaHeartSemanticAnchorReceipt.self, forKey: .init("receipt"))
            let encoded = try values.decode(String.self, forKey: .init("responseEvent"))
            guard let event = Data(base64Encoded: encoded), !event.isEmpty,
                  event.count <= PinkhaHeartSemanticAnchorProfile.maximumEventBytes,
                  heartBytesEqual(encoded, event.base64EncodedString()) else {
                throw PinkhaHeartSemanticAnchorError.invalidReply
            }
            responseEvent = event
        } else {
            try heartExactKeys(values, ["protocolVersion", "outcome"])
            receipt = nil; responseEvent = nil
        }
    }
}

private struct HeartWireKey: CodingKey {
    let stringValue: String
    var intValue: Int? { nil }
    init(_ value: String) { stringValue = value }
    init?(stringValue: String) { self.stringValue = stringValue }
    init?(intValue: Int) { return nil }
}

private func heartExactKeys(_ values: KeyedDecodingContainer<HeartWireKey>, _ names: Set<String>) throws {
    guard Set(values.allKeys.map(\.stringValue)) == names else {
        throw PinkhaHeartSemanticAnchorError.invalidReply
    }
}

func heartBytesEqual(_ left: String, _ right: String) -> Bool {
    left.utf8.elementsEqual(right.utf8)
}

private func heartValidIdentity(_ value: String) -> Bool {
    !value.isEmpty && value.utf8.count <= 1_024 && !value.utf8.contains(0)
}

private func heartValidAnchorID(_ value: String) -> Bool {
    let bytes = Array(value.utf8)
    guard bytes.count == 36 else { return false }
    for (index, byte) in bytes.enumerated() {
        if [8, 13, 18, 23].contains(index) {
            if byte != 45 { return false }
        } else if !(48...57).contains(byte) && !(97...102).contains(byte) {
            return false
        }
    }
    return true
}

private func heartValidDigest(_ value: String) -> Bool {
    value.utf8.count == 64 && value.utf8.allSatisfy { (48...57).contains($0) || (97...102).contains($0) }
}

private func heartMarker(spaceID: String, objectID: String, anchorID: String) -> String {
    func component(_ value: String) -> String {
        Data(value.utf8).base64EncodedString().replacingOccurrences(of: "+", with: "-")
            .replacingOccurrences(of: "/", with: "_").replacingOccurrences(of: "=", with: "")
    }
    return "pinkha-anchor://v1/\(component(spaceID))/\(component(objectID))/\(anchorID)"
}

private func heartJSONString(_ value: String) -> String {
    var result = "\""
    for scalar in value.unicodeScalars {
        switch scalar.value {
        case 0x22: result += "\\\""
        case 0x5c: result += "\\\\"
        case 0x08: result += "\\b"
        case 0x0c: result += "\\f"
        case 0x0a: result += "\\n"
        case 0x0d: result += "\\r"
        case 0x09: result += "\\t"
        case 0..<0x20, 0x26, 0x3c, 0x3e, 0x2028, 0x2029:
            result += String(format: "\\u%04x", scalar.value)
        default: result.unicodeScalars.append(scalar)
        }
    }
    result += "\""
    return result
}
