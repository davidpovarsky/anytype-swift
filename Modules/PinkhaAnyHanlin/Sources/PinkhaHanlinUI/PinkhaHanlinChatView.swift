#if canImport(UIKit)
import SwiftUI
import UIKit
import HanlinChatUI
import HanlinScriptUI
import HanlinPresentationKit

/// Layout composition only. Message rendering, input and send control are canonical Hanlin UI.
public struct PinkhaHanlinChatView: View {
    @Bindable var presentation: PinkhaHanlinChatPresentation

    public init(presentation: PinkhaHanlinChatPresentation) { self.presentation = presentation }

    public var body: some View {
        NavigationStack {
            VStack(spacing: 0) {
                if presentation.hasSource {
                    Button(action: presentation.requestContextReadConsent) {
                        presentation.appearance.label(presentation.readAllowed ? PinkhaHanlinStrings.contextShared : PinkhaHanlinStrings.shareContext,
                                    .body)
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
                        presentation.appearance.label(PinkhaHanlinStrings.close, .body)
                    }
                    .accessibilityIdentifier("pinkha.hanlin.close")
                }
                if presentation.hasSource {
                    ToolbarItem(placement: .primaryAction) {
                        Button(action: presentation.returnToSource) {
                            presentation.appearance.label(PinkhaHanlinStrings.returnToSource, .body)
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
                            presentation.appearance.label(receipt, .caption)
                                .foregroundStyle(presentation.appearance.secondary)
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
                presentation.appearance.label(PinkhaHanlinStrings.connectionDescription, .body)
                TextField(PinkhaHanlinStrings.endpoint, text: $endpoint)
                    .accessibilityLabel(Text(PinkhaHanlinStrings.endpoint))
                    .accessibilityIdentifier("pinkha.hanlin.connection.endpoint")
                    .keyboardType(.URL)
                    .textInputAutocapitalization(.never)
                    .autocorrectionDisabled()
                TextField(PinkhaHanlinStrings.model, text: $model)
                    .accessibilityLabel(Text(PinkhaHanlinStrings.model))
                    .accessibilityIdentifier("pinkha.hanlin.connection.model")
                    .textInputAutocapitalization(.never)
                    .autocorrectionDisabled()
                SecureField(PinkhaHanlinStrings.credential, text: $credential)
                    .accessibilityLabel(Text(PinkhaHanlinStrings.credential))
                    .accessibilityIdentifier("pinkha.hanlin.connection.credential")
                    .textInputAutocapitalization(.never)
                    .autocorrectionDisabled()
                Button {
                    presentation.configure(endpoint: endpoint, model: model, credential: credential)
                    credential = ""
                } label: {
                    presentation.appearance.label(PinkhaHanlinStrings.connect, .body)
                }
                .accessibilityIdentifier("pinkha.hanlin.connect")
            }
            Section {
                presentation.appearance.label(PinkhaHanlinStrings.sessionPrivacy, .caption)
            }
        }
        .onDisappear { credential = "" }
    }
}

@MainActor
public final class PinkhaHanlinChatController: UIHostingController<PinkhaHanlinChatView>, UIAdaptivePresentationControllerDelegate {
    public let presentation: PinkhaHanlinChatPresentation

    public init(presentation: PinkhaHanlinChatPresentation) {
        self.presentation = presentation
        super.init(rootView: PinkhaHanlinChatView(presentation: presentation))
        modalPresentationStyle = .pageSheet
    }

    @available(*, unavailable)
    public required init?(coder: NSCoder) { return nil }

    public func revoke() { presentation.invalidate() }
    public func drain() async { await presentation.revokeAndDrain() }

    public override func viewDidAppear(_ animated: Bool) {
        super.viewDidAppear(animated)
        presentationController?.delegate = self
        presentation.didMount(self)
    }

    public override func viewWillDisappear(_ animated: Bool) {
        super.viewWillDisappear(animated)
        if isBeingDismissed || isMovingFromParent || presentingViewController == nil {
            presentation.ownerWillDisappear()
        }
    }

    public override func viewDidDisappear(_ animated: Bool) {
        super.viewDidDisappear(animated)
        if isBeingDismissed || presentingViewController == nil {
            presentation.observedInvalidation("presentationRemoved")
            presentation.invalidate()
        }
    }

    public func presentationControllerDidDismiss(_ presentationController: UIPresentationController) {
        presentation.observedInvalidation("interactivePresentationDismissal")
        presentation.invalidate()
    }
}

#endif
