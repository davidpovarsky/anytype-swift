# Apple SDK build failure 44238998798

The actual run at f8cf3551eb66c725d9241917d778b52a647c71c2 failed during build-for-testing with exit 65. Its selected suites did not execute. The immutable caller identity, canonical Hanlin116 bootstrap, Xcode27 preflight and explicit rebuilt r14 runtime installation passed.

The compiler reported one error in HanlinSDKConsumerTests.swift:103:106: the canonical HanlinToolInvocationLimits default initializer can throw, but the sdkEnvelope helper omitted try. The helper already throws. This follow-up adds only try to that initializer, retaining the exact defaults, original arguments and all assertions. It does not alter production host authority or test selection.

The original outer ZIP was downloaded once and verified against the GitHub artifact SHA256. It and the complete compiler log stay on the Windows host. execution.raw.json preserves the original execution receipt bytes. compiler-diagnostics.txt is a focused excerpt of the original compiler output; archive, inner archive, full log and receipt hashes are in artifact-metadata.json.

The earlier Foundation notification ambiguity is absent from the compiler diagnostics in this run. This does not constitute a test PASS. The new try change still requires the next actual Apple compilation and component execution; no local Swift compile or native UI test is claimed. The separate native return receipt WIP is not included in this fix.
