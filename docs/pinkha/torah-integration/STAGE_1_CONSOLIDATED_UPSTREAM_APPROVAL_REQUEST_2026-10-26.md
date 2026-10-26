# Stage 1 corrected consolidated approval request — H8 and H10 only — 2026-10-26

Status: **OWNER APPROVED AND APPLIED — 2026-10-26**.

The owner approved exactly the two unified diffs below in the 2026-10-26 Codex task. Their pre-edit blobs were revalidated immediately before application. Downstream-only hardening preserves Pinkha LTR's original `.left` marker value and configures/restores UIKit's public `UIScreenEdgePanGestureRecognizer.edges` without adding a transition driver.

H1–H7 and H9 were separately approved by the owner on 2026-10-26, revalidated, applied, and recorded in `docs/architecture/UPSTREAM_EXCEPTION_REGISTER.md`. This document requests one approval for the two remaining hooks only. It does not broaden the earlier approval.

## H8 — Pinkha-only semantic alignment for wide numbered markers

The previously proposed global `.left` → `.natural` edit in `TextBlockIconVIew.swift` is withdrawn. It would alter every numbered-list marker in Anytype.

The replacement leaves `TextBlockIconVIew.swift` byte-identical to upstream. A downstream adapter already exists at `Anytype/Sources/Pinkha/RTL/PinkhaTextBlockLeadingMarkerAdapter.swift`; it is inert until this hook is approved. It checks the already-gated `pinkhaWritingContext`, numbered content, and the existing wide-number threshold before changing only the rendered marker label to `.natural`.

- Host path: `Anytype/Sources/PresentationLayer/TextEditor/BlocksViews/Blocks/Text/Base/TextBlockContentView.swift`
- Upstream blob: `ae90a1f4a91e0204c4d11d2464113a729f9f1f12`
- Pre-H4 current blob: `aba80ccd797160822bbeee2e102a30c9b8c7786a`
- Current approved-H4 worktree blob used by this diff: `55c30c6a1805fbb75d846618f4b6037e512a1795`
- `TextBlockIconVIew.swift` remains unchanged at upstream/current blob `12334d6de523490f494dc030e5153807a34128fe`.

```diff
diff --git a/Anytype/Sources/PresentationLayer/TextEditor/BlocksViews/Blocks/Text/Base/TextBlockContentView.swift b/Anytype/Sources/PresentationLayer/TextEditor/BlocksViews/Blocks/Text/Base/TextBlockContentView.swift
--- a/Anytype/Sources/PresentationLayer/TextEditor/BlocksViews/Blocks/Text/Base/TextBlockContentView.swift
+++ b/Anytype/Sources/PresentationLayer/TextEditor/BlocksViews/Blocks/Text/Base/TextBlockContentView.swift
@@ -146,6 +146,11 @@ final class TextBlockContentView: UIView, BlockContentView, DynamicHeightView, F
         applyTextStorage(configuration.attributedString)

         textBlockLeadingView.update(blockId: configuration.blockId, style: TextBlockLeadingStyle(with: configuration))
+        PinkhaTextBlockLeadingMarkerAdapter.applyNumberAlignment(
+            context: configuration.pinkhaWritingContext,
+            content: configuration.content,
+            to: textBlockLeadingView
+        )

         let restrictions = BlockRestrictionsBuilder.build(textContentType: configuration.content.contentType)
         TextBlockTextViewStyler.applyStyle(textView: textView, configuration: configuration, restrictions: restrictions)
```

Why this hook is necessary: the numbered `UILabel` is private inside the host leading-view composition and is recreated on row reuse. Only the host configuration point knows that recreation has completed. The downstream adapter performs the traversal and gate; the host adds one call only.

Preserved behavior and risk:

- Ordinary Anytype configurations have `pinkhaWritingContext == nil`; the adapter explicitly retains/restores the host's original `.left` wide-number and `.center` narrow-number values, including after cell reuse or a context change.
- Pinkha narrow numbers retain `.center`; only the existing `number >= 20` wide-marker case uses `.natural`.
- Quote, bullet, checkbox, toggle, callout, typography, constraints and model data are untouched.
- Residual risk is visual spacing for 2+ digit markers under Dynamic Type/RTL; it requires focused simulator/device evidence.

Required tests: Pinkha RTL numbers 1/9/10/19/20/99 and nested lists; English Pinkha control; ordinary Anytype numbered-list snapshot in LTR and RTL; reuse/scroll/Dynamic Type; quote-bar and checkbox no-regression.

Rollback: remove this five-line call. The downstream adapter becomes inert; no stored data changes.

## H10 — retain Anytype full-screen Back; Pinkha RTL uses public edge Back only

The previously proposed global removal of Anytype's full-screen recognizer is withdrawn. The corrected design preserves the existing recognizer and its private transition target unchanged for every ordinary Anytype document and for LTR Pinkha UI.

For a currently visible Pinkha writing document **and** an active RTL interface only, the custom full-screen recognizer's existing delegate returns `false`, leaving UIKit's public `interactivePopGestureRecognizer` as the sole transition driver. Progress is normalized for right-to-left motion. The downstream bridge gates by exact registered Pinkha writing-document ID and synchronizes the navigation view's semantic direction from SwiftUI's effective `EnvironmentValues.layoutDirection`; it does not consult `Locale.current` or device preferred languages, so an app language override propagated through the environment is honored.

