# Bind displayed semantic links before editing

The original App13 UI proved the first native Sources action, actual linking, real text replacement and warm activation of the unique Changed Link. After terminating and relaunching, the same actual Link was present and hittable but did not open Sources. That original failure and all private artifacts are retained in the preceding App13 proof.

Exact App13 source shows one callback assignment in PinkhaSemanticAnchorSelectionCoordinator.bind, and only one call to bind: textBlockDidBeginEditing. A freshly opened text input therefore has no semantic URL callback until it has been edited. The warm path had already crossed that setup.

The fix installs the same coordinator callbacks after normal cell content configuration/replacement and again at willDisplay for lazily created content. Begin-editing remains a fallback through the same helper. Callback installation does not focus the view, select text, acquire a native lease or issue a native request. Weak model/input ownership, the editor view hierarchy and actual window are checked before dispatch. Existing parser, editing-versus-navigation rule, current selection ownership, native session, permissions, CAS, event/readback and source-session checks remain.

No original test assertion or preparation is changed. Root's TextBlockContentView focus fix and MiniApps source are outside this patch. Three source files grammar-parse with the actual semantic feature flags. UIKit typecheck and the original affected cold-source sequence remain pending the sole combined App producer.
