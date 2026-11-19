# Focused inline renderer proof attempts

- v1 package runner: setup timed out before any tests; original receipt retained.
- v2 package runner (job_df1ac658185a): the identity-verified Swift process tree was stopped after179.63 seconds with no compiler/test output beyond pkg-config warnings. Source manifest was persisted and remained stable. This was not a product test failure.
- v3 direct component: compiler could not locate XCTest because the manual Windows invocation lacked the framework search path. No tests ran; corrected only the harness.
- v4 direct component: OSError28 while copying source, before compiler launch or initial manifest persistence. It makes no source-stability claim.
- v5 direct component:13 actual unchanged XCTest methods passed with zero failures. Fresh production codec and renderer were compiled, all cached Hanlin implementation objects were excluded, dependency and source hashes stayed stable, and the binary is recorded by SHA256.

The exact codec/AnyUI aliases also passed33 isolated component tests. These proofs do not claim a full SwiftPM package build, UIKit execution, or native engine execution. Apple CI remains the product assembly gate.

The source, scripts, logs and result receipts remain retained. Only released generated caches were reclaimed after their proof and binary hashes were captured. The current compiled dependency subset was preserved and verified before the released Engine cache was removed.
