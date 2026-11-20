import Foundation
import PinkhaKit
import PinkhaAnyEngine

/// A live acceptance probe of the retained public provider facade. It does not
/// replace its transport, retry policy, provider responses, or in-memory caches.
/// Only public identifiers, counts, and digests leave this process.
enum LiveProviderProbe {
    private enum Failure: Error {
        case assertion(String)
        case deadlineExceeded
        case failedChecks
    }

    private struct Measurement: Codable, Sendable {
        var ids: [String] = []
        var counts: [String: Int] = [:]
        var sha256: [String: String] = [:]
    }

    private struct Check: Codable, Sendable {
        let id: String
        let status: String
        let elapsedMilliseconds: Int
        let ids: [String]
        let counts: [String: Int]
        let sha256: [String: String]
        let errorCode: String?
    }

    private struct Report: Codable, Sendable {
        let status: String
        let scope: String
        let count: Int
        let passed: Int
        let failed: Int
        let checks: [Check]
    }

    private static let caseIDs = [
        "hebrew_reference_genesis_1_1",
        "hebrew_text_version_preserved_payload",
        "commentary_and_links",
        "source_hierarchy",
        "topic_search_shabbat",
        "resolve_returned_topic",
        "hebrew_word_with_reference_context"
    ]
    private static let reference = "Genesis 1:1"
    // Structured concurrency cancels at this deadline but still waits for
    // children. The external runner enforces the process deadline as well.
    private static let timeoutSeconds = 90

