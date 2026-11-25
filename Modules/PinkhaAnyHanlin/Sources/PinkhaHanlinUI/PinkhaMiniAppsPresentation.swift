#if canImport(UIKit)
import Foundation
import SwiftUI
import UIKit
import HanlinMiniAppsBridge
import HanlinMiniAppsPicker

/// One source-ownership key shared by both adapters. Existing bridge requests
/// without this key were issued by the original Heart-only application.
public enum PinkhaMiniAppsEngineScope: String, Sendable {
    case heart, any
    public static let metadataKey = "pinkha.engine"
    public func matches(_ source: MiniAppSourceContext) -> Bool {
        guard let engine = source.metadata[Self.metadataKey] else { return self == .heart }
        return engine == rawValue
    }
}

/// Engine adapters own source capture, authorization, native writes and ACK.
/// This shared presentation owns only the common picker and result sheet.
@MainActor
public enum PinkhaMiniAppsPresentation {
    public static func makePicker(store: MiniAppBridgeStore, source: MiniAppSourceContext,
                                  inputs: [MiniAppContent], operation: MiniAppOperation,
                                  callbacks: MiniAppCallbacks,
                                  onOpen: @escaping (URL) -> Void) -> UIViewController {
        let picker = MiniAppPicker(store: store, source: source, inputs: inputs,
                                   operation: operation, callbacks: callbacks, onOpen: onOpen)
        let controller = UIHostingController(rootView: picker)
        configureSheet(controller)
        return controller
    }

    public static func makeResult(result: MiniAppResult, store: MiniAppBridgeStore,
                                  title: String, attachmentTitle: String, closeTitle: String,
                                  onClosed: @escaping () -> Void) -> UIViewController {
        let controller = PinkhaMiniAppsResultController(result: result, store: store,
            title: title, attachmentTitle: attachmentTitle, closeTitle: closeTitle, onClosed: onClosed)
        configureSheet(controller)
        controller.presentationController?.delegate = controller
        return controller
    }

    private static func configureSheet(_ controller: UIViewController) {
        controller.modalPresentationStyle = .pageSheet
        controller.sheetPresentationController?.detents = [.medium(), .large()]
        controller.sheetPresentationController?.prefersGrabberVisible = true
    }
}

@MainActor
private final class PinkhaMiniAppsResultController: UIHostingController<PinkhaMiniAppsResultView>, UIAdaptivePresentationControllerDelegate {
    private let onClosed: () -> Void
    private var finished = false

    init(result: MiniAppResult, store: MiniAppBridgeStore, title: String, attachmentTitle: String, closeTitle: String, onClosed: @escaping () -> Void) {
        self.onClosed = onClosed
        super.init(rootView: PinkhaMiniAppsResultView(result: result, store: store, title: title, attachmentTitle: attachmentTitle, closeTitle: closeTitle, onDone: {}))
        rootView = PinkhaMiniAppsResultView(result: result, store: store, title: title, attachmentTitle: attachmentTitle, closeTitle: closeTitle) { [weak self] in
            guard let self else { return }
            dismiss(animated: true) { self.finish() }
        }
    }

    @available(*, unavailable)
    required init?(coder: NSCoder) { fatalError("unavailable initializer") }

    func presentationControllerDidDismiss(_ presentationController: UIPresentationController) {
        finish()
    }

    private func finish() {
        guard !finished else { return }
        finished = true
        onClosed()
    }
}

private struct PinkhaMiniAppsResultView: View {
    let result: MiniAppResult
    let store: MiniAppBridgeStore
    let title: String
    let attachmentTitle: String
    let closeTitle: String
    let onDone: () -> Void

    var body: some View {
        NavigationStack {
            List {
                if let message = result.message, !message.isEmpty {
                    Text(message).textSelection(.enabled)
                }
                ForEach(Array(result.items.enumerated()), id: \.offset) { _, item in
                    switch item.kind {
                    case .text, .json:
                        Text(item.text ?? "").textSelection(.enabled)
                    case .url:
                        if let url = item.url { Link(item.name ?? url.absoluteString, destination: url) }
                    case .file:
                        if let id = item.attachmentID, let url = try? store.attachmentURL(id: id) {
                            ShareLink(item: url) {
                                Label(item.name ?? attachmentTitle, systemImage: "doc")
                            }
                        }
                    }
                }
            }
            .navigationTitle(title)
            .toolbar {
                ToolbarItem(placement: .confirmationAction) {
                    Button(closeTitle, action: onDone)
                }
            }
        }
    }
}

#endif
