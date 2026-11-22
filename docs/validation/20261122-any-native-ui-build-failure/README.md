# Native Any UI build failure — original run 44958245692

Run [44958245692](https://github.com/davidpovarsky/anytype-swift/actions/runs/44958245692), job `137011052214`, used source `9f83adf96d13036e4cf4dea7240c274a0454df0b`. It failed while compiling the UI test target, before the provider preflight and every selected native journey.

The original compiler reported two errors in `NativeLaunchTests.swift`, lines 1329 and 1333: the new archive journey's local `add` button shadowed `XCTestCase.add` inside its nested diagnostic capture function. The exact correction in `07999694c2ae6a116226b13598516433764029dd` qualifies the two receivers as `self.add(ax)` and `self.add(screenshot)`. Assertions, UI selectors, fixture data, timeouts and product code are unchanged. The corrected file passed syntax parsing only; replacement Apple compilation/execution is pending.

## Execution boundary

- The single native entry, seven dependent journeys and real Files archive roundtrip are all **NOT_RUN**. No product failure or new test pass is inferred from this compiler failure.
- The source-bound native binary reuse and original UIKit14 reuse gates passed. The original producer receipts remain unchanged and explicitly record zero tests executed by this consumer's reuse.
- The owned simulator boot request was accepted. The subsequent readiness/provider preparation phase was skipped because the build failed; no simulator-readiness or provider acceptance claim is made.
- Cleanup ran successfully and reported that no private provider fixture directory had been created.

The complete original artifact ZIP is preserved byte-for-byte, including the original build log and build xcresult. Artifact `14731470248` is 415,224 bytes; SHA-256 `cac61f8ec2515624d1faa78efadf4e65ac6a13467d91bd562b82895eae535c32`. Small original provenance/cleanup receipts are also copied without modification. The compiler excerpt and qualification JSON are derived summaries, clearly separated from the original files.

A replacement run must use the corrected source and the converged shared Kit pin. It should retain the exact original native/UIKit evidence with a newly reviewed source comparison and execute only the still-unproved entry, dependent journeys and archive scope.
