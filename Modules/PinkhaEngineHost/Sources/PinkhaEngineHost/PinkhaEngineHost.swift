#if PINKHA_DUAL_ENGINE_RUNTIME
import PinkhaAnyNative
import PinkhaAnyUI
import PinkhaAnyHost

// Explicit public facade; no second native library and no alternate application.
public typealias PinkhaEmbeddedAnyApplication = PinkhaAnyNative.AnyNativeApplication
public typealias PinkhaEmbeddedAnyLaunchConfiguration = PinkhaAnyNative.AnyNativeLaunchConfiguration
public typealias PinkhaEmbeddedAnyPresentation = PinkhaAnyNative.AnyNativePresentationSession
public typealias PinkhaEmbeddedAnyRootView = PinkhaAnyNative.AnyNativeRootView
public typealias PinkhaEmbeddedAnyMiniAppsReturnRouter = PinkhaAnyUI.AnyMiniAppsReturnRouter
public typealias PinkhaEmbeddedHeartSourceReview = PinkhaAnyHost.AnyHeartNativeSourceCaptureReview
public typealias PinkhaEmbeddedHeartSourceReviewView = PinkhaAnyUI.AnyHeartNativeSourceReviewView
#else
/// Legacy validation builds retain their original single Heart dependency graph.
public enum PinkhaEngineHostNotConfigured {}
#endif
