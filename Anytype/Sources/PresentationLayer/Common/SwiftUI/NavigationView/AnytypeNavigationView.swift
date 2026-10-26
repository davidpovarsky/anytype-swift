import Foundation
import SwiftUI

struct AnytypeNavigationView: View {

    @Binding var path: [AnyHashable]
    @Binding var pathChanging: Bool

    let moduleSetup: (_ builder: AnytypeDestinationBuilderHolder) -> Void

    var body: some View {
        AnytypeNavigationViewRepresentable(path: $path, pathChanging: $pathChanging, moduleSetup: moduleSetup)
            .ignoresSafeArea()
    }
}

struct AnytypeNavigationViewRepresentable: UIViewControllerRepresentable {

    @Binding var path: [AnyHashable]
    @Binding var pathChanging: Bool
    let moduleSetup: (_ builder: AnytypeDestinationBuilderHolder) -> Void

    func makeUIViewController(context: Context) -> FullScreenSwipeNavigationController {
        let controller =  FullScreenSwipeNavigationController()
        controller.setNavigationBarHidden(true, animated: false)
        controller.delegate = context.coordinator

        let popProgress = context.environment.anytypeNavigationPopProgress
        context.coordinator.popProgress = popProgress
        controller.onInteractivePopProgress = { [weak popProgress] progress in
            popProgress?.update(progress)
        }
        controller.onInteractivePopAborted = { [weak popProgress] in
            popProgress?.settle(cancelled: true, duration: Constants.abortedSwipeDuration)
        }

        moduleSetup(context.coordinator.builder)
        return controller
    }
    
    func updateUIViewController(_ controller: FullScreenSwipeNavigationController, context: Context) {
        PinkhaNavigationGestureBridge.update(
            controller: controller,
            topNavigationItem: path.last,
            layoutDirection: context.environment.layoutDirection
        )
        let builder = context.coordinator.builder
        var freeViewControllers = context.coordinator.currentViewControllers
        var viewControllers = [UIHostingController<AnytypeNavigationViewBridge>]()
        
        path.enumerated().forEach { index, pathItem in
            if let index = freeViewControllers.firstIndex(where: { $0.rootView.data == pathItem }) {
                let vc = freeViewControllers.remove(at: index)
                viewControllers.append(vc)
            } else {
                let view = builder
                    .build(pathItem.base)
                    .anytypeNavigationItemData(pathItem)
                    .eraseToAnyView()
                let vc = UIHostingController(rootView: AnytypeNavigationViewBridge(content: view, data: pathItem))
                viewControllers.append(vc)
            }
        }
        if viewControllers.isEmpty {
            return
        }
        
        let currentViewControllers = context.coordinator.currentViewControllers
        if currentViewControllers != viewControllers {
            context.coordinator.currentViewControllers = viewControllers
            context.coordinator.numberOfTransactions += 1
            if currentViewControllers.last == viewControllers.last {
                controller.setViewControllers(viewControllers, animated: false)
            } else {
                controller.setViewControllers(viewControllers, animated: currentViewControllers.isNotEmpty)
            }
        }
    }
    
    func makeCoordinator() -> AnytypeNavigationCoordinator {
        return AnytypeNavigationCoordinator(path: _path, pathChanging: _pathChanging)
    }
}

private extension AnytypeNavigationViewRepresentable {
    enum Constants {
        static let abortedSwipeDuration: TimeInterval = 0.25
    }
}
