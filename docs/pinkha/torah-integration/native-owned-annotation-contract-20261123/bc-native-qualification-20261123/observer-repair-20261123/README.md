# Native bundled schema observer repair

## Evidence and scope

The immutable previous control is 9934ccf396139fd8ff4367dd416b0460f23d49df, which executed run 45225259295. The original native build passed. Its first text leaf failed before importer execution during bundled prerequisite observation; the other eight leaves did not run. The retained failure did not identify the first key or distinguish RootOnlyIncomplete from PopulatedConflict. This packet does not infer a missing key-specific result.

The actual bundled-definition helper incorrectly required uniqueKey in persisted Details. Original Heart marks uniqueKey as a derived field. Native State.SetDetails and State.SetDetail route it to LocalDetails; the native details injector also treats it as derived. The original raw observer compares persisted Details and already authenticates signed native kind/internal-key headers. Requiring a derived value in persisted Details therefore rejects an otherwise valid populated object.

Only that one persisted-field requirement is removed. The original signed header/key/kind checks, raw replay, archive/deletion checks, all other required fields, RootOnlyIncomplete and PopulatedConflict refusal, body/mapping/readback assertions, operation drain and owner cleanup remain intact. No installer retry or readiness shortcut is added.

## Explicit source composition

REPAIR_INPUTS.json binds three afterimages: the minimal observer correction, the original Native9 fixture with bounded key/disposition failure diagnostics, and a new focused semantic test. The sealed candidate and fixture files remain unmodified. The runner composes their exact historical preimages first, then checks and applies these three explicit rows.

The final fixture is gofmt-normalized. Its SHA256 is 3f54464ab2dc860e79f41f55d6b4a0813409828a4e3d8c5d5a596e4666ffc422; the earlier preparation hash 075aebe4 represented the same code before three alignment spaces were added by gofmt. Current source preparation, diffs and manifest agree.

The exact workflow template and its attempt-one-only guard remain unchanged. The active workflow differs only by the explicit execution-manifest digest. The runner declares 88 required compiler inputs across application, core and objectcreator; the composed native afterimage map contains 86 paths.

## Validation and claims

The new native selector is TestOwnedAnnotationBundledPersistedDefinitionContract. It reads five original bundled sources through their real native State implementation, proves that uniqueKey is local rather than persisted, applies the original installer's explicit sourceObject transform, accepts the correct persistent shape, rejects the former derived-field predicate, rejects corruption of each required field and the wrong object type, and rejects an unsupported bundled key. It is a separate prerequisite and does not replace any of the original nine cases.

The runner requires one parent and all six expected semantic leaves to run and pass exactly once, with a passing package result and no extra tests. Eleven synthetic collector controls are retained in COLLECTOR_CONTROL_RESULTS.json. These are local parser controls, not native execution.

Native semantic execution and the repaired Native9 run are not yet performed at source preparation. A fresh source activation is required because the workflow intentionally accepts attempt 1 only. Any native result must retain the exact source, run, original declared dependency closure, post-execution stability, and cleanup evidence. No result here qualifies generated RPC, Swift Invocation, Host ACK authority, cold reopen, or production import.
