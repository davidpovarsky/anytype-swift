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

    /// Encodes the canonical v2 document-and-block payload used only by the
    /// explicitly limited single-active-writer track.
    public func encodeCanonicalDocument(_ payload: TorahCanonicalAssociationsPayload) throws -> Data {
        guard payload.version == TorahCanonicalAssociationsPayload.currentVersion else {
            throw TorahAssociationPayloadCodecError.unsupportedVersion(payload.version)
        }
        return try encode(payload)
    }

    /// Decodes v2 canonical data or losslessly lifts legacy v1 document items
    /// into the supplied exact document location. Future versions fail before
    /// yielding writable data.
    public func decodeCanonicalDocument(
        _ data: Data,
        legacyLocation: TorahAssociationLocation
    ) throws -> TorahCanonicalAssociationsPayload {
        let version = try inspectVersion(data)
        switch version {
        case TorahDocumentAssociationsPayload.currentVersion:
            let legacy = try decodeDocument(data)
            return TorahCanonicalAssociationsPayload(
                records: legacy.items.map {
                    TorahStoredAssociationRecord(location: legacyLocation, item: $0)
                },
                unknownFields: legacy.unknownFields
            )
        case TorahCanonicalAssociationsPayload.currentVersion:
            return try decode(TorahCanonicalAssociationsPayload.self, from: data)
        default:
            throw TorahAssociationPayloadCodecError.unsupportedVersion(version)
        }
    }

    public func decodeCanonicalDocument(
        _ string: String,
        legacyLocation: TorahAssociationLocation
    ) throws -> TorahCanonicalAssociationsPayload {
        guard let data = string.data(using: .utf8) else {
            throw TorahAssociationPayloadCodecError.invalidUTF8
        }
        return try decodeCanonicalDocument(data, legacyLocation: legacyLocation)
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
