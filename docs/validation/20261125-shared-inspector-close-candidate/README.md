# Shared inspector Close integration candidate

Pins every active shared consumer to TorahInspectorKit `9058b489e9acc271b4f8ef69e2ed24648f93b4ed`. This retains the ready shared common SDK and shows the existing Close independently beside Search. The actual macOS SwiftUI compilation and original source hashes are committed in TorahInspectorKit `bcdf9c822b9030a3ad1bca42c9bf0642cae56aff`; iOS interaction remains pending.

The original Archive test is unchanged outside its sheet-close preparation: replacing the new real Close tap with the original swipe restores the complete NativeLaunchTests file from the actually built `6f1194f9b8c9540dea1187826dda6a256777dbbf` byte-for-byte. All sheet-absence, export/import, original IDs, native bodies, canonical sources and cold-reopen assertions remain. Both prior actual dismissal failures are retained and are not passes.

The separate E menu-lifetime handoff fix `e04180d3a609974c4c637411d4e93e5e160f08fc` is integrated as `37e801cdc2b0f6a10d45edf476acc002673e3770`. Actual read-only stack evidence identified EditorPageController.present ending editing during UIKit edit-menu presentation; the scoped guard preserves only the current attached editor input with an active public menu lifecycle. It must pass the original mounted/linked acceptance on the next built app.

The locked 56 dependency identities change only TorahInspectorKit. SDK30e and native70f0 remain unchanged. Historical validation manifests and package-lock originals are preserved. This checkpoint is source/compilation preparation, not new application acceptance.
