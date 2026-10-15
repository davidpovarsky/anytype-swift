import Foundation
import TorahInspectorCore

public struct SefariaTextProvider: TextProvider {
    public let providerID = "sefaria"
    private let client: SefariaClient

    public init(client: SefariaClient = SefariaClient()) {
        self.client = client
    }

    public func fetchText(
        reference: String,
        request: TorahTextRequest = TorahTextRequest()
    ) async throws -> TorahTextDocument {
        try Task.checkCancellation()
        async let metadataCall = client.get(pathSegments: ["api", "ref", reference])
        async let requestedTextCall = fetchPayload(
            reference: reference,
            version: request.language,
            fillInMissingSegments: request.fillInMissingSegments
        )

        let ((metadataData, metadataResponse), requestedText) = try await (metadataCall, requestedTextCall)
        if metadataResponse.statusCode == 404 { throw TorahError.invalidReference }
        try SefariaJSON.requireSuccess(metadataResponse, operation: "reference metadata")
        guard let metadata = try SefariaJSON.object(from: metadataData) as? [String: Any] else {
            throw TorahError.malformedResponse
        }
        guard metadata["is_ref"] as? Bool == true else { throw TorahError.invalidReference }

        var selectedText = requestedText
        if !Self.hasUsableVersion(requestedText.root), request.language.lowercased() != "source" {
            selectedText = try await fetchPayload(
                reference: reference,
                version: "source",
                fillInMissingSegments: request.fillInMissingSegments
            )
        }
        try Task.checkCancellation()
        return try Self.decode(
            requestedReference: reference,
            root: selectedText.root,
            metadata: metadata
        )
    }

    private func fetchPayload(
        reference: String,
        version: String,
        fillInMissingSegments: Bool
    ) async throws -> (root: [String: Any], payload: String) {
        let (data, response) = try await client.get(
            pathSegments: ["api", "v3", "texts", reference],
            query: [
                URLQueryItem(name: "version", value: version),
                URLQueryItem(name: "fill_in_missing_segments", value: fillInMissingSegments ? "1" : "0"),
                URLQueryItem(name: "return_format", value: "text_only")
            ]
        )
        try SefariaJSON.requireSuccess(response, operation: "text request")
        guard let root = try SefariaJSON.object(from: data) as? [String: Any] else {
            throw TorahError.malformedResponse
        }
        return (root, SefariaJSON.payload(root))
    }

    static func hasUsableVersion(_ root: [String: Any]) -> Bool {
        guard let versions = root["versions"] as? [[String: Any]] else { return false }
        return versions.contains { version in
            segmentTexts(version["text"]).contains {
                !$0.text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
            }
        }
    }

    static func decode(
        requestedReference: String,
        root: [String: Any],
        metadata: [String: Any]
    ) throws -> TorahTextDocument {
        guard let canonical = SefariaJSON.string(root, keys: ["ref", "sectionRef"]),
              let sectionRef = SefariaJSON.string(root, keys: ["sectionRef", "ref"])
        else { throw TorahError.malformedResponse }

        guard let versions = root["versions"] as? [[String: Any]] else {
            if root["versions"] == nil { throw TorahError.noText }
            throw TorahError.malformedResponse
        }
        guard let versionObject = versions.first(where: { version in
            segmentTexts(version["text"]).contains {
                !$0.text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
            }
        }) else { throw TorahError.noText }

        guard let versionTitle = SefariaJSON.string(versionObject, keys: ["versionTitle"]),
              let language = SefariaJSON.string(versionObject, keys: ["language", "actualLanguage"])
        else { throw TorahError.malformedResponse }

        let texts = segmentTexts(versionObject["text"]).filter {
            !$0.text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
        }
        guard !texts.isEmpty else { throw TorahError.noText }

        let startIndexes = metadata["start_indexes"] as? [Int] ?? []
        let endIndexes = metadata["end_indexes"] as? [Int] ?? []
        let depth = metadata["depth"] as? Int
        let hasSegmentIndex = depth.map { startIndexes.count >= $0 } == true
        let isExactSegment = texts.count == 1
            && hasSegmentIndex
            && (endIndexes.isEmpty || startIndexes == endIndexes)
        let startOrdinal = hasSegmentIndex ? (startIndexes.last ?? 0) : 1
        guard startOrdinal > 0 else { throw TorahError.malformedResponse }

        if let depth,
           startIndexes.count >= depth,
           endIndexes.count >= depth,
           startIndexes.dropLast() != endIndexes.dropLast() {
            // Texts V3 does not provide an exact ref for each flattened item in
            // a cross-section range. Refuse to invent identities across a
            // boundary; callers can request each returned section explicitly.
            throw TorahError.malformedResponse
        }

        let segments = texts.map { entry -> TorahTextSegment in
            let ordinal = startOrdinal + entry.offset
            // `start_indexes` is documented as already 1-based. Exact segment
            // requests retain the provider's canonical ref verbatim. For a
            // section or same-section range, the provider-returned section ref
            // plus the documented numeric ordinal is the conservative identity.
            let segmentRef = isExactSegment ? canonical : "\(sectionRef):\(ordinal)"
            return TorahTextSegment(
                canonicalRef: segmentRef,
                hebrewRef: isExactSegment ? SefariaJSON.string(root, keys: ["heRef"]) : nil,
                text: entry.text,
                ordinal: ordinal
            )
        }

        let navigation = metadata["navigation_refs"] as? [String: Any] ?? [:]
        return TorahTextDocument(
            providerID: "sefaria",
            requestedRef: requestedReference,
            canonicalRef: canonical,
            hebrewRef: SefariaJSON.string(root, keys: ["heRef"]),
            sectionRef: sectionRef,
            hebrewSectionRef: SefariaJSON.string(root, keys: ["heSectionRef"]),
            segments: segments,
            previousSectionRef: SefariaJSON.string(navigation, keys: ["prev_section_ref"]),
            nextSectionRef: SefariaJSON.string(navigation, keys: ["next_section_ref"]),
            version: TorahTextVersionMetadata(
                language: language,
                actualLanguage: SefariaJSON.string(versionObject, keys: ["actualLanguage"]),
                languageFamilyName: SefariaJSON.string(versionObject, keys: ["languageFamilyName"]),
                versionTitle: versionTitle,
                versionTitleInHebrew: SefariaJSON.string(versionObject, keys: ["versionTitleInHebrew"]),
                license: SefariaJSON.string(versionObject, keys: ["license"]),
                direction: SefariaJSON.string(versionObject, keys: ["direction"])
            ),
            rawProviderPayload: SefariaJSON.payload(root)
        )
    }

    private static func segmentTexts(_ value: Any?) -> [(offset: Int, text: String)] {
        if let text = value as? String { return [(0, text)] }
        guard let values = value as? [Any] else { return [] }

        var flattened: [(offset: Int, text: String)] = []
        for value in values {
            if let text = value as? String {
                flattened.append((flattened.count, text))
            } else {
                for nested in segmentTexts(value) {
                    flattened.append((flattened.count, nested.text))
                }
            }
        }
        return flattened
    }
}
