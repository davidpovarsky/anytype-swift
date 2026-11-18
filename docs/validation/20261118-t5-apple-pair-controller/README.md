# T5 Apple same-source pair controller handoff

Source-only milestone. Actual Apple pair execution is NOT_RUN; no product flag was enabled. The new Swift fixture passed a Swift5 syntax parse on Windows, not an Apple typecheck. SDK independently reviewed the real WalletCreate/Recover masks, AuthService migration mapping, same-account ledger, native block API and AccountStop/not-running boundary without finding a blocker.

The controller rejection suite passed14 functions and46 subcases with zero skips. Its original output and source hashes are retained here. These are acceptance-controller checks, not a simulation counted as native acceptance. YAML and the cache-log boundary inline Python parse successfully.

See Tools/PinkhaSimulatorGate/T5_APPLE_PAIR_CONTRACT.md for exact original r14 provenance, r15 build-only input requirements, same-source/flags binding, all four native phases and limitations. The existing dispatcher, Startup/UI workflows, r14 builder and root-owned production files are not changed by this commit.
