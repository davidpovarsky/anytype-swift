# Original Any native entry failure and focus repair

Run [45031455896](https://github.com/davidpovarsky/anytype-swift/actions/runs/45031455896)
at `ef06a2c438104d1b47a715319bb78d31348edc04` passed native binary reuse,
original UIKit14 evidence reuse, compiled-product controls, the App/UI-runner
build, built app ownership, frozen-product identity and owned provider setup.
Its one native entry method failed before editor input. The seven dependent
journeys, real Files roundtrip and custom Type transition did not execute.

The native debug trace records actual paragraph creation, readback publication
and completion before the first text-view accessibility query times out.
The original XCResult spindump places all 266 samples of the app's busy main
thread inside `becomeFirstResponder`, reached from the diffable snapshot
completion while `updateUIViewController` is still on the stack. The sampled
thread consumed 4.925 CPU seconds in five seconds. This supports fixing the
responder handoff, not weakening the UI assertions or treating the failure as
a transient accessibility outage.

`original-failure-evidence.zip` contains 16 exact selected original files,
including the zstd-compressed original full spindump. It is explicitly a
selection from the original 1,430-file, 76,048,603-byte artifact 14760000069,
whose SHA-256 is
`cb5275f3497c6b8580462e43dc69dca52bce1a819757005b49fda2136b2cb974`.
The original full artifact and compiled-product TAR were downloaded and
verified; those binaries and the whole XCResult are not duplicated in this
selected evidence ZIP. `original-app-spindump.txt` is the exact app section of
the decompressed original attachment. `FAILURE_EVIDENCE.json` binds the original
and selected artifact digests, selected file inventory and observed scope.

The repaired controller defers and coalesces real focus readiness on the next
main-queue turn. Owner/version/source/visibility checks remain, canceled or
replaced intents cannot run, and native refusal still requires a new actual
attachment/key-window event. See the neighboring focus-handoff review for
the exact source changes and validation receipts.

The continuation executes six affected existing focus methods plus four new
handoff methods. Five unrelated marked-text and three renderer methods retain
their original source-bound proof after exact closure and embedded text-view
checks. The five compiled-product Python controls also retain their original
successful execution because all four control dependencies are byte-identical;
the actual new App and UI-runner products must still pass their original gate.
The native entry test and its assertions are unchanged. A successful new
component result does not substitute for the real native entry or its pending
dependent journeys.

No full Any, SDK, migration, T2, T5 or physical-device acceptance is asserted.
