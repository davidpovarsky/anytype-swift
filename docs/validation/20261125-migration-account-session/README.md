# Original-app source session ownership — 2026-11-25

Product source: 62d3682addd71bb664d64b96fde91e0d6379584e.

The original app adapter is Anytype/Sources/Pinkha/Migration/PinkhaHeartSourceCaptureController.swift, compiled only with PINKHA_DUAL_ENGINE_RUNTIME. It obtains the current account mnemonic through the injected original SeedService on the main actor and calls original Invocation.walletCreateSession. Both request and response masks remove authentication material from Invocation logging. The returned app token is not persisted. The actual returned session token is owned in memory by the shared controller, checked for the exact requested account, full scope and no app association, and closed through original WalletCloseSession. It never closes the ordinary app's account or a session supplied by another component.

AnyHeartNativeSourceAccountController owns session minting and the source coordinator. The mint operation must be observed even after cancellation because Invocation checks cancellation after native completion. Capture and validation are also drained before closing the owned token. Cancel/release/account change/engine change await this drain. A real close failure throws sessionCloseFailed, retains the owned token and prevents another capture/engine transfer until a later explicit close retry succeeds. Public methods do not persist or expose the token. The native Service wrappers are injected through ProtobufMessages; no extra Go runtime or Lib import is added to PinkhaAnyHost.

Public application boundary:

- throwing initializer privateDirectory / obtainSeed (MainActor Sendable).
- capture(accountID:spaceID:) async throws -> AnyHeartNativeSourceCaptureReview.
- revalidate(source:) async throws.
- invalidate(reason:) async throws; cancel and release are also async throws.

The host must await successful invalidation before replacing its account or engine. It must not interpret source review as destination admission. The existing complete-census/source-bound checks and explicit semantic blockers remain unchanged.

## Actual qualification

Eight focused methods passed with zero failures and zero skips on the exact unchanged product source. Original source fixture bytes for the 144-object native capture were used for successful reviews. The session/Service callbacks were injected unit controls, not a live native app session. Total controller time was 47.537 seconds including Swift compilation; methods took 5.067 seconds.

The methods cover:

1. A complete original source review, explicit semantic blockers and revalidation, followed by one owned-session close.
2. Account change while minting: await the late token, close it, dispatch no capture and refuse another capture before drain.
3. Caller cancellation while minting: do not lose the late successful token to Invocation's post-response cancellation check.
4. Caller cancellation while the native capture callback finishes late: close only after that callback returns.
5. Wrong account, limited scope, app association and empty token: refuse source capture, close every nonempty owned token.
6. Engine change while native validation finishes late: await validation, release metadata and close before transfer completes.
7. Failed native close: keep the token and block new capture; an explicit retry closes that same token without another mint.
8. Invalid native descriptor: close the owned session and retain the original captured files.

Original Swift log SHA-256: 69f46e1652bbabc0a73cdcf8a6b77e348b74ad939500b1e4aa28b09291808324.

The app file passes Swift grammar parsing with the shipping flag enabled. Apple module typechecking, linkage to the generated Service header, actual mounted app capture and the main host's account/engine transition are pending D's combined runtime integration. This result does not establish complete semantic mapping, native destination execution, fresh-process offline destination reopen, complete real-space migration or Task C completion.
