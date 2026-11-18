# Native document return: UI22 source handoff

This is a source and controller-control handoff, **not an Apple/UI PASS**. It adds the approved 22nd check to the existing native consent/read/create/lifetime lane. Actual selected-block return remains **NOT_RUN**.

## Behavior and evidence

The same H1 presentation and process first complete the existing native consent, cancelled creation, confirmed title-only Page creation and readback checks. Before the user action, the diagnostic captures the actual H1 navigation context and requires no native return receipt. XCTest presses the production `pinkha.hanlin.return-to-source` control, then requires the original full Space:Object editor identifier to exist and be hittable.

The driver asynchronously observes the handoff's terminal state and reads its actual receipt. It does not invoke `acknowledgeMounted`, construct a `HanlinHostNavigationResult`, post lifecycle events, or supply a UIKit callback. It requires a mounted/presented result, validates it against the actual queued destination, checks the complete original host context, and independently checks the original visible editor after dismissal. Both new read and create attempts through the closed H1 host must fail.

All 21 prior checks and H2–H4 remain. After H4 obtains fresh native consent and closes, H1 read/create denial is checked again while the original account, Space and document still exist, before the source-lock/Space-switch/logout probes. The final metadata must still equal the return receipt observed immediately after H1. No provider is configured or called.

The new check is `native_return_mounted_original_document`. The fixture explicitly requires empty selection references and no requested block. `navigationContext` anchors the original account/Space/context generation/scene/source revision, while `nativeReturn` contains the actual presented request ID and separately the original queued request ID, original session, observed returned context/target and acknowledgement flag. These context scene IDs are SDK host identities, not OS scene identifiers. The main `NATIVE_HOST_ACCEPTANCE.md` describes the exact schema and preparation/XCTest contract.

## Controller controls

The original 12 validator controls remain. Seven new controls reject missing/queued/unmounted or numerically truthy receipts, foreign request/session/context/target identities, changed original fixture scope, missing/extra schema fields, selected-block claims in this document fixture, and a missing/false closed-host denial check. The complete **19-control Python run passed** on Linux. Its raw output and input hashes are retained here. The tests use synthetic JSON and do not run the iOS application.

The result summary still requires actual XCTest separately and reports `originalDocumentOnly`, `selected_block_ui_verified=false`, and `full_sdk_acceptance=false`. A diagnostic label alone cannot establish acceptance.

## Integration boundary

Producer parent: `9f6c786263d6cc4a72b715a7212ccd8f964bf47a`. The two validator files are copied from root source `e7bb02742cb188cda1d5b44a8700b51fa2930421` (their blobs equal the previously frozen `101d4f4` versions) before the narrow UI22 edits. They are new paths on this producer branch but already exist on integration; review/apply the bounded delta against the recorded base, preserving root's caller and workflow changes.

The existing UI method, fixture preparation, opt-in environments, debug-only build and runtime contracts stay the same. No project or workflow file is changed here. Swift type checking, actual component execution and native UI execution remain Apple gates. The previous SDK run `44245129998` was cancelled while queued after shared quote-test compiler errors were confirmed; root's independent `d325987d1fe721938d8991b2e086cb0de6adcfd3` repair must be present for the next build.
