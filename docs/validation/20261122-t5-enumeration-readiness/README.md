# T5 enumeration readiness and one-build R07 completion

## Original result

[Run 44960856322](https://github.com/davidpovarsky/anytype-swift/actions/runs/44960856322), source `87a543d81b51ca16d624d2f21f9ce50d70c0ab5b`, completed one corrected-r15 Release App build. Its host test enumeration then timed out at the existing 180-second limit. The output contains the invocation and `BUILD INTERRUPTED`; no host, native preparation, or UI method started. This is a controller/discovery failure, not evidence that the product tests failed.

The original artifact 14731226989 is 1,051,075 bytes and its SHA256 is `bf0f9c2392e5963dfcae533c54bf066a8c1aef6b5df517f7058a768fffb9bea6`. `ORIGINAL_FAILURE.json` binds the original run, App/runtime, all retained raw files, and the successful cache save. The original job log confirms a cache was actually saved at 00:09:26 UTC; the report does not infer that from a green workflow step.

Source inspection found a concrete missing prerequisite: preflight created the owned simulator, but the corrected T5 controller entered enumeration without explicitly booting it and waiting for readiness. The failed run did not record the simulator's state at enumeration, so the exact operating-system cause remains unproven. SDK and retained Release already perform boot/readiness; they do not have this omission.

## Correction

`owned_simulator_readiness.py` shares the established `simctl boot` followed by `simctl bootstatus -b` sequence between the T5 host and R07 adapters. It makes one scoped preboot query for the exact owned UUID, validates its name, device type, runtime and stable state, and records the same UUID's successful bootstatus command and raw log hash. The 120-second boot and 180-second bootstatus limits match the existing native controllers and the actual qualified Heart iOS host. Enumeration remains 180 seconds.

The separately inspected original Release run 44960843842 had successfully built both products and completed bootstatus, then stalled on a redundant postboot device-inventory query. That evidence led to removal of all postboot and shutdown inventory queries from this new helper. Shutdown requires the same verified ownership/readiness receipt and records only the bounded command's actual success; it does not claim a separate final-state observation. Unknown shutdown errors and timeouts fail. Actual xcresult destination identity remains mandatory.

The host's original compiled selection and actual 11-method/12-case validators are unchanged. Discovery cannot begin if readiness fails. Original command logs survive; cleanup cannot turn an incomplete stage into PASS.

## One App build, separate account data

The corrected T5 controller now includes `TorahT5NativeAccountRetryPendingTests/nativeStoppedAccountPendingNineOnly` in the same Release build used for host 11/12, native type/delete preparation, and the four UI invocations. It adds no App or native build.

`t5_account_retry_existing_build.py` validates the same source, corrected runtime 44943967103, App/XCTest/configuration hashes, and code inventory. It binds the successful unique simulator-create command to the source, run, nonce and returned UUID, requires that same destination's scoped preboot state to be Shutdown, and keeps the existing empty-App-container gate. It then uses the unchanged pending-only native execution and receipt validators. The existing complete UTF8/UTF16 credential scan gates publication of the native logs. The new receipt is separate under `account-retry-pending/` and requires one actual method, three query observations, eight successful service calls and one actual native error: exactly nine calls. The original 36 service calls remain evidence from the original run/runtime; this controller never claims 45 new candidate calls.

Runtime, fixture, account identity and original 36 source impact are documented separately in `../20261122-t5-r07-pending-nine/`. No ACL scenario or production source was changed here.

## Verification and remaining work

The first controller draft covered 17 distinct methods. Its initial attempt passed 10 and exposed seven new test expectations using `ValueError` even though the existing `pair.require` throws `RuntimeError`. Only those seven expectation sites were corrected; only those seven methods were run again, and all seven passed. The controller implementation did not change between these two attempts. Original failed and corrected logs are retained; the first attempt is not relabeled successful.

After the separate Release evidence prompted the scoped-query revision, 14 affected/new controls passed in 3.417 seconds with no failures or skips. Four unaffected prior controls were retained without reexecution: two runtime/scope guards and two corrected-build admission controls. Current coverage is 18 distinct controller methods. The final source hashes, method retention, and raw third-attempt log are recorded in `CONTROLLER_QUALIFICATION.json`.

Python syntax, workflow YAML and all workflow Bash blocks passed. A separate read-only peer review found no blocking identity, publication, cleanup or acceptance issue. These are controller checks, not Apple acceptance. The corrected host 11/12, R07 pending 9, type/delete preparation and UI 4 still require actual execution from the final integrated source and dependency pins. No CI was dispatched from this worktree.

Use the existing `t5-corrected-ui` dispatcher with `source_run_id=44943967103`. Do not dispatch the standalone pagination reusable workflow for pending 9 alongside it; that standalone route performs another full App build.
