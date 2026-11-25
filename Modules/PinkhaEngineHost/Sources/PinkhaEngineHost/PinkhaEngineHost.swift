#if PINKHA_DUAL_ENGINE_RUNTIME
import PinkhaAnyNative

// Explicit public facade; no second native library and no alternate application.
public typealias PinkhaEmbeddedAnyApplication = PinkhaAnyNative.AnyNativeApplication
public typealias PinkhaEmbeddedAnyPresentation = PinkhaAnyNative.AnyNativePresentationSession
public typealias PinkhaEmbeddedAnyRootView = PinkhaAnyNative.AnyNativeRootView
#else
/// Legacy validation builds retain their original single Heart dependency graph.
public enum PinkhaEngineHostNotConfigured {}
#endif
