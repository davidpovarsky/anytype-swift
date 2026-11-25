# Shared MiniApps integration checkpoint

This integration merges the ready original Anytype MiniApps branch bf289002dfdf0d657253514f86a865efbeb12293, including the original five-method selector correction and local producer provenance checks. It preserves the original planner controls and historical failure evidence; no five-method native/UI pass is claimed.

Both engines can use the existing shared PinkhaHanlinUI module's PinkhaMiniAppsPresentation factories. The SDK MiniAppPicker remains the one picker; the existing Heart result sheet was moved into the same common module with caller-provided localized labels and unchanged result content/close-once behavior. Native source capture, account/space/revision fences, writes and ACK remain engine-adapter responsibilities. The shared pinkha.engine metadata key distinguishes Any requests from Heart; missing legacy keys continue to identify old Heart requests.

The Heart adapter retains original text/block/file operations and adds explicit engine ownership to capture/return routing. The authentication decorator invokes the unified host's capture drain before every native account-changing call; a failed close must propagate. Conditional compilation preserves the existing non-unified host.

Hanlin is pinned to 44bcebf687206a37893cb584cf72c6aafbc5ca48 and SwiftAI to 3f38f1302764635c9991d0d00fd7b12471a5373c. This combines the original catalog race/cancellation fixes with ready MiniApps62a work. The critical continuation implementation and both original regression tests remain byte-identical to97ffa. An earlier exact97ffa native source closure executed49 original tests successfully; added HanlinScriptExtensions notification behavior requires its own current qualification. Full app and companion acceptance remain pending.

The32 original build-configuration blocks still match their recorded hashes. Owner bundle IDs/team and declared App Groups pass the source declaration check only. The real Apple profile group grants are still PENDING_APPLE_GRANT. No simulator entitlement or source declaration is represented as distribution signing.

The actual49-test log remains SHA256adb975407aba2569fdf521f40afdd2f24c4e78a95f21bf81f8a6bca105bfe3f9. The first controller's summary parser did not recognize the original “in N suites” wording and stopped after the successful tests; the original result/log are retained for explicit followup qualification rather than rerunning unchanged tests.
