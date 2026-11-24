# Original editor SDK on the dedicated Mac

The local route has its own UUID, source commit, source tree, checkout path and
actual Apple silicon host identity. Do not set GitHub Actions run identifiers for
a local execution. The existing GitHub Actions route remains available.

## Execution order

Use an isolated full checkout of `codex/otzaria-local-annotation-sdk-20261124` at the exact
published commit, with Python 3.12 or newer and Xcode 27.0 build 27A266a. Reserve
the Mac build slot with the other task owners before starting compilation.

1. Run `prepare_local_execution.py --root ROOT --evidence ROOT/build/SDK-Evidence
   --work ROOT/build/SDK-Work` with `python3 -B`. Source the resulting
   `ROOT/build/SDK-Evidence/local-execution.env`. This creates only provenance and
   disposable simulator preflight, and awards no acceptance.
2. Obtain the source-bound Native9/RPC/schema/semantic qualification from the
   native import execution owner. A failed or partial native run must not be
   used. Preserve the already authenticated generator and changed-Swift receipts;
   do not replay their passed work. The frozen qualification index has schema
   `otzaria.local-abi-input-qualifications/1`, the exact `sdk_source_sha`, and
   hashed `proofs` for `generation_qualification`,
   `changed_swift_qualification` and `final_native_rpc_union`. Its
   `historical_receipts` retain the four original files bound by
   `reused_abi_history.py`; normalized summaries must exactly match those bytes.
3. Run `build_local_import_abi.py` with the pinned proof index, its SHA-256, the
   qualified native Heart checkout, separate fresh `build/ABI-Work` and
   `build/ABI-Evidence` roots, and the exact Go 1.26.5 toolchain/cache paths.
   The script reuses the original observer, verifier and Invocation probe in
   `ImportRPC/` byte for byte. It runs one original three-target mobile bind,
   verifies each binary's Import exports, and compiles/links the original
   ProtobufMessages/Invocation consumer. It does not rerun generators or native
   tests. Only a successful terminal `ABI_INPUT.json` is an SDK input.
4. Prepare the committed Hanlin source using the existing `Tools/Hanlin` route,
   then use `prepare_reviewed_macro.py` for the exact reviewed macro trust entry.
   Keep its state for restoration after the framework execution.
5. Run `run_framework_acceptance.py --root ROOT --evidence
   ROOT/build/SDK-Evidence --work ROOT/build/SDK-Work --import-abi-receipt
   ROOT/build/ABI-Evidence/ABI_INPUT.json --import-abi-sha256 DIGEST` with
   `python3 -B`. The receipt is checked before and after compilation. The original
   source closure, 52 package pins, resource ownership, public/SPI surface and
   real English/Hebrew external consumer assertions remain required.
6. Restore the macro trust entry using the original restoration command. Run the
   existing shared runtime ownership verifier before adopting the distribution
   into the shared Maktabah candidate.

The ABI receipt explicitly does **not** claim full SDK acceptance or editor UI
acceptance. The complete SDK consumer result also does not claim editing,
saving, synchronization or relaunch. Those require the shared Maktabah StageB
runtime tests, including close and reopen in a new process.

## Evidence boundaries

`test_local_execution.py` and `test_import_abi_input.py` are synthetic metadata
admission controls. Their passes are not native import, iOS, SDK or editor
runtime evidence. The historical aggregate generator failure remains recorded;
only its individually qualified stable outputs are reused.

The shared AI pins adopt Hanlin `f8cf6ca543c5ceed05a60141644664c93e4565b4` and
Swift AI SDK `3f38f1302764635c9991d0d00fd7b12471a5373c`. These source pins are
bound by the profile and still require compilation within the complete SDK.


## Production local annotation source continuation

The reviewed product leaf is `cbe25cb467f989a1d40ed564d833616346a7d9b6`.
It adds exactly five framework Swift files and one original Services auth extension
to `bc36e8ecd803c0c4f9c856ed9a5384e074432952`. The original generated 733-file
inventory and its historical generator/adoption receipts remain unchanged.
The current source preflight independently verifies the six additions, current
product trees, all 20 framework compiler inputs and the unchanged original UI,
resources and native middleware. The Services auth extension is individually
bound by committed blob, SHA-256 and byte count in the source observation.

The new compiler contract requires 111 Debug declarations: all previous 86 plus
25 production local lifecycle declarations. The production subset is 89 and the
existing Debug qualification SPI remains 22. These are required counts, not
observations until the actual compiler graph passes. The local capture/session
cannot be constructed by an external caller.

`admit_retained_source_controls.py` is the historical 4fd/15-facade admission
route. The new local execution does not invoke it or use its old source proof to
admit the current product. Its historical constraints remain unchanged. Use the
current `source_observation` through the genuine local producer instead.

The local lifecycle supports canonical bodies in their original Host profile
with increasing local SQLite revisions. A transported/rebased rich body needs
a separate genuine canonical transport admission; it is rejected here without
rewriting historical provenance. The production normal-entry UI test, including
Save, Discard and cold relaunch in its own owned Simulator container, is separate
from both resource/ABI acceptance and the existing Debug qualification journey.
