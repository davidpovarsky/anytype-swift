import SwiftUI
import UIKit
import HanlinChatUI
import HanlinScriptUI
import HanlinPresentationKit

/// Layout composition only. Message rendering, input and send control are canonical Hanlin UI.
struct PinkhaHanlinChatView: View {
    @Bindable var presentation: PinkhaHanlinChatPresentation

    var body: some View {
        NavigationStack {
            VStack(spacing: 0) {
                if presentation.hasSource {
                    Button(action: presentation.requestContextReadConsent) {
                        AnytypeText(presentation.readAllowed ? PinkhaHanlinStrings.contextShared : PinkhaHanlinStrings.shareContext,
                                    style: .bodyRegular)
                    }
                    .disabled(presentation.isStreaming || presentation.readAllowed)
                    .accessibilityIdentifier("pinkha.hanlin.share-context")
                    .padding()
                }
                if let error = presentation.errorMessage {
                    HanlinChatErrorBanner(errorMessage: error)
                }
                if presentation.isConfigured {
                    chat
                } else {
                    PinkhaHanlinConnectionView(presentation: presentation)
                }
            }
            .navigationTitle(PinkhaHanlinStrings.title)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button(action: presentation.invalidate) {
                        AnytypeText(PinkhaHanlinStrings.close, style: .bodyRegular)
                    }
                    .accessibilityIdentifier("pinkha.hanlin.close")
                }
                if presentation.hasSource {
                    ToolbarItem(placement: .primaryAction) {
                        Button(action: presentation.returnToSource) {
                            AnytypeText(PinkhaHanlinStrings.returnToSource, style: .bodyRegular)
                        }
                        .disabled(presentation.isReturningToSource)
                        .accessibilityIdentifier("pinkha.hanlin.return-to-source")
                    }
                }
            }
        }
        .accessibilityIdentifier("pinkha.hanlin.chat")
    }

    private var chat: some View {
        HanlinChatView(shell: ShellDescriptor(id: "anytype.hanlin", title: PinkhaHanlinStrings.title)) {
            ScrollViewReader { reader in
                ScrollView {
                    LazyVStack(spacing: 12) {
                        ForEach(presentation.messages) { message in
                            HanlinChatMessageBubble(message: message,
                                isStreaming: presentation.isStreaming && message.id == presentation.messages.last?.id,
                                presentationMode: .full)
                                .id(message.id)
                        }
                        ForEach(Array(presentation.receiptMessages.enumerated()), id: \.offset) { _, receipt in
                            AnytypeText(receipt, style: .caption1Regular)
                                .foregroundStyle(Color.Text.secondary)
                        }
                    }
                    .padding()
                    .padding(.bottom, 96)
                }
                .onChange(of: presentation.messages.last?.content) { _, _ in
                    if let last = presentation.messages.last { reader.scrollTo(last.id, anchor: .bottom) }
                }
            }
        } composer: {
            HanlinChatComposer(text: $presentation.draft, canSend: presentation.canSend,
                isStreaming: presentation.isStreaming, presentationMode: .full,
                placeholder: PinkhaHanlinStrings.prompt, onSend: presentation.send)
                .accessibilityIdentifier("pinkha.hanlin.composer")
        }
    }
}

private struct PinkhaHanlinConnectionView: View {
    let presentation: PinkhaHanlinChatPresentation
    @State private var endpoint = "https://api.openai.com/v1"
    @State private var model = ""
    @State private var credential = ""

    var body: some View {
        Form {
            Section {
                AnytypeText(PinkhaHanlinStrings.connectionDescription, style: .bodyRegular)
                TextField(PinkhaHanlinStrings.endpoint, text: $endpoint)
                    .keyboardType(.URL)
                    .textInputAutocapitalization(.never)
                    .autocorrectionDisabled()
                TextField(PinkhaHanlinStrings.model, text: $model)
                    .textInputAutocapitalization(.never)
                    .autocorrectionDisabled()
                SecureField(PinkhaHanlinStrings.credential, text: $credential)
                    .textInputAutocapitalization(.never)
                    .autocorrectionDisabled()
                Button {
                    presentation.configure(endpoint: endpoint, model: model, credential: credential)
                    credential = ""
                } label: {
                    AnytypeText(PinkhaHanlinStrings.connect, style: .bodyRegular)
                }
                .accessibilityIdentifier("pinkha.hanlin.connect")
            }
            Section {
                AnytypeText(PinkhaHanlinStrings.sessionPrivacy, style: .caption1Regular)
            }
        }
        .onDisappear { credential = "" }
    }
}

@MainActor
final class PinkhaHanlinChatController: UIHostingController<PinkhaHanlinChatView>, UIAdaptivePresentationControllerDelegate {
    let presentation: PinkhaHanlinChatPresentation

    init(presentation: PinkhaHanlinChatPresentation) {
        self.presentation = presentation
        super.init(rootView: PinkhaHanlinChatView(presentation: presentation))
        modalPresentationStyle = .pageSheet
    }

    @available(*, unavailable)
    required init?(coder: NSCoder) { return nil }

    override func viewDidAppear(_ animated: Bool) {
        super.viewDidAppear(animated)
        presentationController?.delegate = self
        presentation.didMount(self)
    }

    override func viewDidDisappear(_ animated: Bool) {
        super.viewDidDisappear(animated)
        if isBeingDismissed || presentingViewController == nil {
            #if DEBUG && targetEnvironment(simulator)
            PinkhaHanlinNativeAcceptanceDriver.observedInvalidation(sessionID: presentation.session.id, cause: "presentationRemoved")
            #endif
            presentation.invalidate()
        }
    }

    func presentationControllerDidDismiss(_ presentationController: UIPresentationController) {
        #if DEBUG && targetEnvironment(simulator)
        PinkhaHanlinNativeAcceptanceDriver.observedInvalidation(sessionID: presentation.session.id, cause: "interactivePresentationDismissal")
        #endif
        presentation.invalidate()
    }
}
