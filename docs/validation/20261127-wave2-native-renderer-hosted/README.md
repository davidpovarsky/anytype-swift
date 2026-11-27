# Renderer3: one finite hosted lane, runtime closed

This packet adds `native-renderer-hosted-only` to a separate successor of the
published Core13 controller `dc001f2f09c64997515b77147fca4bacbac31397`.
It makes the three existing `AnyNativeTextRendererTests` methods selectable
through the same original F consumer and `AnytypeTests` target. The original
Properties9, block-creation2 and typography2 suites remain byte-bound to their
published sources. Available scope becomes four suites / 16 methods; a renderer
invocation selects only its exact three methods.

## Source and behavior

The renderer source was read from repository commit
`6e3e25194bca7b117989135f3cc4c6d2dd1cf878` at
`Modules/PinkhaAnyUI/Tests/PinkhaAnyUITests/AnyNativeTextRendererTests.swift`.
Its 3,269 bytes have SHA256
`695c89e5c8d5ad8e41f8ec525486836e42338bcc063d13f0945080c169fd7eaa`
and Git blob `c8372f370ff3cba7bc6f9563c4e522f919081662`.
That is observed source provenance, not a claim that this commit was built.

The exact methods check equal-text attribute replacement without character or
selection replacement; changed-text selection clamping; and preservation of
characters, selection and attributes while the renderer receives
`isComposing: true`. The original Hebrew and emoji text and UTF-16 range remain.
These are UIKit component assertions. They do not establish real keyboard or
IME operation, native persistence, permissions, mounted UI or device acceptance.

No App, test, project, package, receipt allowlist or complete compiler inventory
file changes. The renderer was already directly bridged and allowed. The old
closed preparation's 46-native/9-UI source inventory is not reused as current
product proof. The final integration had 57-native/10-Stage1 source files when
observed; the actual future producer must derive and prove its entire current
source set.

## Exact controller delta

`prepare_renderer_hosted.py` requires the complete SHA256 of three original
Core13 artifacts, plus both the renderer source SHA256 and Git object identity.
It produces a fresh separate directory; it refuses an existing output.

- The profile gains one fixed three-method suite and a finite XCTest signature
  map. Typography retains its exact two throwing signatures. Renderer uses its
  exact three non-throwing signatures. Whole-source hashes remain mandatory.
- The F host gains one plan and one result slot. Every original function and
  class is unchanged, including process lifecycle and error handling.
- The closed JSON adds the renderer source/dependency and changes the available
  total from 13 to 16. It does not bind a future App or producer.

All three full-source inverses are retained. The original compiler witness,
suite selector, enumeration validator, result validator and `run_hosted`
function are unchanged. The actual runtime path still requires the admitted
common producer's own native compiler proof before and after the same 300-second
hosted stage. No independently supplied compiler proof substitutes for it.

`require_runtime_ready` remains unconditionally closed, even when a caller flips
a mutable ready flag. The three future source/producer/admission pins remain
null. Wave3 must prepare a separately reviewed exact successor after a matching
shared build succeeds. This packet neither starts a build nor opens that gate.

## Verification performed

Four affected portable controls passed in 0.08221485 seconds. They read the
actual pinned Renderer3 and Typography2 source declarations, reject source
drift, exercise the original enumeration and result validators with explicitly
synthetic three-method records, restore all three original artifacts, and check
the new lane remains closed before external input, process or product activity.
The synthetic compiler fields in validator controls are test inputs only; no
actual compiler proof was validated and no XCTest method was executed.

The original six Core13 portable controls are reused from receipt SHA256
`babc802cb108d77eb3be8411c7a51372eeb7708d9c04320c6b766d76a2194940`.
They were not rerun. No Swift compiler, Apple host, native operation, simulator,
device setting or physical device was invoked for this packet.

## Reproduction and integration

Materialize into a new directory using the exact Core13 inputs:

```sh
python3 prepare_renderer_hosted.py \
  --core-input /path/to/published/native-core-hosted \
  --renderer-source /path/to/repository/Modules/PinkhaAnyUI/Tests/PinkhaAnyUITests/AnyNativeTextRendererTests.swift \
  --output /path/to/new/renderer3-closed
```

The output is not a standalone product closure. The other unchanged F/common
helpers must be supplied and hash-bound in the actual future 15-file consumer
closure. G02 has its separate 17-file closure and is unchanged here. Other
source-bound Torah or RTL compatibility updates are separate successors; this
packet does not silently substitute their source hashes.

Wave3 alone owns the final branch, common build, admitted execution and delivery.
The remaining Renderer3 Apple execution and mounted editor acceptance are open.