    static func run() async throws {
        let workspace: AnytypeTorahWorkspace
        do {
            workspace = try AnytypeTorahWorkspace.sefaria()
        } catch {
            let checks = caseIDs.map {
                Check(id: $0, status: "FAIL", elapsedMilliseconds: 0,
                      ids: [], counts: [:], sha256: [:], errorCode: sanitized(error))
            }
            try emit(checks)
            throw Failure.failedChecks
        }

        var checks: [Check] = []
        checks.append(await measure(caseIDs[0]) {
            let resolved = try await workspace.resolveReference("בראשית א:א")
            try require(resolved.canonical == reference, "canonical_reference_mismatch")
            try require(containsHebrew(resolved.labelHe), "missing_hebrew_reference_label")
            try require(resolved.isEmbeddableSource, "resolved_reference_is_not_precise")
            let raw = try payloadObject(resolved.payload)
            try require(raw["is_ref"] as? Bool == true, "missing_raw_reference_authority")
            let rawReference = raw["normalized"] as? String ?? raw["ref"] as? String
            try require(rawReference == resolved.canonical, "raw_reference_mismatch")
            return Measurement(
                ids: [resolved.canonical],
                counts: ["payloadBytes": resolved.payload.utf8.count,
                         "addressDepth": resolved.startIndexes.count],
                sha256: ["preservedProviderJSON": digest(resolved.payload)]
            )
        })

        checks.append(await measure(caseIDs[1]) {
            let document = try await workspace.fetchText(reference: reference)
            try require(document.providerID == "sefaria", "unexpected_text_provider")
            try require(document.canonicalRef == reference, "text_reference_mismatch")
            try require(document.segments.count == 1, "exact_segment_count_mismatch")
            try require(document.segments.allSatisfy { $0.canonicalRef == reference },
                        "segment_identity_mismatch")
            try require(document.segments.contains { containsHebrew($0.text) },
                        "missing_hebrew_text")
            try require(!document.version.versionTitle.isEmpty && !document.version.language.isEmpty,
                        "missing_version_metadata")
            let raw = try payloadObject(document.rawProviderPayload)
            try require(raw["ref"] as? String == reference, "raw_text_reference_mismatch")
            let versions = raw["versions"] as? [[String: Any]] ?? []
            try require(versions.contains {
                $0["versionTitle"] as? String == document.version.versionTitle
            }, "version_not_present_in_raw_payload")
            return Measurement(
                ids: [document.id] + document.segments.map(\.canonicalRef),
                counts: ["segments": document.segments.count,
                         "textUTF8Bytes": document.segments.reduce(0) { $0 + $1.text.utf8.count },
                         "payloadBytes": document.rawProviderPayload.utf8.count,
                         "versionsInPayload": versions.count],
                sha256: [
                    "preservedProviderJSON": digest(document.rawProviderPayload),
                    "versionMetadata": try digestJSON(document.version),
                    "segmentTexts": try digestJSON(document.segments.map(\.text))
                ]
            )
        })

        checks.append(await measure(caseIDs[2]) {
            let links = try await workspace.links(for: reference)
            try require(!links.isEmpty && links.count <= 10_000, "links_empty_or_over_bound")
            let commentary = links.filter { $0.relationshipKind == .commentary }
            try require(!commentary.isEmpty, "missing_commentary")
            let anchored = commentary.filter { $0.anchorRefs.contains(reference) }
            try require(!anchored.isEmpty, "missing_exact_commentary_anchor")
            try require(anchored.contains { containsHebrew($0.hebrewText ?? "") },
                        "missing_commentary_hebrew_preview")
            let ordered = links.sorted { $0.id < $1.id }
            try require(ordered.allSatisfy {
                !$0.sourceRef.isEmpty && !$0.canonicalBookID.isEmpty
                    && $0.rawProviderPayload.utf8.count > 2
            }, "missing_link_identity_or_payload")
            let sample = anchored[0]
            let raw = try payloadObject(sample.rawProviderPayload)
            let rawReference = raw["sourceRef"] as? String ?? raw["ref"] as? String
            try require(rawReference == sample.sourceRef, "raw_commentary_reference_mismatch")
            return Measurement(
                ids: anchored.prefix(4).map(\.sourceRef),
                counts: ["links": links.count, "commentaries": commentary.count,
                         "exactAnchoredCommentaries": anchored.count,
                         "payloadBytes": ordered.reduce(0) { $0 + $1.rawProviderPayload.utf8.count }],
                sha256: ["preservedProviderJSONRows": try digestJSON(ordered.map(\.rawProviderPayload))]
            )
        })

        checks.append(await measure(caseIDs[3]) {
            let hierarchy = try await workspace.fetchSourceHierarchy()
            try require(hierarchy.providerID == "sefaria" && !hierarchy.roots.isEmpty,
                        "missing_source_hierarchy")
            var pending = hierarchy.roots.map { (node: $0, depth: 0) }
            var ids: [String] = []
            var genesisIDs: [String] = []
            var leaves = 0
            while let next = pending.popLast() {
                try Task.checkCancellation()
                try require(ids.count < 100_000 && next.depth <= 128,
                            "hierarchy_exceeded_probe_bound")
                try require(!next.node.id.isEmpty, "missing_hierarchy_identity")
                ids.append(next.node.id)
                if next.node.children.isEmpty { leaves += 1 }
                if next.node.canonicalKey == "Genesis" { genesisIDs.append(next.node.id) }
                pending.append(contentsOf: next.node.children.map { (node: $0, depth: next.depth + 1) })
            }
            try require(!genesisIDs.isEmpty, "genesis_missing_from_source_hierarchy")
            return Measurement(
                ids: Array(genesisIDs.sorted().prefix(4)),
                counts: ["roots": hierarchy.roots.count, "nodes": ids.count, "leaves": leaves],
                sha256: ["decodedHierarchyNodeIDs": try digestJSON(ids.sorted())]
            )
        })

        let topicSearch = await measure(caseIDs[4]) {
            let candidates = try await workspace.suggestTopics("Shabbat", limit: 8)
            try require(!candidates.isEmpty && candidates.count <= 8, "topics_empty_or_over_bound")
            try require(candidates.allSatisfy { !$0.id.isEmpty && !$0.displayTitle.isEmpty },
                        "missing_topic_identity_or_title")
            try require(Set(candidates.map(\.id)).count == candidates.count, "duplicate_topic_ids")
            let ids = candidates.map(\.id)
            return Measurement(ids: ids, counts: ["candidates": candidates.count],
                               sha256: ["returnedTopicIDs": try digestJSON(ids)])
        }
        checks.append(topicSearch)
        let returnedTopicID = topicSearch.status == "PASS" ? topicSearch.ids.first : nil
        checks.append(await measure(caseIDs[5]) {
            guard let returnedTopicID else { throw Failure.assertion("topic_search_failed") }
            let topic = try await workspace.resolveTopic(returnedTopicID)
            try require(topic.slug == returnedTopicID, "resolved_topic_identity_mismatch")
            try require(!topic.displayTitle.isEmpty, "missing_resolved_topic_title")
            let raw = try payloadObject(topic.payload)
            try require(raw["slug"] as? String == topic.slug, "raw_topic_identity_mismatch")
            return Measurement(
                ids: [topic.slug],
                counts: ["payloadBytes": topic.payload.utf8.count,
                         "localizedTitles": [topic.labelHe, topic.labelEn].compactMap { $0 }.count],
                sha256: ["preservedProviderJSON": digest(topic.payload)]
            )
        })

        checks.append(await measure(caseIDs[6]) {
            let words = try await workspace.resolveWord(
                "בראשית", context: TorahLexicalContext(canonicalReference: reference))
            try require(!words.isEmpty && words.count <= 1_000, "word_entries_empty_or_over_bound")
            try require(words.allSatisfy {
                !$0.candidate.id.isEmpty && !$0.candidate.headword.isEmpty
                    && !$0.candidate.lexicon.isEmpty && $0.candidate.payload.utf8.count > 2
            }, "missing_word_identity_or_payload")
            let definitions = words.filter { !($0.candidate.description ?? "").isEmpty }
            try require(!definitions.isEmpty, "missing_lexical_definition")
            let ordered = words.sorted { $0.candidate.id < $1.candidate.id }
            _ = try payloadObject(ordered[0].candidate.payload)
            return Measurement(
                ids: Array(ordered.prefix(4).map { $0.candidate.id }),
                counts: ["entries": words.count, "definitions": definitions.count,
                         "payloadBytes": ordered.reduce(0) { $0 + $1.candidate.payload.utf8.count }],
                sha256: ["preservedProviderJSONRows": try digestJSON(ordered.map { $0.candidate.payload })]
            )
        })

        try emit(checks)
        guard checks.count == caseIDs.count, checks.allSatisfy({ $0.status == "PASS" }) else {
            throw Failure.failedChecks
        }
    }

