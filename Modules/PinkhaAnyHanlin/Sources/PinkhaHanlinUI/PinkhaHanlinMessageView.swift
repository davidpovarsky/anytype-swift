#if canImport(UIKit)
import SwiftUI
import UIKit
import Translation
import HanlinChatCore
import HanlinChatUI
import HanlinPresentationKit
import HanlinAgentActivityUI
import SwiftStreamingMarkdown

/// Source-aware callbacks and layout around the ORIGINAL shared Hanlin message
/// components. Menus, previews, Markdown, selection and action controls stay in
/// the SDK, with the same implementation used by Hanlin itself.
struct PinkhaHanlinMessageView: View {
    let message: HanlinChatMessage
    let containerWidth: CGFloat
    let presentation: PinkhaHanlinChatPresentation
    @State private var showsSelection = false
    @State private var showsTranslation = false
    @State private var showsSources = false
    @State private var activityExpanded = false
    @State private var selectAll = false
    @State private var selectedText: String?
    @State private var isCopied = false
    @State private var copyFeedback = false
    @Environment(\.locale) private var locale
    @Environment(\.layoutDirection) private var layoutDirection
    @Environment(\.colorScheme) private var colorScheme
    @Environment(\.dynamicTypeSize) private var dynamicTypeSize

    private var isAssistant: Bool { message.role == "assistant" }
    private var isResponding: Bool {
        presentation.isRespondingToMessage(message.id)
    }
    private var activity: PinkhaHanlinMessageActivity? { presentation.activities[message.id] }
    private var content: HanlinCitationProjection {
        activity?.projection(text: message.content)
            ?? .make(text: message.content, messageID: message.id, sources: [], anchors: [])
    }
    private var actionState: HanlinMessageActionState {
        .init(isCopied: isCopied, copyFeedback: copyFeedback,
              isSpeaking: presentation.isSpeaking(message.id),
              isPersonallySaved: presentation.isMessageSaved(message.id),
              canSavePersonal: presentation.canSaveMessage(message.id), isResponding: isResponding)
    }

    private var actions: HanlinMessageActions {
        HanlinMessageActions(
            copy: message.content.isEmpty ? nil : copy,
            select: message.content.isEmpty ? nil : {
                guard presentation.canAccessMessage(message.id) else { return }
                selectedText = nil
                showsSelection = true
            },
            speech: isAssistant && !message.content.isEmpty ? { presentation.speak(message.id) } : nil,
            translate: isAssistant && !message.content.isEmpty ? {
                guard presentation.canAccessMessage(message.id) else { return }
                showsTranslation = true
            } : nil,
            // Visibility requires the original body-capable catalog and a
            // completed original SDK message; ordinary hosts keep it absent.
            savePersonal: presentation.hasMessageSaveAction(message.id)
                ? { presentation.saveMessage(message.id) } : nil,
            saveKnowledge: nil,
            delete: presentation.canModifyTranscript ? { presentation.deleteMessage(message.id) } : nil,
            retry: presentation.canRepeatResponse(message.id) ? { presentation.retryMessage(message.id) } : nil,
            continueResponse: presentation.canContinueResponse(message.id) ? { presentation.continueResponse(message.id) } : nil)
    }

    var body: some View {
        Group {
            if isAssistant {
                HanlinAssistantMessageBubble(isResponding: isResponding) {
                    presentation.appearance.label(PinkhaHanlinStrings.title, .caption)
                        .chatMessagePreviewSource(presentPreview)
                    if let activity {
                        HanlinAgentActivityView(snapshot: activity.snapshot(isActive: isResponding,
                            hasAnswerText: !message.content.isEmpty), isExpanded: $activityExpanded)
                    }
                    HanlinMessageMarkdownView(text: content.markdown, citationGroups: content.groups)
                        .environment(\.chatMessageLongPressPreview, presentPreview)
                    if let sources = activity?.sources, !sources.isEmpty {
                        HanlinSourcesButton(sources: sources, title: PinkhaHanlinStrings.sources) {
                            guard presentation.canAccessMessage(message.id) else { return }
                            showsSources = true
                        }
                    }
                    if !isResponding || !message.content.isEmpty {
                        HanlinMessageActionBar(actions: actions, state: actionState)
                    }
                }
                .frame(maxWidth: .infinity, alignment: .leading)
            } else {
                HanlinUserMessageBubble(text: message.content, containerWidth: containerWidth) {
                    HanlinMessageActionMenu(actions: actions.userMenu)
                }
                .frame(maxWidth: .infinity, alignment: .trailing)
            }
        }
        .sheet(isPresented: $showsSelection) {
            HanlinMessageSelectionView(text: message.content, shouldSelectAll: $selectAll,
                isCopied: isCopied, copy: copySelection) {
                ScrollView {
                    HanlinMessageMarkdownView(text: message.content,
                        onSelectionChanged: { selection in
                            selectedText = selection.text.isEmpty ? nil : selection.text
                        }, documentSelectionMode: true, selectAllRequest: $selectAll)
                        .padding()
                }
            }
        }
        .translationPresentation(isPresented: $showsTranslation, text: message.content)
        .sheet(isPresented: $showsSources) {
            HanlinSourcesList(sources: activity?.sources ?? [], title: PinkhaHanlinStrings.sources) { source in
                presentation.openSource(source, messageID: message.id)
            }
        }
        .onChange(of: message.content) { _, _ in isCopied = false }
    }

    private func presentPreview(from source: UIView, at point: CGPoint) {
        guard presentation.canAccessMessage(message.id) else { return }
        HanlinMessagePreviewPresenter.present(from: source, at: point,
            preferredWidth: containerWidth,
            style: .init(locale: locale, layoutDirection: layoutDirection,
                         colorScheme: colorScheme, dynamicTypeSize: dynamicTypeSize),
            actions: actions.assistantMenu(state: actionState)) {
                HanlinAssistantMessageBubble(isResponding: false) {
                    HanlinMessageMarkdownView(text: content.markdown, citationGroups: content.groups)
                }
            }
    }

    private func copy() {
        guard presentation.copyMessage(message.id) else { return }
        isCopied = true
        copyFeedback.toggle()
    }

    private func copySelection() {
        guard presentation.copyMessage(message.id, selection: selectedText) else { return }
        isCopied = true
        copyFeedback.toggle()
    }
}
#endif
