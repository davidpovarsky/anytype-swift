# Shared exact JSON guard qualification

TorahSourceJSONGuard moves the existing Any exact decimal-token and duplicate-key scanner into PinkhaKit. The complete private Scanner is byte-identical after the documented error-type rename. Any keeps its existing public API and error cases through a compatibility shim. Canonical codec behavior, malformed JSON errors, preserved unknown fields and lower-level source authority remain unchanged. No repository cutover or read-time migration is activated.

One isolated Linux Swift 6.4.3 component build compiled the complete actual PinkhaKit production target and all eight actual TorahInspectorCore files exported from 9058b489e9acc271b4f8ef69e2ed24648f93b4ed. The Any compatibility surface compiled against that shared target. Six new shared controls and two byte-exact original Any method bodies executed: **8 PASS, 0 FAIL, 0 SKIP**. The test wrapper changes only the target import and enclosing suite; original Any assertions are unchanged. Source manifests before and after are identical.

The original producer failed at collection because Swift Testing produced original-swift-testing.xml for the requested --xunit-output original.xml. Its original exit-zero log, XML, source manifests, producer failure and original controller remain retained. A separately pinned read-only collector admitted the existing original eight outcomes and exact hashes, without another build or test invocation. The future producer path is corrected, while the original failure is unchanged.

This is portable component qualification. It does not claim full Any migration acceptance, Apple UI compilation, native operation authority, a Heart immutable repository, or activation of a legacy cutover.
