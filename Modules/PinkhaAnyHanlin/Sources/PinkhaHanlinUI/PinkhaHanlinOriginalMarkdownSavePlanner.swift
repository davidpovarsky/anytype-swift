#if os(iOS)
import Foundation
import SwiftStreamingMarkdown
import PinkhaHanlinCore
import PinkhaAnyHanlin

/// Original parser ownership stays local to this call. Only the fully converted
/// Sendable plan leaves it; the original non-Sendable AST is not shared with UI
/// or the native worker. This helper grants no permission and advertises no tool.
public enum PinkhaHanlinOriginalMarkdownSavePlanner {
    /// Presentation-only eligibility using the original completed parser and
    /// the same strict content builder as convert(_:). No identity, native
    /// authority or manifest is fabricated. A later real invocation must still
    /// pass original consent, engine-specific preflight and complete readback.
    public static func supportsCompletedMessage(title: String, markdown: String,
                                                citationCoder: CitationCoder = .default) async -> Bool {
        do {
            try PinkhaHanlinSaveMessagePlan.validateContent(title: title, markdown: markdown)
            try Task.checkCancellation()
            let parser = MarkdownParserImpl()
            let result = await parser.parse(text: markdown, option: .init(speculativeRewrite: false))
            try Task.checkCancellation()
            try PinkhaHanlinMarkdownSaveConversion.validateCompletedMessageContent(
                title: title, markdown: markdown, originalDocument: result.document,
                originalSourceText: result.sourceText, speculativeRewritten: result.speculativeRewritten,
                citationMarker: citationCoder.citationMarker,
                citationMarkerQueryParam: citationCoder.citationMarkerQueryParam)
            return !Task.isCancelled
        } catch {
            return false
        }
    }

    public static func convert(_ plan: PinkhaHanlinSaveMessagePlan,
                               citationCoder: CitationCoder = .default) async throws -> PinkhaHanlinMarkdownSaveConversion {
        try Task.checkCancellation()
        let parser = MarkdownParserImpl()
        let result = await parser.parse(text: plan.markdown, option: .init(speculativeRewrite: false))
        try Task.checkCancellation()
        return try .init(plan: plan, originalDocument: result.document,
            originalSourceText: result.sourceText, speculativeRewritten: result.speculativeRewritten,
            citationMarker: citationCoder.citationMarker,
            citationMarkerQueryParam: citationCoder.citationMarkerQueryParam)
    }
}
#endif
