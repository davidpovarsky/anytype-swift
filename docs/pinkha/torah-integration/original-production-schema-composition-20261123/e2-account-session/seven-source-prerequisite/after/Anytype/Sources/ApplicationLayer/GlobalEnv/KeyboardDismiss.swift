import Foundation
import SwiftUI

struct KeyboardDismiss {
    
    private weak var window: UIWindow?
    private weak var scopedView: UIView?
    
    init(window: UIWindow?) {
        self.window = window
    }
    
    init(view: UIView?) {
        self.scopedView = view
    }

    @MainActor
    func callAsFunction() {
        if let scopedView {
            scopedView.endEditing(true)
        } else {
            window?.endEditing(true)
        }
    }
}

extension EnvironmentValues {
    @Entry var keyboardDismiss = KeyboardDismiss(window: nil)
}

extension View {
    func setKeyboardDismissEnv(window: UIWindow?) -> some View {
        environment(\.keyboardDismiss, KeyboardDismiss(window: window))
    }
}

extension View {
    func setKeyboardDismissEnv(view: UIView?) -> some View {
        environment(\.keyboardDismiss, KeyboardDismiss(view: view))
    }
}