- Host path 1: `Anytype/Sources/PresentationLayer/Common/SwiftUI/NavigationView/FullScreenSwipeNavigationController.swift`
- Upstream/current blob: `0ee63a6623cab25b318ac97c9313eb19855cb1eb`
- Host path 2: `Anytype/Sources/PresentationLayer/Common/SwiftUI/NavigationView/AnytypeNavigationView.swift`
- Upstream/current blob: `a7755dbf09680be2116b7523f82cc733c4ee42cc`
- Downstream bridge: `Anytype/Sources/Pinkha/RTL/PinkhaNavigationGestureBridge.swift` (already present but inert without the two calls below).

```diff
diff --git a/Anytype/Sources/PresentationLayer/Common/SwiftUI/NavigationView/FullScreenSwipeNavigationController.swift b/Anytype/Sources/PresentationLayer/Common/SwiftUI/NavigationView/FullScreenSwipeNavigationController.swift
--- a/Anytype/Sources/PresentationLayer/Common/SwiftUI/NavigationView/FullScreenSwipeNavigationController.swift
+++ b/Anytype/Sources/PresentationLayer/Common/SwiftUI/NavigationView/FullScreenSwipeNavigationController.swift
@@ -37,7 +37,11 @@ final class FullScreenSwipeNavigationController: UINavigationController, UIGest
         case .began, .changed:
             let width = view.bounds.width
             guard width > 0 else { return }
-            onInteractivePopProgress?(recognizer.translation(in: view).x / width)
+            onInteractivePopProgress?(PinkhaNavigationGestureBridge.normalizedProgress(
+                controller: self,
+                translationX: recognizer.translation(in: view).x,
+                containerWidth: width
+            ))
         case .ended, .cancelled, .failed:
             // A live transition reports its own outcome through the transition coordinator.
             if transitionCoordinator == nil {
@@ -49,6 +53,9 @@ final class FullScreenSwipeNavigationController: UINavigationController, UIGest
     }

     func gestureRecognizerShouldBegin(_ gestureRecognizer: UIGestureRecognizer) -> Bool {
+        guard !PinkhaNavigationGestureBridge.requiresPublicEdgePop(controller: self) else {
+            return false
+        }
         guard viewControllers.count > 1 else { return false }

         guard let panGestureRecognizer = gestureRecognizer as? UIPanGestureRecognizer else { return false }
diff --git a/Anytype/Sources/PresentationLayer/Common/SwiftUI/NavigationView/AnytypeNavigationView.swift b/Anytype/Sources/PresentationLayer/Common/SwiftUI/NavigationView/AnytypeNavigationView.swift
--- a/Anytype/Sources/PresentationLayer/Common/SwiftUI/NavigationView/AnytypeNavigationView.swift
+++ b/Anytype/Sources/PresentationLayer/Common/SwiftUI/NavigationView/AnytypeNavigationView.swift
@@ -41,4 +41,9 @@ struct AnytypeNavigationViewRepresentable: UIViewControllerRepresentable {
     func updateUIViewController(_ controller: FullScreenSwipeNavigationController, context: Context) {
+        PinkhaNavigationGestureBridge.update(
+            controller: controller,
+            topNavigationItem: path.last,
+            layoutDirection: context.environment.layoutDirection
+        )
         let builder = context.coordinator.builder
         var freeViewControllers = context.coordinator.currentViewControllers
         var viewControllers = [UIHostingController<AnytypeNavigationViewBridge>]()
```

Why this is the minimum safe hook:

- `interactivePopGestureRecognizer` is public, but ownership of the competing full-screen recognizer and its delegate is inside this controller.
- The bridge cannot safely disable a private host recognizer through runtime discovery or swizzling.
- The representable is the exact boundary that exposes the active SwiftUI layout-direction override and top navigation item.

Preserved behavior and risk:

- Non-Pinkha and Pinkha-LTR paths return the original `translation.x / width` and original `translation.x > 0` full-screen begin rule.
- The original full-screen recognizer is neither removed nor globally disabled.
- Pinkha RTL blocks only the custom full-screen recognizer; UIKit's public edge recognizer drives start, cancellation and completion.
- The bridge resets the navigation view's semantic content attribute to `.unspecified` when the exact Pinkha-RTL gate is no longer active.
- Residual risk: UIKit right-edge behavior after a live language override, gesture competition with text selection/horizontal content, and transition cancellation require Xcode/simulator/device validation. If the public recognizer does not relocate safely to the right edge on a supported OS, the change must remain blocked rather than adding another private selector or a competing transition driver.

Required tests: active app-language override Hebrew/English without device-language change; Pinkha RTL right-edge leftward completion/cancel/progress; Pinkha LTR original full-screen swipe; ordinary Anytype LTR and RTL original full-screen behavior; root stack; active text selection/IME; horizontal table/collection; Inspector sheet; Stage Manager narrow width; VoiceOver Back action.

Rollback: remove the bridge call, progress wrapper and three-line begin guard. Existing Anytype full-screen and system edge recognizers return exactly to their prior code; no data migration exists.

## Recorded decision

**Approved and applied exactly as shown.** No other upstream file or hunk is included by this approval.
