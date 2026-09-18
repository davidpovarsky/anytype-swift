import Foundation
import SwiftUI
import Assets

/// Helper to safely render vector SVG assets (which may have 512x512 intrinsic dimensions)
/// scaled to a specific layout frame without visual overflow.
struct PinkhaSizedAssetIcon: View {
    let asset: ImageAsset
    var size: CGFloat = 18

    var body: some View {
        Image(asset: asset)
            .renderingMode(.template)
            .resizable()
            .scaledToFit()
            .frame(width: size, height: size)
    }
}
