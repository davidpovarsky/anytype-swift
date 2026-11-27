# Inspector reference resolution error publication

A source-open resolution could finish with an error after the user typed a new
query. The success path already checked the request ID, original query and
original scope. The error path checked only the request ID, so it could replace
the newer search message without another source-open request.

The shared presenter now applies the same query/scope check before reporting a
provider error. Both engines use this presenter. Native calls, provider APIs,
writes, navigation, successful resolution and existing source bodies are
unchanged. The complete original presenter is restored by removing the two
added comparisons from the recorded current source.

## Verification completed

- Independent interfaces source review found no product blocker.
- Its test reliability finding was addressed with a two-second, cancellable
  provider-entry rendezvous and release on setup failure. No fixed delay is used
  to decide when to change the query.
- Swift 6 frontend parse of the two exact changed/new Swift files passed.
  This is grammar checking only, not typechecking or test execution.
- The original source-retention verifier passed on the staged source tree:
  121 mappings, zero unreviewed original-file changes and zero inventory errors.
  120 map entries are structurally unchanged. Only the existing shared presenter
  entry updates its shared Git blob and appends its review note.
- A preparatory cross-filesystem backup relocation failed before grammar or
  tests ran. That record remains in preparation-attempt1.json. The correction
  copied the two owned backups, verified their bytes and retained them privately.

## Apple work still required

TorahSearchResolutionPublicationTests contains one new method with two
arguments: an unchanged query still reports the actual error, and a replacement
query preserves its current message. The test uses the real shared presenter and
session with a suspended controlled reference provider and a single request.
Both cases are NOT_RUN. Include
AnyTypeTests/Pinkha/TorahSearchResolutionPublicationTests.swift in the shared
AnytypeTests compiler-input evidence and execute the test from that product.

No App build, native call, product test, visual or physical-device acceptance is
claimed by this source tranche. Earlier T3 failures and scoped passes are intact.
The final integrator must preserve newer map additions, including the separate
Properties entries, while applying this one existing-entry change.
