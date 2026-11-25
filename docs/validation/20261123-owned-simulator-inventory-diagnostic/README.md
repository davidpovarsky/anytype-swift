# Unexecuted owned-simulator diagnostic

The new diagnostic is source-frozen for independent review. Runtime, Mac, product and CI execution are NOT_RUN.

Entry points:
- Tools/SimulatorBootInventoryDiagnostic/run.py
- Tools/SimulatorBootInventoryDiagnostic/profile.json
- Tools/SimulatorBootInventoryDiagnostic/source-inputs.json
- .github/workflows/pinkha-owned-simulator-inventory-diagnostic.yml
- docs/validation/20261123-owned-simulator-inventory-diagnostic/INLINE-central-packet.json

See PROTOCOL.md for the exact diagnostic scope, original30second failure preservation, one conditional120second observation, ownership, sampled resource limits and causal limitations. source-review.json records static source checks only. qualified-body-inverses.json binds copied policy/function bytes to immutable56b4 Git source.

No existing file or default route is changed. Root owns integration and any actual run.
