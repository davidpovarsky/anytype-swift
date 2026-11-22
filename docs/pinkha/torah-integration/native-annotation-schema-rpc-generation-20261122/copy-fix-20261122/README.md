# Preserve the materialized SDK source in private generation lanes

This candidate fixes only the SDK source-copy preparation that failed in actual generation run [45052270280](https://github.com/davidpovarsky/anytype-swift/actions/runs/45052270280). The full failure archive and terminal observer are retained at commit `2e4a004778d5cc29afebaa4c278a2f1a8bf5c74d`. Neither the failed run nor this source preparation claims actual RPC generation or compilation.

## Source-dependent change

The exact executed checkout action, `actions/checkout@11d5960a326750d5838078e36cf38b85af677262`, selects `blob:none` when sparse checkout is enabled. Its original `src/git-source-provider.ts` is retained in `ACTIONS_CHECKOUT_ORIGINAL_SOURCE.json`, with original Git blob `2d3513897655e0ea2eb4efc2b2c9d6132a69549f`. The actual SDK input is therefore a materialized sparse checkout backed by a promisor repository. The original local clone attempted upload-pack and failed on a missing promised object before any tool download or generation.

The driver now invokes one finite `copy_materialized_checkout.py` child per SDK lane. It copies the existing checkout and its private Git directory using ordinary filesystem copies. It does not serve Git objects, hydrate the repository, expand sparse scopes, or fetch a second remote checkout. The exact original SDK commit remains `3be6ecab805b17e2c90fee897fdab45a0b03bfdc`.

The helper rejects symlinks, nonregular files, linked worktrees, alternate object storage, shared common directories and external worktree/include configuration. It verifies exact HEAD and clean status with optional Git writes and lazy fetching disabled. It compares complete copied file membership, bytes and modes; verifies that source and copy do not share file identities; and rechecks both inventories after Git readback. Each lane retains a compact receipt with the complete inventory digest and measured counts. A partial copy failure remains owned by the original finite command-group cleanup.

## Preserved source and acceptance

The original driver’s seven helper bodies remain byte-identical. The other ten original control files, all 42 original input rows, the custom protobuf replacement, archive pins, two proto afterimages and original generation recipes remain unchanged. The original Heart and SwiftProtobuf checkout routes are unchanged. Only the two SDK clone/sparse/checkout sequences become two private-copy commands, reducing a complete successful command plan from 41 to 37.

All original fresh-output removal, required-output checks, separate baseline drift and candidate delta, Go message compilation, generated Swift model typecheck, failure capture and process-group drain checks remain. No handwritten generated code, package/module rewrite, native test selector, application build or runtime acceptance is added.

The workflow binds only the new dedicated branch and the exact execution manifest hash. At root review’s request, the paths filter is removed before freezing this candidate; the prior zero-run routing evidence is preserved without attributing its cause to that filter. The workflow uses the same six SDK sparse scopes. The original attempted-run verifier is preserved unchanged in its failure packet; the new verifier adds the two copy receipts and the revised manifest/command-count binding. Its finite observer template is unbound and refuses execution until an exact actual run is assigned.

## Local preparation evidence

`LOCAL_PARTIAL_GIT_COPY_CONTROLS.json` records aggregate local preparation controls against a real partial Git repository with an unfetched blob and its source remote taken offline. Both private copies passed, the blob remained unfetched, a candidate-file mutation left the source and baseline unchanged, and alternate object storage was rejected before creating the target. The fixture directory was removed. No product, original generator or native test ran.

The local Git version was 2.56.1; actual Actions used 2.56.0. The local old-clone diagnostic returned zero, so these controls do **not** claim to reproduce the original Actions failure. `LOCAL_PARTIAL_GIT_OLD_CLONE_DIFFERENCE.json` preserves the earlier overly strict reproduction assertion. `LOCAL_PARTIAL_GIT_FIXTURE_SETUP_FAILURE.json` preserves an earlier setup mistake that disabled lazy fetching before the fixture itself was materialized. Neither result is a product/helper failure or has been rewritten as a pass. The copy helper’s bytes were unchanged across all of these local observations.

The next gate must execute actual original generation and the existing limited message compilation before any generated outputs are reviewed or integrated. Middleware endpoint compilation, Invocation error/late-cancellation behavior, full SDK integration and selected-destination production wiring remain separate dependencies. All previously passed native controls are preserved without replay.
