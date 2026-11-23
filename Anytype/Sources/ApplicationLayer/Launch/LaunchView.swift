import Foundation
import SwiftUI

struct LaunchView: View {
    
    @State private var showPrivateDebugMenu = false
    @State private var showPublicDebugMenu = false
    private let allowsDebugMenus: Bool

    init(allowsDebugMenus: Bool = true) {
        self.allowsDebugMenus = allowsDebugMenus
    }

    var body: some View {
        ZStack {
            Color.Background.primary
                .onTapGesture(count: 10) {
                    guard allowsDebugMenus else { return }
                    showPrivateDebugMenu.toggle()
                }
                .ignoresSafeArea()
            
            LaunchCircle()
                .onTapGesture(count: 5) {
                    guard allowsDebugMenus else { return }
                    showPublicDebugMenu.toggle()
                }
                .sheet(isPresented: allowsDebugMenus ? $showPrivateDebugMenu : .constant(false)) {
                    if allowsDebugMenus {
                        DebugMenuView()
                    }
                }
                .sheet(isPresented: allowsDebugMenus ? $showPublicDebugMenu : .constant(false)) {
                    if allowsDebugMenus {
                        PublicDebugMenuView()
                    }
                }
                .zStackPosition(.center)
                .ignoresSafeArea()
            
            HStack(spacing: 8) {
                IconView(asset: .X18.lockWithTick)
                // Do not localize
                Text("encrypted, local, yours forever")
                    .anytypeStyle(.previewTitle2Medium)
                    .foregroundStyle(Color.Text.secondary)
            }
            .zStackPosition(.bottom)
            .padding(.bottom, 26)
        }
    }
}

#Preview {
    LaunchView()
}
