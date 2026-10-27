import SwiftUI
import UIKit
import PinkhaKit
import Services

@MainActor
enum PinkhaNavigationGestureBridge {
    private struct Target: Equatable {
        let objectId: String
        let spaceId: String
    }

    private final class Entry {
        weak var controller: FullScreenSwipeNavigationController?
        var target: Target?
        var isPinkhaWritingDocument = false
        var layoutDirection: PinkhaLayoutDirection = .leftToRight
        var resolutionTask: Task<Void, Never>?
        let originalSemanticContentAttribute: UISemanticContentAttribute
        let originalInteractivePopEnabled: Bool?
        let originalContentPopEnabled: Bool?
        var didOverrideSystemPop = false
        lazy var systemPopObserver = SystemPopObserver(controller: controller)

        init(controller: FullScreenSwipeNavigationController) {
            self.controller = controller
            originalSemanticContentAttribute = controller.view.semanticContentAttribute
            originalInteractivePopEnabled = controller.interactivePopGestureRecognizer?.isEnabled
            if #available(iOS 26.0, *) {
                originalContentPopEnabled = controller.interactiveContentPopGestureRecognizer?.isEnabled
            } else {
                originalContentPopEnabled = nil
            }
        }

        deinit {
            resolutionTask?.cancel()
        }
    }

    private final class SystemPopObserver: NSObject {
        weak var controller: FullScreenSwipeNavigationController?

        init(controller: FullScreenSwipeNavigationController?) {
            self.controller = controller
        }

        @objc func handle(_ recognizer: UIGestureRecognizer) {
            guard let controller,
                  let pan = recognizer as? UIPanGestureRecognizer else {
                return
            }
            switch recognizer.state {
            case .began, .changed:
                let width = controller.view.bounds.width
                guard width > 0 else { return }
                controller.onInteractivePopProgress?(
                    PinkhaNavigationGestureBridge.normalizedProgress(
                        controller: controller,
                        translationX: pan.translation(in: controller.view).x,
                        containerWidth: width
                    )
                )
            case .ended, .cancelled, .failed:
                if controller.transitionCoordinator == nil {
                    controller.onInteractivePopAborted?()
                }
            default:
                break
            }
        }
    }

    private static var entries = [ObjectIdentifier: Entry]()

    static func update(
        controller: FullScreenSwipeNavigationController,
        topNavigationItem: AnyHashable?,
        layoutDirection: LayoutDirection
    ) {
        let key = ObjectIdentifier(controller)
        let entry: Entry
        if let existingEntry = entries[key], existingEntry.controller === controller {
            entry = existingEntry
        } else {
            // ObjectIdentifier values may be reused after a navigation controller is released.
            entry = Entry(controller: controller)
            entries[key] = entry
        }

        entry.layoutDirection = layoutDirection == .rightToLeft ? .rightToLeft : .leftToRight
        let editorData = topNavigationItem?.base as? EditorScreenData
        let nextTarget = editorData.flatMap { data -> Target? in
            guard let objectId = data.objectId else { return nil }
            return Target(objectId: objectId, spaceId: data.spaceId)
        }

        if entry.target != nextTarget {
            entry.resolutionTask?.cancel()
            entry.target = nextTarget
            entry.isPinkhaWritingDocument = nextTarget.map {
                PinkhaDocumentIdentityStorage.shared.isConfirmed(
                    objectId: $0.objectId,
                    spaceId: $0.spaceId
                )
            } ?? false
            if let nextTarget, !entry.isPinkhaWritingDocument {
                resolveIdentity(for: nextTarget, entry: entry)
            }
        } else if let nextTarget,
                  PinkhaDocumentIdentityStorage.shared.isConfirmed(
                    objectId: nextTarget.objectId,
                    spaceId: nextTarget.spaceId
                  ) {
            entry.isPinkhaWritingDocument = true
        }

        applySystemNavigation(to: entry)
        pruneReleasedControllers()
    }

    /// The approved host hook uses this result to suspend Anytype's private-selector pan only
    /// while UIKit's public, direction-aware transition recognizer owns Pinkha RTL navigation.
    static func requiresPublicEdgePop(
        controller: FullScreenSwipeNavigationController
    ) -> Bool {
        guard let entry = entries[ObjectIdentifier(controller)] else { return false }
        return requiresPublicSystemPop(entry)
    }

    static func normalizedProgress(
        controller: FullScreenSwipeNavigationController,
        translationX: CGFloat,
        containerWidth: CGFloat
    ) -> CGFloat {
        guard let entry = entries[ObjectIdentifier(controller)],
              requiresPublicSystemPop(entry) else {
            return translationX / containerWidth
        }
        return CGFloat(PinkhaNavigationDirectionPolicy.normalizedBackProgress(
            translationX: Double(translationX),
            containerWidth: Double(containerWidth),
            layoutDirection: entry.layoutDirection
        ))
    }

    private static func requiresPublicSystemPop(_ entry: Entry) -> Bool {
        entry.layoutDirection == .rightToLeft && entry.isPinkhaWritingDocument
    }

    private static func resolveIdentity(for target: Target, entry: Entry) {
        entry.resolutionTask = Task { @MainActor [weak entry] in
            let isPinkha = await authoritativeIdentity(for: target)
            guard !Task.isCancelled,
                  let entry,
                  entry.target == target else {
                return
            }
            entry.isPinkhaWritingDocument = isPinkha
            entry.resolutionTask = nil
            if isPinkha {
                PinkhaDocumentIdentityStorage.shared.registerConfirmed(
                    objectId: target.objectId,
                    spaceId: target.spaceId
                )
            }
            applySystemNavigation(to: entry)
        }
    }

    private static func authoritativeIdentity(for target: Target) async -> Bool {
        guard PinkhaRuntime.enabled else { return false }

        let manifest: PinkhaSpaceManifest
        if let cached = Container.shared.pinkhaBootstrapService().manifest(forSpaceId: target.spaceId) {
            manifest = cached
        } else {
            let stateManager = Container.shared.pinkhaBootstrapStateManager()
            if case .uninitialized = stateManager.state(for: target.spaceId) {
                PinkhaBootstrapHook.handleSpaceActivated(spaceId: target.spaceId)
            }
            guard let ready = try? await stateManager.awaitReadiness(
                spaceId: target.spaceId,
                timeoutSeconds: 15
            ) else {
                return false
            }
            manifest = ready
        }

        guard let response = try? await ClientCommands.objectShow(.with {
            $0.contextID = target.objectId
            $0.objectID = target.objectId
            $0.spaceID = target.spaceId
        }).invoke(qos: .userInitiated, ignoreLogErrors: .objectDeleted),
        let detailsStruct = response.objectView.details.first(where: { $0.id == target.objectId })?.details,
        let details = try? ObjectDetails(protobufStruct: detailsStruct) else {
            return false
        }
        return manifest.isRegisteredDocumentType(typeId: details.type)
    }

    private static func applySystemNavigation(to entry: Entry) {
        guard let controller = entry.controller else { return }
        let usePublicRTLPop = requiresPublicSystemPop(entry)

        if usePublicRTLPop {
            controller.view.semanticContentAttribute = .forceRightToLeft
            // Do not retarget UIKit's edge recognizer by mutating its `edges`: on device that
            // changed recognition geometry without changing the transition driver's direction.
            // iOS 26's public content-pop recognizer is installed by UINavigationController,
            // owns the real interactive transition, and follows leading-to-trailing semantics.
            controller.interactivePopGestureRecognizer?.isEnabled = false
            if #available(iOS 26.0, *) {
                if let contentPop = controller.interactiveContentPopGestureRecognizer {
                    if !entry.didOverrideSystemPop {
                        contentPop.addTarget(
                            entry.systemPopObserver,
                            action: #selector(SystemPopObserver.handle(_:))
                        )
                    }
                    contentPop.isEnabled = true
                }
            }
            entry.didOverrideSystemPop = true
            return
        }

        guard entry.didOverrideSystemPop else { return }
        controller.view.semanticContentAttribute = entry.originalSemanticContentAttribute
        if let original = entry.originalInteractivePopEnabled {
            controller.interactivePopGestureRecognizer?.isEnabled = original
        }
        if #available(iOS 26.0, *),
           let contentPop = controller.interactiveContentPopGestureRecognizer {
            contentPop.removeTarget(
                entry.systemPopObserver,
                action: #selector(SystemPopObserver.handle(_:))
            )
            if let original = entry.originalContentPopEnabled {
                contentPop.isEnabled = original
            }
        }
        entry.didOverrideSystemPop = false
    }

    private static func pruneReleasedControllers() {
        entries = entries.filter { _, entry in entry.controller != nil }
    }
}
