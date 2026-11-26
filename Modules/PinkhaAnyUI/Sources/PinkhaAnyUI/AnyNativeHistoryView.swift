#if canImport(UIKit) && canImport(SwiftUI)
import Foundation
import SwiftUI
import PinkhaAnyHost

/// A document-owned read-only browser. The live editor is never replaced by a
/// historical snapshot and this screen has no restore or history-write action.
struct AnyNativeHistoryView: View {
    @Bindable var presentation: AnyNativeHistoryPresentation
    @State private var path: [String] = []
    @Environment(\.dismiss) private var dismiss
    @Environment(\.scenePhase) private var scenePhase

    var body: some View {
        NavigationStack(path: $path) {
            List {
                Section {
                    Text(AnyUIErrorText.text(
                        "גרסאות שמורות של המסמך. התאריכים נרשמו במכשיר של המחבר.",
                        "Saved document versions. Dates come from the author’s device."))
                        .font(.footnote).foregroundStyle(.secondary)
                }
                if presentation.isLoading && presentation.changes.isEmpty {
                    ProgressView(AnyUIErrorText.text("טוען גרסאות", "Loading versions"))
                }
                if let problem = presentation.problem {
                    historyProblem(problem)
                        .accessibilityIdentifier("any-native-history-problem")
                }
                if !presentation.isLoading && presentation.changes.isEmpty && presentation.problem == nil {
                    ContentUnavailableView(AnyUIErrorText.text("אין גרסאות שמורות", "No saved versions"),
                                           systemImage: "clock.arrow.circlepath")
                }
                ForEach(presentation.changes) { change in
                    NavigationLink(value: change.version) {
                        VStack(alignment: .leading, spacing: 4) {
                            Text(historyDate(change.timestamp))
                            Text(AnyUIErrorText.text("מחבר: ", "Author: ") + change.author)
                                .font(.caption).foregroundStyle(.secondary).lineLimit(1)
                            if change.truncated {
                                Text(AnyUIErrorText.text("התוכן המוקדם אינו זמין במכשיר", "Earlier content is unavailable on this device"))
                                    .font(.caption).foregroundStyle(.secondary)
                            }
                        }
                    }.accessibilityIdentifier("any-native-history-version-" + change.version)
                }
                if presentation.hasMore {
                    Button(AnyUIErrorText.text("טעינת גרסאות נוספות", "Load more versions")) {
                        Task { await presentation.loadMore() }
                    }.disabled(presentation.isLoading)
                        .accessibilityIdentifier("any-native-history-load-more")
                }
            }
            .accessibilityIdentifier("any-native-history-list")
            .navigationTitle(AnyUIErrorText.text("היסטוריית גרסאות", "Version history"))
            .navigationBarTitleDisplayMode(.inline)
            .navigationDestination(for: String.self) { version in
                AnyNativeHistoryVersionView(presentation: presentation, version: version, closeHistory: closeHistory)
            }
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button(AnyUIErrorText.text("סגירה", "Close"), action: closeHistory)
                        .accessibilityIdentifier("any-native-history-close")
                }
                ToolbarItem(placement: .primaryAction) {
                    Button(AnyUIErrorText.text("רענון", "Refresh"), systemImage: "arrow.clockwise") {
                        path = []
                        Task { await presentation.refresh() }
                    }.disabled(!presentation.isActive || presentation.isLoading)
                }
            }
        }
        .task { await presentation.refresh() }
        .onChange(of: scenePhase) { _, phase in
            if phase != .active { presentation.revoke() }
        }
        .onChange(of: presentation.isActive) { _, active in
            if !active { path = [] }
        }
        .onDisappear {
            presentation.revoke()
            Task { await presentation.drain() }
        }
    }

    private func closeHistory() {
        presentation.revoke()
        dismiss()
    }
}

private struct AnyNativeHistoryVersionView: View {
    @Bindable var presentation: AnyNativeHistoryPresentation
    let version: String
    let closeHistory: @MainActor () -> Void

