import Foundation
import SwiftUI

@main
struct AnytypeApp: App {
    
    @UIApplicationDelegateAdaptor(AppDelegate.self) var appDelegate
    
    var body: some Scene {
        WindowGroup {
            #if PINKHA_DUAL_ENGINE_RUNTIME
            PinkhaEngineSceneView {
                ApplicationCoordinatorView()
                    .setupGlobalEnv()
                    .setupAppSceneUrlHandler()
                    .setupTraitCollectionNotifier()
                    .foregroundStyle(Color.Text.primary)
            }
            #else
            ApplicationCoordinatorView()
                .setupGlobalEnv()
                .setupAppSceneUrlHandler()
                .setupTraitCollectionNotifier()
                .foregroundStyle(Color.Text.primary)
            #endif
        }
    }
}
