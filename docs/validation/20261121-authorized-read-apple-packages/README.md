# Authorized operation read: original Apple package proof

The [original run 44952901524](https://github.com/davidpovarsky/anytype-swift/actions/runs/44952901524) passed exactly **14 new named methods**, with zero failed, skipped, duplicate or extra methods. Its source is `a7db1f90241b7d4075eb768d3d38446887991ee3`; this evidence is not relabeled to the later report or iOS candidate commit.

| Package | Named methods passed | What the focused methods cover |
|---|---:|---|
| PinkhaKit | 5 | Complete conflict closure, exact bytes/provenance, local absence, exact UTF-8 authority identity and response bounds |
| PinkhaAnyEngine | 6 | Native envelope decoding, unreachable block semantics, tampering/refused partial results, scope/bounds and exact opt-in capabilities |
| PinkhaAnyIntegration | 3 | Mapping to the shared contract, session generation, cancellation/invalidation and no-payload error propagation |

The toolchain was Apple Swift 6.4 (`swiftlang-6.4.0.34.1`, target `arm64-apple-macosx27.0.0`) and Xcode 27.0 build 27A266a. The job ran from 21:44:57 to 21:49:45 UTC on 2026-11-21. This is a macOS package proof; it does not execute the Any C runtime, the real application-owner Host wrapper, iOS, a simulator, or two clients.

## Original evidence and independent qualification

Artifact `14727045427` has ZIP SHA-256 `3680f4216a2f483d57319c9e772ebb1d760bc1b2bc4ec4028d060a1b83199e46`. Its original receipt SHA-256 is `4336c4e1fb7a81de71e980ee2a2cb90a58c7acf9a30847c7bd54e473409bca80`.

The downloaded archive digest matched GitHub's artifact digest. The original receipt, three XML records and filtered original XCTest terminal lines are retained here. Independent read-only qualification required exact method sets from both XML and terminal output, checked every log/XML/dependency-lock digest, and compared all three package Git trees to the original source commit. No test was reexecuted for this verification. Full original logs and before/after lock files remain in the run artifact.

All three resolve-only preflights passed before any test compilation, preserving the declared pins: TorahInspectorKit `158acb295f832e96907cdadc813a1c2a4bb6a03c`, swift-crypto `e8d6eba1fef23ae5b359c46b03f7d94be2f41fed`, and swift-asn1 `917b472dbe53ba699cbb0495f9a95a084bc6364d`. Six receipt-controller rejection checks also passed; they are controller checks, separate from the 14 product methods.

## Earlier failure retained

[Run 44951720201](https://github.com/davidpovarsky/anytype-swift/actions/runs/44951720201) passed the same resolve/source preflight but executed **zero selected methods**: the first fixture did not compile because `TorahAssociationTarget` is an existing enum with `.object` and `.block` cases, not a struct with a memberwise initializer. The same constructor mistake in the new Any adapter was corrected at the same time. Assertions, method selection, source gates and byte/authority bounds were unchanged. The original failed receipt and log identity are retained so the first attempt is not reported as a test pass.

## What remains open

The real native read component/HTTP proof remains separately attributed to its frozen v10 tree. The isolated candidate iOS test still must prove the linked C library, managed account and Space, real application-owner lease, exact append/read bytes, block deletion, original-store cold reopen and stale-owner rejection. The retained v9 default and full T2 activation remain unchanged. This package success does not close the remaining two-client, source-page/watermark, backup/import, causal-ordering or full T2 acceptance rows.
