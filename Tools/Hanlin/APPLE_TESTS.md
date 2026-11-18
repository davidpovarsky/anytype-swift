# SDK06 focused Apple component lane

The reusable workflow `pinkha-sdk06-tests.yml` builds `Debug-Anytype` on the
existing `xcode-27` ARM64 runner and runs only these four `AnytypeTests` suites:

- `HanlinHostAdapterTests` (22 reviewed declarations)
- `HanlinHostWriteTests` (12)
- `HanlinHostReadWriteTests` (17)
- `HanlinSDKConsumerTests` (6, including a two-budget parameterized test)

The Debug configuration is required: some journal and consumer tests are
compiled only with `DEBUG` and iOS. There are 57 declarations and 58 expected
parameter executions. The gate reads every declaration in the actual four
source files, requires the reviewed per-suite minimum, and checks every method
in actual xcresult test-case nodes. It accepts either Xcode's declaration or
parameter-execution summary counting, but never fewer than 57 passing tests,
an omitted method, an unrelated suite, a failure, or a skip.

## Integration caller

Root must first merge the focused source and this workflow into
`codex/chatgpt-wave15-integration-20261118`, include that exact branch in the
existing verified-Heart installer's supported branches, and complete the
separate Startup smoke. This workflow does not edit that installer or root's
dispatcher, and has no automatic push trigger. The coordinator then adds a
reviewed caller job (after Startup success):

```yaml
sdk06:
  needs: startup
  uses: ./.github/workflows/pinkha-sdk06-tests.yml
  with:
    expected_app_branch: codex/chatgpt-wave15-integration-20261118
    heart_source_run_id: '44203168617'
```

Use that source run only if its runtime build succeeds and publishes
`Pinkha-Universal-Verified-Heart-r14`. The input is required and there is no
fallback to the missing historical artifact. `startup` above names the caller's
actual startup job; adapt the job dependency to the reviewed dispatcher.

The workflow uses only `github.token` with contents/actions read permission.
Hanlin is public and is checked out at immutable revision
`116cc6be0654a5d11bc56ba00e0310031107ee36`. `prepare_sdk.py` materializes the exact
three local packages before any SPM resolution. It never changes the producer
repository. No certificate, model key, middleware download secret, or provider
call is introduced. Simulator signing uses the existing native lane's ad-hoc
flags. Fresh DerivedData prevents accepting stale test products.
The disposable simulator is booted before `build-for-testing`. App/test binary
paths come from the actual Xcode `.xctestrun` and each bundle's
`CFBundleExecutable`, following [Apple TN2339, Listing 20](https://developer.apple.com/library/archive/technotes/tn2339/_index.html).

## Evidence and limits

The runner rejects a branch or source/run identity mismatch and verifies both
the Heart installer receipt and the installed runtime bytes. It records actual
Hanlin snapshot hashes, resolved Swift AI SDK and Kit checkout/lock revisions,
app/test executable hashes, build/test commands, raw xcresult JSON, the full
xcresult and logs. The result must identify the fresh OS27 ARM64 iPad from the
run's preflight receipt. Source and dependency identities are checked again
after execution. Evidence is uploaded even on failure, with 14-day retention.

`SDK06_COMPONENT_PASS` covers these host and canonical-dispatcher tests. It does
not establish mounted document entry, real native page creation, account/Space/
scene lifecycle UI, network provider behavior, or release acceptance. Those
remain separate acceptance work. A Python gate test pass is synthetic evidence
validation only; it is never a Swift compilation or Apple test pass.
