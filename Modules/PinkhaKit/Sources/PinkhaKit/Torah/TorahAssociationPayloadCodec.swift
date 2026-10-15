import Foundation

public enum TorahAssociationPayloadCodecError: Error, Sendable, Equatable {
    case invalidUTF8
    case malformedJSON
    case unsupportedVersion(Int)
}

/// Deterministic wire codec. Version checks happen before typed decoding so future data is read-only.
public struct TorahAssociationPayloadCodec: Sendable {
    public init() {}

    public func encodeDocument(_ payload: TorahDocumentAssociationsPayload) throws -> Data {
        guard payload.version == TorahDocumentAssociationsPayload.currentVersion else {
            throw TorahAssociationPayloadCodecError.unsupportedVersion(payload.version)
        }
        return try encode(payload)
    }

    public func decodeDocument(_ data: Data) throws -> TorahDocumentAssociationsPayload {
        let version = try inspectVersion(data)
        guard version == TorahDocumentAssociationsPayload.currentVersion else {
            throw TorahAssociationPayloadCodecError.unsupportedVersion(version)
        }
        return try decode(TorahDocumentAssociationsPayload.self, from: data)
    }

    public func decodeDocument(_ string: String) throws -> TorahDocumentAssociationsPayload {
        guard let data = string.data(using: .utf8) else {
            throw TorahAssociationPayloadCodecError.invalidUTF8
        }
        return try decodeDocument(data)
    }

    public func encodeSourceQuote(_ payload: TorahSourceQuotePayload) throws -> Data {
        guard (1...TorahSourceQuotePayload.currentVersion).contains(payload.version) else {
            throw TorahAssociationPayloadCodecError.unsupportedVersion(payload.version)
        }
        return try encode(payload)
    }

    public func decodeSourceQuote(_ data: Data) throws -> TorahSourceQuotePayload {
        let version = try inspectVersion(data)
        guard (1...TorahSourceQuotePayload.currentVersion).contains(version) else {
            throw TorahAssociationPayloadCodecError.unsupportedVersion(version)
        }
        return try decode(TorahSourceQuotePayload.self, from: data)
    }

    private func inspectVersion(_ data: Data) throws -> Int {
        struct Envelope: Decodable { let version: Int }
        do {
            return try decoder().decode(Envelope.self, from: data).version
        } catch {
            throw TorahAssociationPayloadCodecError.malformedJSON
        }
    }

    private func encode<T: Encodable>(_ value: T) throws -> Data {
        do { return try encoder().encode(value) }
        catch { throw TorahAssociationPayloadCodecError.malformedJSON }
    }

    private func decode<T: Decodable>(_ type: T.Type, from data: Data) throws -> T {
        do { return try decoder().decode(type, from: data) }
        catch let error as TorahAssociationPayloadCodecError { throw error }
        catch { throw TorahAssociationPayloadCodecError.malformedJSON }
    }

    private func encoder() -> JSONEncoder {
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.sortedKeys, .withoutEscapingSlashes]
        encoder.dateEncodingStrategy = .custom { date, encoder in
            var container = encoder.singleValueContainer()
            try container.encode(Self.makeDateFormatter(fractionalSeconds: true).string(from: date))
        }
        return encoder
    }

    private func decoder() -> JSONDecoder {
        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .custom { decoder in
            let value = try decoder.singleValueContainer().decode(String.self)
            if let date = Self.makeDateFormatter(fractionalSeconds: true).date(from: value)
                ?? Self.makeDateFormatter(fractionalSeconds: false).date(from: value) {
                return date
            }
            throw DecodingError.dataCorruptedError(
                in: try decoder.singleValueContainer(),
                debugDescription: "Expected an RFC 3339 UTC timestamp"
            )
        }
        return decoder
    }

    private static func makeDateFormatter(fractionalSeconds: Bool) -> ISO8601DateFormatter {
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = fractionalSeconds
            ? [.withInternetDateTime, .withFractionalSeconds]
            : [.withInternetDateTime]
        formatter.timeZone = TimeZone(secondsFromGMT: 0)
        return formatter
    }
}
