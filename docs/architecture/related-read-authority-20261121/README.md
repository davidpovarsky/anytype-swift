# Related-document access loss across Heart and Any

## Shared source boundary

This app slice requires TorahInspectorKit commit `511454e49450cb2581ddf77f644146ff3e30dbef` on branch `codex/chatgpt-wave15-related-access-20261121`. All application/package consumers must resolve that same immutable revision before the new shared calls are compiled. The integration owner updates the existing package/project pins and generated resolution files together; this isolated source commit does not silently rewrite them.

The shared `TorahEditorSession` now retires its repository's related-document owner synchronously during `deactivateDocument()`. Explicit activation resumes with no cached related results. Both engines already use this session and repository. The Kit implementation clears its own caches, in-flight requests and mounted panel rows on a confirmed current access loss, while generation checks prevent late failures from affecting a newer owner. Ordinary provider/network failures keep the existing previous-rows warning behavior.

## Native adapter mappings

Heart maps only an actual `Object.Search.Response.Error` or `Object.Show.Response.Error` with code `badInput` (2), paired with one exact machine description:

| Exact description | Shared reason |
| --- | --- |
| `PINKHA_CURRENT_SPACE_READ_DENIED_V1` | `denied` |
| `PINKHA_CURRENT_SPACE_READ_INVALIDATED_V1` | `invalidated` |

The first pair is reserved for the native current-read authority fence confirming absent permission. The second represents a changed or unavailable native account/Space/principal/ACL snapshot. Other BAD_INPUT responses, generic transport failures, wrong typed codes, and similar-looking descriptions do not establish a denial. The existing service still propagates both native error types to this wrapper; only not-found/deleted object candidates retain their existing unavailable-candidate behavior. No protobuf enum, field, capability or native default is changed here. The native signed-ACL fence and its acceptance are owned separately.

Any maps its actual native/host errors: closed or changed session/workspace/account and native HTTP 401 invalidate; native HTTP 403 or typed association permission denial deny. The service is a native-read boundary, not a provider HTTP boundary. A cancelled request invalidates only if its actual `AnyApplicationSession.isActive` is false; cancellation while that owner remains live stays ordinary. Arbitrary error text never drives the classification.

The public adapter methods preserve every existing successful mapping and query. A current typed failure is handed to the common Kit repository. No database contents, canonical write format or acceptance threshold changes.

## Exact remaining validation scopes

The accompanying JSON is a selection profile, **not an execution receipt**. These scopes remain separate:

| Profile | Methods / argument cases | Purpose |
| --- | --- | --- |
| Kit related access | 15 / 17 | 10 new methods plus 5 affected existing cache/refresh methods |
| Any adapter | 3 / 4 | Typed native denial, live-versus-retired cancellation, negative text/transport cases |
| Heart adapter | 2 / 3 | Both exact native error types and code/description negative controls |
| Shared session | 1 / 1 | Actual deactivate/reactivate wiring around repository cache reads |
| Existing R05 | 1 / 1 | Resolver-to-canonical-query connection; its exact-one controller remains authoritative |

The macOS package steps may share a job, but different package roots are distinct SwiftPM build contexts. The session and R05 steps use the same Presentation package and can benefit from its valid incremental outputs; this must be observed rather than inferred merely from sharing a job. Heart's mapping suite belongs in the already necessary Debug host build.

**Current execution status: NOT_RUN for these new scopes.** Four bounded Windows attempts of the exact-source Kit component are preserved in the Kit commit. Core and test modules compiled after a test-only Swift 6 observer capture correction; SwiftPM discovery/link hit the final bound before any test case ran. No further Windows attempt is authorized or needed. Syntax parsing passed for all 14 changed Swift files across Kit and app. This is not full app/SwiftUI compilation, a passing test result or native permission acceptance.

## Evidence retention

Original Kit `158acb295f832e96907cdadc813a1c2a4bb6a03c` and original native/UIKit receipts remain historical proofs of their own source. Any UI run `44958245692` executes its already dispatched `9f83adf96d13036e4cf4dea7240c274a0454df0b` source, independently of this change. Do not relabel it as proof of this new pin.

Before reusing UIKit14 in a future source build, review the precise dependency and protected-file changes and preserve the original producer receipt. Related-document native journeys genuinely depend on this changed presentation/adapter boundary. Unrelated provider, text renderer, IME and focus passes do not become failed simply because the shared dependency revision advances; neither does a new revision automatically qualify their reuse.
