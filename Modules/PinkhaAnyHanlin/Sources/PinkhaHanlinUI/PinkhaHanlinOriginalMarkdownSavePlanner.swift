#if os(iOS)
import Foundation
import SwiftStreamingMarkdown
import PinkhaHanlinCore
import PinkhaAnyHanlin

/// Original parser ownership stays local to this call. Only the fully converted
/// Sendable plan leaves it; the original non-Sendable AST is not shared with UI
/// or the native worker. This helper grants no permission and advertises no tool.
public enum PinkhaHanlinOriginalMarkdownSavePlanner {
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
