import Foundation
import UIKit

@MainActor
protocol ViewControllerProviderProtocol {
    var window: UIWindow? { get }
    var rootViewController: UIViewController? { get }
    var topVisibleController: UIViewController? { get }
    func setSceneWindow(_ sceneWindow: UIWindow?)
}

@MainActor
final class ViewControllerProvider: ViewControllerProviderProtocol {
    
    private weak var sceneWindow: UIWindow?
    private weak var scopedRootViewController: UIViewController?
        
    // MARK: - ViewControllerProviderProtocol
    
    var window: UIWindow? {
        return sceneWindow
    }
    
    var rootViewController: UIViewController? {
        return scopedRootViewController ?? sceneWindow?.rootViewController
    }
    
    var topVisibleController: UIViewController? {
        return rootViewController?.topVisibleController
    }
    
    /// Used only by a separately retained external editor provider. The
    /// original app singleton and its scene window are never reconfigured.
    func setScopedRootViewController(_ viewController: UIViewController) {
        self.scopedRootViewController = viewController
    }

    func setSceneWindow(_ sceneWindow: UIWindow?) {
        self.sceneWindow = sceneWindow
    }
}
