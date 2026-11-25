import Foundation
import HanlinMiniAppsBridge

struct PinkhaMiniAppsBlockSnapshot: Codable, Equatable, Sendable {
    let id: String
    let text: String
    let marks: Data
}

/// Persisted before any native edit, so a cold callback resumes the same operation.
struct PinkhaMiniAppsEditPlan: Codable, Sendable {
    struct Mutation: Codable, Sendable {
        let before: PinkhaMiniAppsBlockSnapshot
        let location: Int
        let length: Int
        let replacement: String

        var afterText: String? {
            guard let range = PinkhaMiniAppsEditPlanner.range(location: location, length: length, in: before.text)
            else { return nil }
            var text = before.text
            text.replaceSubrange(range, with: replacement)
            return text
        }
    }

    let requestID: UUID
    var mutations: [Mutation]
    var additions: [MiniAppContent]
    var appliedBlocks: Set<String> = []
    var insertedBlocks: [String: String] = [:]
    var preservedNewerContent = false
    var completed = false
}

enum PinkhaMiniAppsEditPlanner {
    enum Failure: Error { case invalidSource, invalidRange, unsupportedEdit }

    static func make(request: MiniAppInvocation, result: MiniAppResult) throws -> PinkhaMiniAppsEditPlan {
        guard request.id == result.requestID,
              let encoded = request.source.metadata["anytype.blocks"]?.data(using: .utf8),
              let snapshots = try? JSONDecoder().decode([PinkhaMiniAppsBlockSnapshot].self, from: encoded),
              Set(snapshots.map(\.id)).count == snapshots.count else { throw Failure.invalidSource }
        let source = Dictionary(uniqueKeysWithValues: snapshots.map { ($0.id, $0) })
        var plan = PinkhaMiniAppsEditPlan(requestID: request.id, mutations: [], additions: [])
        let textItems = result.items.filter { $0.kind == .text || $0.kind == .json }
        let text = textItems.compactMap(\.text).joined(separator: "\n")
        let otherItems = result.items.filter { $0.kind != .text && $0.kind != .json }

        switch result.operation {
        case .display, .custom:
            return plan
        case .insert:
            if let selection = request.source.selection, selection.blockIDs.count == 1,
               let before = source[selection.blockIDs[0]], !textItems.isEmpty {
                // Inserting preserves the selected text and starts at its trailing caret.
                let position = selection.location.addingReportingOverflow(selection.length)
                guard !position.overflow,
                      range(location: position.partialValue, length: 0, in: before.text) != nil
                else { throw Failure.invalidRange }
                plan.mutations = [.init(before: before, location: position.partialValue, length: 0, replacement: text)]
                plan.additions = otherItems
            } else {
                plan.additions = result.items
            }
        case .replaceSelection:
            guard let selection = request.source.selection else { throw Failure.invalidSource }
            let selected = selection.blockIDs.compactMap { source[$0] }
            guard !selected.isEmpty else {
                // A file-only selection remains intact; returned items are inserted next to it.
                plan.additions = result.items
                return plan
            }
            guard !textItems.isEmpty else {
                plan.additions = result.items
                return plan
            }
            if selected.count == 1 {
                let before = selected[0]
                guard let selectedRange = range(location: selection.location, length: selection.length, in: before.text),
                      String(before.text[selectedRange]) == selection.text
                else { throw Failure.invalidRange }
                plan.mutations = [.init(before: before, location: selection.location,
                    length: selection.length, replacement: text)]
            } else {
                // Keep native IDs, children, styles and annotations attached to their blocks.
                // A block selection replaces textual content in its original document order.
                let ordered = snapshots.filter { selection.blockIDs.contains($0.id) }
                plan.mutations = ordered.enumerated().map { index, before in
                    .init(before: before, location: 0, length: before.text.utf16.count,
                          replacement: index == 0 ? text : "")
                }
            }
            plan.additions = otherItems
        case .replaceDocument:
            guard !textItems.isEmpty else { throw Failure.unsupportedEdit }
            if snapshots.isEmpty {
                plan.additions = result.items
            } else {
                // Body replacement preserves title, non-text blocks and the native block tree.
                plan.mutations = snapshots.enumerated().map { index, before in
                    .init(before: before, location: 0, length: before.text.utf16.count,
                          replacement: index == 0 ? text : "")
                }
                plan.additions = otherItems
            }
        }
        return plan
    }

    static func range(location: Int, length: Int, in text: String) -> Range<String.Index>? {
        guard location >= 0, length >= 0, location <= text.utf16.count,
              length <= text.utf16.count - location else { return nil }
        return Range(NSRange(location: location, length: length), in: text)
    }

    /// Preserve each unaffected part of a native mark in UTF16 coordinates.
    static func shiftedMarkRanges(from: Int, to: Int, editLocation: Int,
                                  editLength: Int, replacementLength: Int) -> [NSRange] {
        guard from >= 0, to > from else { return [] }
        let editEnd = editLocation + editLength
        let delta = replacementLength - editLength
        if to <= editLocation { return [NSRange(location: from, length: to - from)] }
        if from >= editEnd { return [NSRange(location: from + delta, length: to - from)] }
        var parts: [NSRange] = []
        if from < editLocation { parts.append(NSRange(location: from, length: editLocation - from)) }
        if to > editEnd {
            let start = editLocation + replacementLength
            parts.append(NSRange(location: start, length: to - editEnd))
        }
        return parts
    }

    enum ReplayDecision: Equatable { case apply, alreadyApplied, preserveNewerContent }
    static func replayDecision(mutation: PinkhaMiniAppsEditPlan.Mutation,
                               current: PinkhaMiniAppsBlockSnapshot?, alreadyRecorded: Bool,
                               expectedMarks: Data) -> ReplayDecision {
        if alreadyRecorded { return .alreadyApplied }
        guard let current else { return .preserveNewerContent }
        if current.text == mutation.afterText && current.marks == expectedMarks { return .alreadyApplied }
        if current == mutation.before { return .apply }
        return .preserveNewerContent
    }
}
