import Foundation

/// Central feature gate and runtime controller for Pinkha features.
public enum PinkhaRuntime: Sendable {
    /// Controls whether Pinkha features and UI customizations are active.
    /// When `false`, Anytype runs in standard upstream mode.
    public static let enabled: Bool = true
}
