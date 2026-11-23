# Release 45129057825: bounded continuation design

Status: READ-ONLY PROPOSAL. No source changes, controls, product tests, API calls or dispatches were performed for this design.

## Evidence and scope

The reviewed controller is a69d0967c1dad4b9476b04af2b681474983e0b96. Its original App/Products remain d254a4a1ccd9288f585ff9374088cbaf965b36b4 from run 45095838065. The current run started zero new native or UI methods. Eleven actual kernel group observations and the initial 33 exact controller-source bindings remain valid in their original scopes. The nested group audit and outer worker quiescence failed; exact device cleanup passed. GitHub cancellation cause is UNKNOWN.

The first lookup was a required NEGATIVE_UNCLASSIFIED gate, not an absence proof. Its own declared freshness basis is NEW_OWNED_DEVICE_BEFORE_FIRST_APP_INSTALL. The original 30-second timeout must remain a failure. The original observation records empty stdout/stderr, but the original package excludes the .stdout/.stderr members; they must not be reconstructed.

## 1. Fresh construction for the explicit original-Products continuation

Use a new, versioned construction receipt only when the caller is the exact OriginalProductsContext, with coherent-heart-release profile and the admitted two-origin run. Keep the ordinary FrozenBuild/default lookup contract and its validator unchanged. Do not convert a timed-out lookup to negative, absent, or successful.

The existing full batch-simulator-baseline.json is already captured before lane creation. Preserve and bind its raw bytes, parse its complete devices dictionary with bounded strict shapes, require unique valid UUIDs, and verify that its UUID set equals the batch intent. This is the complete precreation inventory; no extra global simctl inventory is needed. Preserve the existing exact planned-name query and require no matching planned name before creating.

Before the existing create operation, write an exclusive creation intent binding:

- current controller SHA, original App SHA, run ID and attempt;
- batch intent bytes/hash and nonce;
- exact lane, planned name, runtime ID and device type;
- original complete precreation inventory hash;
- a fresh owned journal root and no install/selection attempt yet.

Execute the same one create with its existing 30-second cap, preserving exact argv, original output, exit status and command receipt. Reuse the existing qualified coherent_original_preflight.Commands ownership wrapper if its exact calling contract fits. Its observe callback runs before group-quiescence validation, so the new caller must persist a valid returned nonbaseline UUID and its original command/output hashes immediately, even if a later owned-group observation fails. No failed create or later failure may emit the passing construction receipt.

Bind the returned UUID to the command's exact name/type/runtime, both the complete baseline and planned ownership, and the existing verified initial Shutdown identity. Keep successful owned boot/bootstatus and the exact readiness receipt. A receipt is eligible only before any App/native selection in that owned journal. Claim CONSTRUCTION_VERIFIED_BEFORE_FIRST_NATIVE_SELECTION, with container_absence_proved=false and lookup=NOT_PERFORMED_CONSTRUCTION_CONTRACT.

At the actual first native selection boundary, append an exclusive FIRST_NATIVE_SELECTION_ATTEMPT journal record before delegating to the unchanged ordinary selection route. Bind exact source/product/descriptor, UUID, blueprint, method and selection-plan hash. This records an attempt, not a successful install. Never reset that journal or permit a second first selection. The real native preparation must still pass. The existing actual post-preparation get_app_container and native fixture read remain mandatory; observe_fixture still enforces the actual owned UUID plus distinct Space/container. The later UI and postflight remain unchanged.

Concrete hooks to review:

- wave15_batch.worker creation block, currently lines 727-745: call the origin-specific owned creation adapter only when origin is present; preserve the ordinary branch.
- OriginalProductsContext.confirm_empty_container override: emit/validate the explicit construction receipt; the inherited ordinary gate stays unchanged.
- OriginalProductsContext.run_selection override: journal the first actual native attempt, then delegate to the existing implementation without alternate publication or fake result.
- validate_worker_conclusion, currently wave15_batch.py lines 1083-1089: use the origin-specific construction validator only for the explicit original-Products context; default calls the unchanged validate_fresh_device_receipt.
- New bounded coherent_fresh_construction helper for receipt/journal validation. No App/product/fixture or original Products changes.

