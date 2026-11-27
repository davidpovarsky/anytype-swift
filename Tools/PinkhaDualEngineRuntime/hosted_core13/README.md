# Original Core13 on the live hosted producer

This is a new runtime entry point for the same GitHub job that compiled the
original App and complete Stage1 UI products. It runs no compiler, prepares no
native account and changes no old Mac, T5 or closed-profile entry point.

## Executed interface

Run once after the original hosted producer succeeds and before product
retention or runner teardown, using the same `DEVELOPER_DIR` and root plan:

```sh
python3 -B control/Tools/PinkhaDualEngineRuntime/hosted_core13/run.py \
  --control "$GITHUB_WORKSPACE/control" \
  --source "$GITHUB_WORKSPACE/app/source" \
  --build-root "$BUILD_ROOT" \
  --plan "$RUNNER_TEMP/pinkha-root-plan.json" \
  --plan-sha256 "$PLAN_SHA256" \
  --output "$RUNNER_TEMP/pinkha-hosted-core13-${GITHUB_RUN_ID}-${GITHUB_RUN_ATTEMPT}"
```

The owner of the hosted build workflow adds that step. This directory does not
modify the workflow or its original producer. An unsuccessful admission exits
before simulator creation. Re-running over the same execution directory is
refused; an old result is never overwritten.

## Exact admission

The adapter requires the original GitHub-hosted ARM64 repository/run/attempt/job,
clean executed control commit, root-reviewed source commit/tree and exact live
workspace/output paths. It verifies the actual completed App/UI producer,
original process-exit and group observations, source snapshots, original native
transport and assembly, complete Products, all 57 selected native and 10 UI
sources, actual compiler invocations/FileLists and three original toolchain
outputs. It reconstructs the actually executed expanded producer from the
unchanged original 204f producer and reviewed hosted adapter, then compares every
byte and the original full inverse proof.

The hosted owner is the exact `079ec77f508ce508096d8534f66a4d5164efbde26b49b67075999dce3e32d47a`
successor; its native input helper is
`e8aaf254140c06410813d5ab6f3b9168b71c1722dfe2ecdac8155a1bdc9d4d3c`.
The common build gate is the exact published d63b8a04 version. A source or
producer change requires a reviewed successor, not a path override or relaxed
hash check. The common gate's retained MiniApps method labels describe its
original contract; this invocation executes no MiniApps methods.

All 15 original Python control files are pinned by byte length, SHA256 and Git
blob in `original_sources.json`. The loader retains the exact original selected
AST declarations, decorators/defaults and the complete original `Commands`
class. The emitted declaration proof identifies every original function/method.
Swift tests are neither copied nor projected: the original hosted source and
actual compiler witness bind the exact three package files directly compiled
into `AnytypeTests`.

## Runtime scope

| Original source suite | Actual hosted target | Methods / cases |
| --- | --- | ---: |
| AnyNativePropertyPresentationTests | AnytypeTests | 9 / 9 |
| AnyNativeTextBlockCreationTests | AnytypeTests | 2 / 2 |
| AnyNativeTextTypographyTests | AnytypeTests | 2 / 2 |

The exact method names and source hashes come from the unchanged original
`native_core_hosted_profile.fixed_contract` and `source_contract`; there is no
caller-supplied suite/method list. The separately owned Renderer3 successor can
extend that original finite profile only after publication and review. This
entry point remains Core13 and will reject any changed pinned profile bytes.

`simctl list --json` must report one available OS27 runtime and the original
iPad Pro 13-inch M5 type. Missing or ambiguous runtime information fails closed.
The three producer toolchain commands are repeated read-only under the same
selected Xcode and compared with their original output. A fresh owned iPad is
created for each original suite; its actual UUID, name, runtime, device type and
boot state are checked before executing tests. No retained account or old
fixture is admitted.

The actual Products are verified completely, then cloned on the same host into
the new owned directory with modes/links/bytes verified. Original descriptors
remain unchanged. The original descriptor binder permits only its established
selector/environment delta, with full inverse and unchanged injection settings.
There is no cross-host prefix rewriting.

Each suite uses the original 180-second enumeration and 600-second complete
host-suite allowance. The original exact enumeration, xcresult node/argument
validators, real test success terminal, installed Mach-O code identity and
actual runtime/UUID checks remain in effect. Zero, missing, extra, skipped or
failed methods cannot produce acceptance. The original 2 GiB live floor,
owned-process groups, bounded terminate/reap and positive ESRCH rules are
unchanged; historical positively absent groups are not probed again.

An adapter-owned admission barrier wraps the unchanged original command class.
An unresolved owned group permanently closes all later command admission,
including original xcresult helper calls. The adapter also skips private
container reads and simulator shutdown while that barrier is closed. The
original final read-only observer can record later absence, but that observation
cannot reopen execution or erase the earlier unresolved custody failure.

## Evidence and cleanup

Always retain the separate runtime output on success or failure before runner
teardown. It contains raw command logs/process receipts, every original
enumeration/invocation, xcresult bundles and extracted summaries/tests/attachments,
per-suite execution/result receipts, exact input/admission and original control
proofs, cloned product inventories and the final `receipt.json`. The build
owner retains the complete original compiled source, Products and producer
evidence separately. Read-only private witness copies belong to the fresh
disposable test sandbox; original helper fields describe the observation when
it was made, not a later artifact upload.

Failure preserves the failed lane as failed, including whether its real test
command was invoked. Original validator counts are separate from fully
qualified suite counts. Private retention or owned simulator shutdown failures
also fail the final cleanup. A create command without an admitted UUID remains
unresolved; the adapter does not guess another simulator's ownership. Only its
recorded UUIDs are shut down and checked again; no simulator is deleted.
Terminal, checkpoint and final receipt write failures preserve the first error
in memory and report the later IO failure separately. No partial receipt is
overwritten. If the final receipt cannot be retained, original process stdout
contains the failure/retention observation and the adapter exits unsuccessfully.

`PASS_ORIGINAL_HOSTED_CORE13_METHODS` requires all 13 original methods/cases and
successful owned cleanup/custody checks. It provides no native persistence, ACL,
network, MiniApps, app UI, physical-device, Release or TestFlight acceptance.
This source checkpoint itself has **not executed Apple runtime tests**.

## Portable controls

```sh
PINKHA_CORE13_ORIGINAL_SOURCE=/absolute/original/source \
  python3 -B Tools/PinkhaDualEngineRuntime/hosted_core13/test_control.py
```

The eight portable methods check exact original declarations/scope, byte-tamper
rejection, same-job source/plan authority, observed runtime ambiguity, owned
device/shutdown identity, failed-lane/cleanup reporting, closed command admission
after unresolved ownership, and preservation of the first failure despite
receipt IO failure. Their temporary
fixtures never invoke Apple commands, create simulators or open accounts. They
do not substitute for real Core13 execution.
