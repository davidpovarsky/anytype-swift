# Dedicated generated-byte lifecycle race lane: local review candidate

Status: **LOCAL SOURCE CANDIDATE; NOT PUBLISHED, NOT COMPILED, NOT DISPATCHED**. The 39 Python rejection controls have run successfully. Those controls do not establish any native race outcome.

This proposal adds a distinctly named `t2-rpc-lifecycle-races` dispatcher route and reusable workflow. It preserves the two existing routes:

| Existing route | Existing purpose | Proposal |
|---|---|---|
| `t2-account-lifecycle` | Original typed/native account and private-history preservation across four processes. | Unchanged. |
| `t2-account-rpc` | Generated protobuf byte entry through the original four-process account lifecycle, including the legacy reopen and eight exports. | Unchanged. |
| `t2-rpc-lifecycle-races` | The unchanged generated-byte baseline followed by three deterministic races in one additional owned native process. | Separate new workflow and controller. |

The route comparison was read from exact integration commit `5fa5fb572f90a9e7b6c97b99591d164ce280f0b8`. The dispatcher proposal is a patch against its exact SHA-256 `f2e854bf8159c674686bdcd196efb79aeefd9f1eee95d3cf1984779206a81c72`; the parent must reconcile that additive patch with its current owned integration source. No existing route is repurposed, and this proposal performs no remote mutation or dispatch.

## Source and binary separation

The product inputs stay pinned to the already qualified `16b7493fa05bdc3abbae190c6e6c364c81874eea` registry, RPC and account inventories and controllers. Heart remains `d98420b1113536afd08cde6de9a5816f6d27ffff`; the approved legacy composition/builder remains `947fbde24d5657d0e1229f45bb3993648884a8a1`. The actual CI control commit will be the new publication commit, recorded independently as `app_sha`. A new CI commit is not relabeled as the earlier product commit.

The separately reviewed test-composition manifest is `b021c51a0541a4603036a579bb339318d15e6fbb0f100cd913db480aa3259799`. Its five instrumented product overlays and two added Go sources are compiled only into an additional test binary. The original product files on disk are not overwritten. The helper package requires an empty directory solely for Go package discovery. The original account fixtures, generated bindings and both original binaries remain byte-for-byte bound to the baseline receipts.

`account_rpc_lifecycle_lane.json` pins eight existing controller/inventory inputs and all twelve files in the reviewed fixture package. The new controller pins that manifest by its exact hash, and checks every input again after compilation and after execution. The local `prepare_candidate.py` remains a source-authoring helper for the separate copied baseline workspace; the runtime lane does not execute it or regenerate approved test source.

## Required execution

1. Generate bindings from the exact clean control source with the existing `run_native_rpc.py generate`, recording the same GitHub run and attempt.
2. Call the original `run_account_rpc.execute` without native-client additions or diagnostic replacement. Require its original two binaries, four passing native invocations, same-account reopen/legacy/recovery evidence and eight exports. Its original `receipt.json`, native logs, phase reports and build receipts remain intact.
3. Preserve the original compile overlay and all of its replacement-source hashes. Add the seven separately reviewed test entries with the existing fail-closed materializer. Compile a third binary using the same pinned Go 1.26.5 Alpine/musl image, tags, generated source, linker identities, native dependency closure and Go workspace. Link the candidate manifest hash into `t2LifecycleFixtureSHA`.
4. Start one additional owned native process against one newly created empty account root. Invoke exactly `TestT2GeneratedByteLifecycleRaces`, once, with a five-minute native test deadline and bounded process supervision. The fixture creates its own disposable account and three Spaces. It exercises first append versus block deletion, durable append versus block deletion, and durable append versus actual AccountStop. All original callbacks and storage calls remain once-only.
5. Require the exact named native PASS and the original three-case JSON together. Check source, nonce, PID, request hashes, exact stage order/counts, original object identities, no gate timeout, absence of the rejected first private root, actual durable history/head shape, retention of both original signed hashes in the Stop case, successful actual deletion/Stop, and subsequent denial codes. The source-bound Go fixture additionally checks original response contents and live in-memory pointer identity; the Python receipt validator does not invent those observations.
6. Publish only the new ownership/result documents, original native log and original lifecycle JSON after scanning all four for both generated wallet secrets. Native output is withheld without its private secret inventory. A successful lane requires all four original files and the supervisor's successful return after process exit. Remove only the new controller-owned account directory; retain a separate receipt that distinguishes directory removal from observed process exit. Recheck both original binaries, native source snapshots, module files, original fixture bytes, compile overlays, generation/build receipts and clean control sources.