    var body: some View {
        List {
            Section {
                Text(AnyUIErrorText.text(
                    "תצוגה מקדימה של הטקסט השמור. עיצוב, קבצים ונתונים נוספים עשויים שלא להופיע כאן. הטקסט מוצג עם סימון Markdown המקורי.",
                    "Preview of saved text. Formatting, files, and other saved data may not appear here. Text retains its original Markdown notation."))
                    .font(.footnote).foregroundStyle(.secondary)
            }
            if presentation.isLoadingVersion && presentation.selectedVersion == version {
                ProgressView(AnyUIErrorText.text("טוען גרסה", "Loading version"))
            } else if let problem = presentation.versionProblem {
                historyProblem(problem).accessibilityIdentifier("any-native-history-version-problem")
            } else if let saved = presentation.selected, saved.version == version {
                if let editor = saved.editor {
                    let byID = Dictionary(uniqueKeysWithValues: editor.blocks.map { ($0.id, $0) })
                    Section(AnyUIErrorText.text("טקסט שמור", "Saved text")) {
                        if editor.blocks.isEmpty {
                            Text(AnyUIErrorText.text("לא היו בלוקים של תוכן בגרסה זו", "This version had no content blocks"))
                        }
                        ForEach(editor.depthFirstIDs, id: \.self) { id in
                            if let block = byID[id] { historyBlock(block) }
                        }
                    }
                    if !editor.unreachableIDs.isEmpty {
                        Section(AnyUIErrorText.text("בלוקים שמורים נוספים", "Other saved blocks")) {
                            Text(AnyUIErrorText.text(
                                "מיקומם של הבלוקים האלה בעץ המסמך אינו זמין בגרסה זו.",
                                "These blocks have no reachable position in this version’s document structure."))
                                .font(.footnote).foregroundStyle(.secondary)
                            ForEach(editor.unreachableIDs, id: \.self) { id in
                                if let block = byID[id] { historyBlock(block) }
                            }
                        }
                    }
                } else {
                    Text(AnyUIErrorText.text("גרסה זו אינה כוללת תוכן של עורך המסמכים", "This version contains no document editor content"))
                }
                let other = saved.datasets.filter { $0.name != "editor_blocks" }
                if !other.isEmpty {
                    Section {
                        Text(AnyUIErrorText.text(
                            "בגרסה זו נשמרו גם נתונים נוספים שאינם מוצגים כתוכן המסמך.",
                            "This version also contains saved data that is not displayed as document content."))
                            .font(.footnote).foregroundStyle(.secondary)
                    }
                }
            }
        }
        .accessibilityIdentifier("any-native-history-preview")
        .navigationTitle(AnyUIErrorText.text("גרסה שמורה", "Saved version"))
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .cancellationAction) {
                Button(AnyUIErrorText.text("סגירה", "Close"), action: closeHistory)
                    .accessibilityIdentifier("any-native-history-close")
            }
        }
        .task(id: version) { await presentation.showVersion(version) }
        .onDisappear { presentation.closeVersion(version) }
    }
}

@ViewBuilder
private func historyBlock(_ block: AnyEditorBlock) -> some View {
    let textTypes: Set<String> = ["paragraph", "heading", "quote", "code", "list_item", "check_list_item"]
    VStack(alignment: .leading, spacing: 4) {
        if !textTypes.contains(block.type) {
            Text(AnyUIErrorText.text("בלוק ללא תצוגה מקדימה: ", "Block without a preview: ") + block.type)
                .font(.caption).foregroundStyle(.secondary)
        }
        if !block.text.isEmpty {
            Text(verbatim: block.text)
                .font(block.type == "code" ? .system(.body, design: .monospaced) : .body)
                .textSelection(.enabled)
        } else if textTypes.contains(block.type) {
            Text(AnyUIErrorText.text("בלוק טקסט ריק", "Empty text block"))
                .foregroundStyle(.secondary)
        }
    }.accessibilityIdentifier("any-native-history-block-" + block.id)
}

private func historyDate(_ timestamp: Int64) -> String {
    // Untrusted author clocks never control native order or data admission.
    guard (0...253_402_300_799).contains(timestamp) else {
        return AnyUIErrorText.text("תאריך המחבר אינו זמין", "Author date unavailable")
    }
    return Date(timeIntervalSince1970: TimeInterval(timestamp)).formatted(date: .abbreviated, time: .shortened)
}

private func historyProblem(_ problem: AnyNativeHistoryProblem) -> some View {
    let text: String
    switch problem {
    case .unavailable:
        text = AnyUIErrorText.text("היסטוריית גרסאות אינה זמינה במנוע הפעיל", "Version history is unavailable in the active engine")
    case .versionNotFound:
        text = AnyUIErrorText.text("הגרסה הזו אינה זמינה במכשיר", "This version is unavailable on this device")
    case .truncated:
        text = AnyUIErrorText.text("השינויים המוקדמים הדרושים לגרסה הזו אינם זמינים במכשיר", "Earlier changes needed for this version are unavailable on this device")
    case .viewTooLarge:
        text = AnyUIErrorText.text("הגרסה גדולה מדי לתצוגה המקדימה", "This version is too large to preview")
    case .paginationLimit:
        text = AnyUIErrorText.text("הוצג גבול הגרסאות לטעינה אחת. ייתכן שקיימות גרסאות נוספות.", "This view reached its version limit. More versions may exist.")
    case .paginationChanged:
        text = AnyUIErrorText.text("רשימת הגרסאות השתנתה במהלך הטעינה. אפשר לרענן ולנסות שוב.", "The version list changed while loading. Refresh to try again.")
    case .accessChanged:
        text = AnyUIErrorText.text("תצוגת ההיסטוריה אינה פעילה עוד. יש לסגור ולפתוח אותה מחדש כדי לבדוק את ההרשאות הנוכחיות.", "History is no longer active. Close and reopen it to check current access.")
    case .malformed:
        text = AnyUIErrorText.text("לא ניתן להציג את נתוני הגרסה שהתקבלו", "The returned version data cannot be displayed")
    case .failed:
        text = AnyUIErrorText.text("לא ניתן לטעון את היסטוריית הגרסאות כרגע", "Version history could not be loaded")
    }
    return Label(text, systemImage: "exclamationmark.circle").foregroundStyle(.secondary)
}
#endif
