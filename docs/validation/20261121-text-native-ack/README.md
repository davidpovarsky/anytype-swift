# Heart native text acknowledgement — 2026-11-21

## Confirmed failure

The retained Heart adapter published an optimistic local `EventsBunch` before awaiting `service.setText`. If the native call failed, the model still contained the local edit. A later retry compared that model with the same text and returned success without another native call. The shared editor queue could therefore clear its dirty state even though persistence had never succeeded.

## Change

`BlockActionHandler.changeText` now owns a native write tail per block. It records an unacknowledged payload before publishing the optimistic event and clears that payload only after native success. A matching failed payload remains retryable. An identical callback that also matches the current optimistic model awaits the actual pending result.

Different accepted values wait for the previous native result; an older failure does not discard a newer value. A queued A → B → A edit remains a real reversal even while the model still shows A. Completed older work cannot remove a newer tail.

The unchanged-model no-op decision stays before the first suspension, preserving the original protection against unnecessary whole-value LWW writes over a peer edit. Text comparisons use exact UTF-8 plus native marks, rather than canonical Swift String equality. A new peer value that differs from a failed local payload remains a no-op.

This is the Heart acknowledgement adapter below the existing shared PinkhaKit edit queue. The common queue and render/composition policy remain unchanged. Any uses its own native versioned acknowledgement boundary; no Heart optimistic-state workaround is copied into that engine.

## Focused regression source

The seven methods in `PinkhaNativeTextAcknowledgementTests` cover:

1. An unchanged acknowledged model emits no native write.
2. Equal-text retries survive repeated native failures, and successful acknowledgement restores no-op suppression.
3. Canonically equivalent text with different UTF-8 persists the accepted bytes.
4. An identical in-flight callback receives the native failure.
5. A newer accepted value waits for an older failed native write.
6. A queued A → B → A reversal persists the final A.
7. A failed local payload does not turn an unchanged peer value into a new write.

The fixture models the optimistic document subscriber at the real service boundary. These are adapter component tests with a controlled failing native service, not a claim of real engine or UI persistence.

## Verification and execution scope

An independent source review checked main-actor ordering, tail ownership, failed retries and the queued-reversal case. Swift syntax parsing succeeded for the service and mock, then for the final seven-test source; the attached receipt records the exact scope and source hashes.

The seven new methods are to run once in the existing `hanlin-native` Debug acceptance build, before its fresh native fixture, with their own exact result/count receipt. This avoids another full Debug app build. No existing passing pure-queue or UIKit test is repeated merely for this adapter addition.

Apple type checking, actual seven-method execution, retained editor UI, quote UI and physical iPad acceptance remain separate requirements until their original results exist.

## Implemented efficient selection

The explicit hanlin-native-text-ack lane resolves to the existing SDK06 hanlin-native Debug journey and adds exactly these seven component methods before its fresh native fixture. It reuses that same built app and XCTest bundle, records a separate count/source receipt, and fails before fixture creation on any missing, skipped or failing component. The original hanlin-native lane excludes these added methods, allowing later UI work to retain already qualified component evidence without rerunning it. Five declaration/result/scope rejection controls and the two workflow syntax checks passed; actual Apple execution remains pending.
