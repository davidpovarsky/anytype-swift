# Canonical Hanlin compatibility pin ? 18 November 2026

## Actual build failure and minimum correction

Apple SDK run [44209702553](https://github.com/davidpovarsky/anytype-swift/actions/runs/44209702553)
failed at TEST BUILD before the four component suites ran. At the old published
pin `e195ef50fbf741d339f4bf515869a1ee6a038fc2`,
`Packages/HanlinPresentationSDK/Sources/HanlinRichUI/OpenUIBlock.swift` lines
55 and115 pass completion closures to the `contentWorld:` async WebKit overload.
The actual Xcode27 diagnostics are extra trailing closure and inability to infer
the closure parameter result.

The canonical producer already published a minimum two-commit correction:

1. [25729ca41871ca061ddff88ef0c6adb81ec35555](https://github.com/davidpovarsky/hanlin-ai/commit/25729ca41871ca061ddff88ef0c6adb81ec35555)
   is the direct child of the old pin. Both calls become `try await` inside
   MainActor Tasks. The navigation decision handler uses MainActor/Sendable.
2. [116cc6be0654a5d11bc56ba00e0310031107ee36](https://github.com/davidpovarsky/hanlin-ai/commit/116cc6be0654a5d11bc56ba00e0310031107ee36)
   is its direct child and changes only the bundled resource-directory getter
   to public, as required by the newly public initializer's default argument.

The current consumer pin is **116cc6be0654a5d11bc56ba00e0310031107ee36**.
Exact GitHub commit and parent identity and public repository visibility were
verified. No moving branch, newest producer HEAD, package fork, local source
patch or modification of any Hanlin producer checkout is used.

[Apple's WKWebView documentation](https://developer.apple.com/documentation/webkit/wkwebview)
lists the callback variant with the second `in:` label and the async variant
with `contentWorld:`. The selected producer correction uses that async API.

## Full dependency delta reviewed

Across all three consumed packages, exactly six files change:62 insertions and
24 deletions. The review included every changed line, not just the build error.

- OpenUIBlock additionally requires matching message identity, approved render
  target and catalog subset. Its async error handling stays on MainActor; update
  checks ready before starting and before displaying an error.
- OpenUIRendererConfiguration adds a default bundled directory. The next commit
  exposes only that already-bundled directory getter.
- NativeOpenUINode displays non-node literal children as text. OpenUICatalogs
  adds selected presentation mode and approved targets to its instructions.
- HanlinAgentSession changes only `executePresentationTool`: optional
  presentation reference/onStarted arguments, original-run completion and safe
  failure persistence. Existing interaction admission, unresolved-write,
  catalog/context and definition-dispatch guards remain. A final current-run
  check is added. Anytype's current host presentation does not call this method.
  Its canonical stream path is unchanged. The producer test adds assertions
  that the start event precedes effects and shares the actual resulting run.

All HanlinHostContracts, HanlinHostDispatcher, HanlinPlatform and all three
package manifests are byte-identical to the previous pin. The host's native
consent, context validation, cancellation, title-only write, journaling and
error boundaries are unchanged. Swift AI SDK remains
`e7bf34111e603ca977becd007dd4e5bb109af857`; iOS27 minimum is unchanged.

## Consumer changes and verification

`Tools/Hanlin/source.json`, the reusable SDK workflow's checkout, the CI
preparation example and current documentation use the same exact revision.
Root's separate UI workflow must likewise checkout this SHA before preparation;
it must not retain the earlier literal checkout while reading the new pin.

The actual unmodified `prepare_sdk.py --source <producer>` and `--check`
passed against the new pin, materializing a fresh complete snapshot from Git
archive. The old ignored snapshot was moved to the recorded sibling backup
path, and its full file hashes were verified unchanged. The active producer
was read only. No dependency snapshot or backup is staged or committed.

`canonical-pin-116cc6-verify.json` records the published chain, per-changed-file
before/after hashes, complete snapshot manifest hash/count, unchanged contract
paths and preserved old snapshot verification. The original source manifest and
review patch are historical records and are not rewritten.

The new pin has **not yet passed Apple compilation or native acceptance**.
The next focused component run must build the exact integrated consumer SHA
with this canonical pin, then produce real nonzero four-suite results. Native
consent/create and lifecycle acceptance remains a separate Debug lane.
