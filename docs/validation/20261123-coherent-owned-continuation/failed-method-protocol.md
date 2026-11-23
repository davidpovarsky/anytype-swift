# Failed cleanup method: bounded continuation

This continuation preserves attempt1 as FAIL: four methods executed; three passed and the fourth had five assertion errors. The errors came from expecting ValueError where the unchanged Origin guards correctly raise batch.require's RuntimeError. Original source, events, traceback streams and all63 copied originals remain at commit d322886d287a903170b3fd6d985e0646b3ee4c88 and the original diagnostics directory.

Source ad05ea15beb10b98feb74ab5ec705e18535fa8ba changes only two assertion expressions in the failed fourth method, accounting for exactly five exception expectations. Its complete file reverses byte-for-byte to source3a6. First three method bodies, all production code and the original four-method wrapper remain unchanged.

The distinct run-failed-cleanup-control.py selects only CoherentOwnedContinuationTests.test_cleanup_snapshot_checks_live_bytes_closure_and_intent_without_git. It binds the corrected source and explicit one-method name, checks the original capacity reserve, captures exact source/loaded inputs and named outcomes, and preserves any new failure. The passing first three methods are not selected. Incidental positive fourth-method subcases from attempt1 are not treated as a complete method pass.

Use only after independent review of failed-control-inputs.json and root authorization:

    python3 -B docs/validation/20261123-coherent-owned-continuation/run-failed-cleanup-control.py --evidence /mnt/development/projects/diagnostics/coherent-owned-continuation-controls-20261123/attempt2

This is controller and ownership evidence only. Simulator, native, App, UI, old suites and product methods execute zero times. The actual execution receipt establishes whether the corrected fourth method passes; the earlier failed receipt remains immutable.
