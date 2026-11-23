# Preserved test fixture initialization failure

Source 7188a566c0a09580cd6491c9d40b5aeaba650a11; FAIL_BUILD.
Actual methods executed: 0. Actual methods passed: 0.

The hot-cache compile took about eight seconds and exposed the next test-only
diagnostic after the earlier missing-try correction: HeartCaptureProbe.init's
WorkspaceOpen builder closure captured self.plan before self.lease had been
initialized. The repair binds the same immutable fixture plan to a local value
and uses that local value inside the closure. No assertion or product source
changes. Original source and compiler artifacts are retained here.

All 705 prior package files had been verified and archived before this attempt;
only the two throwing expressions in the client test differed from attempt1.
The exact dependency resolution was retained, and all three actual dependency
checkouts were verified clean at their pinned revisions again.
The next attempt preserves this attempt's exact package before its test-only
repair, keeps unchanged build inputs at the same paths, and executes only the
22 new controls that have not yet run. Apple App/native SDK call and mounted
editor acceptance remain NOT_RUN.
