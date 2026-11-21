import Crypto
import Foundation
import PinkhaKit

/// Decoder for Heart's unchanged operation.go binary identity envelope. The
/// payload remains opaque; this is neither JSON normalization nor signature
/// verification. The native reader already binds each receipt to signed history.
struct HeartNativeOperationCanonical: Sendable {
    let bytes: Data
    let spaceID: String
    let operationID: String
    let authorID: String
    let target: TorahAssociationTarget
    let claimID: String

    init(exactBytes: Data) throws {
        guard exactBytes.count <= 256 * 1024 else { throw TorahOperationReadError.readLimit }
        var cursor = HeartCanonicalCursor(exactBytes)
        try cursor.expect(Data("pinkha-t2-operation\0".utf8))
        guard try cursor.uint32() == 1 else { throw TorahOperationReadError.malformedNativeResponse }
        let space = try cursor.text(maximum: 1024, required: true)
        let operation = try cursor.text(maximum: 32, required: true)
        let author = try cursor.text(maximum: 1024, required: true)
        let kind = try cursor.text(maximum: 7, required: true)
        let object = try cursor.text(maximum: 1024, required: true)
        let block = try cursor.text(maximum: 1024, required: false)
        let provider = try cursor.text(maximum: 256, required: false)
        let reference = try cursor.text(maximum: 4096, required: false)
        let payload = try cursor.framed(maximum: 64 * 1024)
        let observedCount = try cursor.uint32()
        guard observedCount <= 256, Self.hex(operation, count: 32) else {
            throw TorahOperationReadError.malformedNativeResponse
        }
        var previous: String?
        for _ in 0..<observedCount {
            let observed = try cursor.text(maximum: 129, required: true)
            guard Self.validClaimID(observed), previous.map({ $0 < observed }) ?? true else {
                throw TorahOperationReadError.malformedNativeResponse
            }
            previous = observed
        }
        guard cursor.atEnd else { throw TorahOperationReadError.malformedNativeResponse }
        switch kind {
        case "add":
            guard observedCount == 0, !payload.isEmpty, !provider.isEmpty, !reference.isEmpty else {
                throw TorahOperationReadError.malformedNativeResponse
            }
        case "remove":
            guard observedCount > 0, payload.isEmpty, provider.isEmpty, reference.isEmpty else {
                throw TorahOperationReadError.malformedNativeResponse
            }
        case "replace":
            guard observedCount > 0, !payload.isEmpty, !provider.isEmpty, !reference.isEmpty else {
                throw TorahOperationReadError.malformedNativeResponse
            }
        default:
            throw TorahOperationReadError.malformedNativeResponse
        }
        var logical = Data("pinkha-t2-operation-key-v1\0".utf8)
        Self.appendFramed(Data(space.utf8), to: &logical)
        Self.appendFramed(Data(operation.utf8), to: &logical)
        self.bytes = exactBytes
        self.spaceID = space
        self.operationID = operation
        self.authorID = author
        self.target = block.isEmpty ? .object(objectId: object) : .block(objectId: object, blockId: block)
        self.claimID = Self.digest(logical) + "/" + Self.digest(exactBytes)
    }

    static func exact(_ lhs: String, _ rhs: String) -> Bool { lhs.utf8.elementsEqual(rhs.utf8) }

    static func hex(_ value: String, count: Int) -> Bool {
        value.utf8.count == count && value.utf8.allSatisfy { (48...57).contains($0) || (97...102).contains($0) }
    }

    static func validClaimID(_ value: String) -> Bool {
        let fields = value.split(separator: "/", omittingEmptySubsequences: false)
        return fields.count == 2 && fields.allSatisfy { hex(String($0), count: 64) }
    }

    static func receiptID(claimID: String, changeID: String) -> String {
        var value = Data("pinkha-t2-receipt-v1\0".utf8)
        appendFramed(Data(claimID.utf8), to: &value)
        appendFramed(Data(changeID.utf8), to: &value)
        return digest(value)
    }

    static func digest(_ data: Data) -> String {
        SHA256.hash(data: data).map { String(format: "%02x", $0) }.joined()
    }

    static func appendFramed(_ data: Data, to output: inout Data) {
        let count = UInt32(data.count)
        output.append(contentsOf: [UInt8(count >> 24), UInt8((count >> 16) & 255), UInt8((count >> 8) & 255), UInt8(count & 255)])
        output.append(data)
    }
}

private struct HeartCanonicalCursor {
    let bytes: [UInt8]
    var position = 0
    init(_ bytes: Data) { self.bytes = Array(bytes) }
    var atEnd: Bool { position == bytes.count }

    mutating func expect(_ expected: Data) throws {
        guard try take(expected.count) == expected else { throw TorahOperationReadError.malformedNativeResponse }
    }

    mutating func uint32() throws -> UInt32 {
        let value = Array(try take(4))
        return UInt32(value[0]) << 24 | UInt32(value[1]) << 16 | UInt32(value[2]) << 8 | UInt32(value[3])
    }

    mutating func framed(maximum: Int) throws -> Data {
        let count = Int(try uint32())
        guard count <= maximum else { throw TorahOperationReadError.malformedNativeResponse }
        return try take(count)
    }

    mutating func text(maximum: Int, required: Bool) throws -> String {
        let data = try framed(maximum: maximum)
        guard (!required || !data.isEmpty), !data.contains(0), let text = String(data: data, encoding: .utf8) else {
            throw TorahOperationReadError.malformedNativeResponse
        }
        return text
    }

    private mutating func take(_ count: Int) throws -> Data {
        guard count >= 0, position <= bytes.count, count <= bytes.count - position else {
            throw TorahOperationReadError.malformedNativeResponse
        }
        defer { position += count }
        return Data(bytes[position..<(position + count)])
    }
}