If all gates pass, the exact native counts are **three compiled binaries, five native invocations/processes overall, and three race cases within the one additional process**. The original baseline and the additional race counts are recorded separately. There is no claim that the three race cases use three separate processes.

## Original artifact acceptance

The artifact contains the original account-wire evidence plus `lifecycle-build.json`, `lifecycle-receipt.json`, `lifecycle-sequence/{ownership.json,result.json,lifecycle.json,native.log}`, `lifecycle-evidence-copy.json` and `lifecycle-cleanup.json`. The native result document uses a narrow status for original log/report validation; only the outer lane receipt can record final success after copy, cleanup and source verification.

The original process supervisor returns its child PID only after a successful exit. As soon as a new launch is requested, the private receipt records `launch_requested=true` and an unknown (`null`) native process count; nonzero exits, timeouts and cancellation retain that unknown count rather than falsely reporting that no process ran. A successful return records the actual PID and exact count of one. The cleanup receipt reports only removal of the controller-owned directory; `process_exit_observed` is true only after that successful supervisor return and null otherwise. An exception in the original supervisor does not become a new claim that its child exited.

Qualification after a real run must start from the original GitHub artifact and its published archive hash, validate archive member integrity, bind the exact control/product/candidate inventories and generated outputs, and replay the original pure report/log validators. GitHub job success alone does not close the acceptance row. Runtime ELF bytes are intentionally not retained in the evidence ZIP; runtime identity is limited to the original build and phase receipts, not a later rebuilt binary. No account database, wallet, mnemonic, private key or unscanned native output enters the artifact.

## Local verification and proposed commands

The local controller suite is:

```sh
python3 -B -m unittest -v test_account_rpc_lifecycle test_account_rpc test_account_lifecycle
```

It contains sixteen new lifecycle controls and the existing six account-wire and seventeen account-lifecycle controls. They reject missing/duplicate/failed/skipped native evidence, wrong source/process/nonce, missing cases, wrong order or target, changed prior history, invalid heads, overclaimed scope, partial or secret-containing evidence, and changed source inputs. Cancellation cleanup and refusal to accept an unretained native claim are exercised with isolated controller fixtures, not reported as native account execution. YAML structure, shell syntax and applicability of the dispatcher patch to the exact base are also checked locally.

The proposed native entry is:

```sh
python3 -B Tools/TorahNativeOperations/run_account_rpc_lifecycle.py \
  --approved-source /workspace/approved-source \
  --heart-legacy /workspace/heart-legacy --heart-new /workspace/heart-new \
  --work /workspace/work/account-rpc --evidence /workspace/evidence \
  --expected-app-sha "$EXPECTED_APP_SHA"
```

The container wrapper installs the same compiler packages and retains the original actual musl `qsort_r` static-link probe. The workflow uses an independent Linux runner; no Windows build, checkout, cache or archive is part of this lane. Source publication remains a later small, reviewed action in the parent's owned checkout.

## Limits that remain explicit

App capability stays OFF. These races do not exercise generated-byte caller cancellation, signed settings deletion, template uninstall, standalone Space.Close, account switching, member ACL transport races, power loss, iOS or the separately active new engine. Their outcome cannot establish all T2 acceptance. The reviewed fixture requires the original host append result before AccountStop acquires its writer lock; later generated response-byte encoding may finish after that acquisition. In the block-deletion case only the durable-write boundary is ordered before deletion acquisition; both successful results are required without a response-order claim.