Journal completeness is scoped to this controller's owned process and exact nonce device. It is not proof against arbitrary external administrator actions, filesystem absence, or global machine isolation.

## 2. Propagate the existing coherent teardown profile

The exact missed call is wave15_batch.run_nested_worker_command line 936:

    verify_owned_group_stopped(path)

The function already requires profile == coherent-heart-release. Forward only that existing validated profile at this call:

    verify_owned_group_stopped(path, cleanup_profile=profile)

The helper itself, its 10-second total deadline, its qualified timely kernel ESRCH behavior, and other/default callers stay unchanged. Record both timeout_observations and quiescence_observation when the caller retains a cleanup exception. Preserve the original worker failure and exact returned command/cleanup receipt. Do not claim that this future wiring makes the original failed outer-worker receipt pass.

## 3. Cleanup from an already admitted exact source snapshot

The failing chain was nested_cleanup -> nested_cleanup_anchor -> validate_intent -> verify_control -> control_sources -> full-root git status, before any group audit. The early 33-source map cannot authorize newly loaded files automatically.

Keep control_sources/decode_batch and ordinary pre-admission checks intact. Before owned worker activity, preload the declared cleanup dependencies and obtain the exact loaded-source map through the existing successful Git/physical admission. Store a private in-memory cleanup snapshot and an evidence hash bound to controller SHA, run/attempt and the original intent/admission. The snapshot includes the actual cleanup helper closure, not merely the historical 33 entries.

Every later successful ordinary verify_control may add newly admitted loaded paths only after the unchanged exact Git/physical check at the same immutable controller SHA. Previously pinned path bytes must remain identical. Record the resulting snapshot map/hash. A path that was never admitted cannot join this snapshot during cleanup.

The cleanup-specific anchor then:

1. Requires the exact existing args/evidence/App roots, current environment origin and immutable original intent/admission bytes.
2. Re-enumerates the actual loaded repository Python modules; every loaded path must be in the already admitted snapshot.
3. Requires bounded regular contained files and exact physical bytes/hash for every admitted snapshot entry. Reject missing files, symlink/path substitution, changed bytes or any newly loaded unadmitted path.
4. Checks pure intent fields and exact ownership without a new git status, rev-parse or cat-file subprocess.
5. Calls the unchanged exact-owned-group audit with the existing coherent profile and deadlines.

If no valid snapshot exists, or any physical/closure/intent mismatch occurs, fail closed and preserve that separate cleanup failure. No broad fallback, source waiver, guessed group absence, or foreign-PID cleanup is permitted. Snapshot identity checks are cleanup-only; they do not replace ordinary admission, active product/source checks or final acceptance.

Implementation can add a small coherent_cleanup_snapshot helper, retain the existing control_sources body, and split pure intent field validation from its ordinary verify_control wrapper. nested_cleanup_anchor alone uses the snapshot route. The parent/worker each owns its own process-local admission; no historical receipt can issue a new live snapshot.

## Minimal new directly affected controls

Propose four new top-level controller methods, with only necessary subcases:

1. Construction receipt and first-selection journal: exact successful source/create/baseline/UUID/readiness binding, no lookup invocation, first native attempt delegation; reject baseline UUID, wrong runtime/type/nonce/run/source, changed original create output/status, and a prior install/selection journal.
2. New creation callback failure path: returned owned UUID is durable before a later wrapper/group failure; original error identity survives and no passing construction receipt exists. This tests the new adapter, not the old preflight suite.
3. Outer teardown caller: the actual coherent-only caller forwards the exact profile, preserves returned quiescence evidence and retains failure observation attributes/original error. No old kernel policy tests or actual 11 observations are replayed.
4. Cleanup snapshot adapter: successful exact physical/loaded/origin checks make zero subprocess calls; changed bytes, missing/unadmitted/escaping module or replayed intent fails closed. This tests the new cleanup route, not old Git batch-decoder cases.

Freeze source/manifest before executing these new methods. Preserve the unchanged old helper bodies by exact source/AST inverses and retain their original qualified receipts. No old native, HTTP, SDK, Page, UI, Release or controller suite reruns. The first future Apple continuation may execute only the still-unrun product scopes from the immutable original Products after root review/publication.