    private static func measure(
        _ id: String,
        operation: @escaping @Sendable () async throws -> Measurement
    ) async -> Check {
        let started = Date()
        do {
            let value = try await withThrowingTaskGroup(of: Measurement.self) { group in
                group.addTask { try await operation() }
                group.addTask {
                    try await Task.sleep(for: .seconds(timeoutSeconds))
                    throw Failure.deadlineExceeded
                }
                defer { group.cancelAll() }
                guard let first = try await group.next() else { throw Failure.deadlineExceeded }
                return first
            }
            try require(value.ids.count <= 16 && value.ids.allSatisfy { $0.utf8.count <= 4_096 },
                        "reported_identifiers_over_bound")
            return Check(id: id, status: "PASS", elapsedMilliseconds: milliseconds(since: started),
                         ids: value.ids, counts: value.counts, sha256: value.sha256, errorCode: nil)
        } catch {
            return Check(id: id, status: "FAIL", elapsedMilliseconds: milliseconds(since: started),
                         ids: [], counts: [:], sha256: [:], errorCode: sanitized(error))
        }
    }

    private static func emit(_ checks: [Check]) throws {
        let passed = checks.filter { $0.status == "PASS" }.count
        let report = Report(
            status: checks.count == caseIDs.count && passed == caseIDs.count ? "PASS" : "FAIL",
            scope: "real_public_sefaria_production_facade", count: checks.count,
            passed: passed, failed: checks.count - passed, checks: checks
        )
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.sortedKeys, .withoutEscapingSlashes]
        let encoded = try encoder.encode(report)
        FileHandle.standardOutput.write(encoded)
        FileHandle.standardOutput.write(Data([0x0a]))
    }

    private static func require(_ condition: Bool, _ code: String) throws {
        guard condition else { throw Failure.assertion(code) }
    }

    private static func payloadObject(_ raw: String) throws -> [String: Any] {
        let bytes = Data(raw.utf8)
        try require(bytes.count > 2 && bytes.count <= 16 * 1_024 * 1_024,
                    "preserved_payload_empty_or_over_bound")
        guard let value = try JSONSerialization.jsonObject(with: bytes) as? [String: Any], !value.isEmpty else {
            throw Failure.assertion("preserved_payload_not_json_object")
        }
        return value
    }

    private static func containsHebrew(_ value: String) -> Bool {
        value.unicodeScalars.contains { (0x05d0...0x05ea).contains($0.value) }
    }

    private static func digest(_ value: String) -> String {
        AnyContentDigest.sha256(Data(value.utf8))
    }

    private static func digestJSON<T: Encodable>(_ value: T) throws -> String {
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.sortedKeys, .withoutEscapingSlashes]
        return AnyContentDigest.sha256(try encoder.encode(value))
    }

    private static func milliseconds(since started: Date) -> Int {
        max(0, Int(Date().timeIntervalSince(started) * 1_000))
    }

    /// Descriptions can include response text or transport URLs. Keep only our
    /// constant assertion codes and the foreign error's concrete type name.
    private static func sanitized(_ error: Error) -> String {
        if let failure = error as? Failure {
            switch failure {
            case .assertion(let code): return code
            case .deadlineExceeded: return "check_deadline_exceeded"
            case .failedChecks: return "one_or_more_checks_failed"
            }
        }
        if error is CancellationError { return "cancelled" }
        return "provider_error_type:" + String(reflecting: type(of: error))
    }
}
