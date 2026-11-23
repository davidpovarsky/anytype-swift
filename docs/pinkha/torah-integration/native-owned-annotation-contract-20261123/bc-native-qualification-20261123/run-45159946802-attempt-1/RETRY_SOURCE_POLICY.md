# Infrastructure continuation proposal — not activated

## Exact frozen admission

At `1ec511b046fff1c46aaeb8425b98932a19400ad2`, `.github/workflows/otzaria-owned-annotation-import.yml` admits the exact repository, push event, isolated qualification branch and `github.run_attempt == 1`. There is no manual-dispatch trigger. The native driver binds its `--control-head` to actual HEAD, the exact workflow/template/manifest bytes and the reviewed candidate-to-control path allowlist; it does not contain an independent run-attempt override.

Official GitHub documentation states that `github.run_attempt` starts at 1 and increases for each rerun, while a rerun retains the original `GITHUB_SHA` and `GITHUB_REF`. Therefore a normal same-run attempt 2 fails the frozen attempt predicate. No predicate modification or rerun has been performed.

Sources reviewed 2026-11-23:
- https://docs.github.com/en/actions/reference/workflows-and-actions/contexts
- https://docs.github.com/en/actions/how-tos/manage-workflow-runs/re-run-workflows-and-jobs

## Smallest proposed unchanged-byte continuation

After explicit root scheduling authorization, create exactly one commit whose parent is the failed source and whose full tree is unchanged:

- Parent: `1ec511b046fff1c46aaeb8425b98932a19400ad2`
- Tree: `5ad7c12f9244e168b618189682cf6413672cd312`
- Branch: `codex/otzaria-native-import-qualification-20261123`
- All source, fixture, driver, manifest, workflow, toolchain, selector, attempt predicate and deadlines: identical bytes.
- The commit message would explicitly identify infrastructure continuation of the zero-step allocation failure; it must not contain a CI skip directive.
- Root would update only the owned branch with expected old SHA and non-force semantics.
- The resulting event is a **new run ID, attempt 1, new commit identity, identical complete source tree**. It is not attempt 2 of run 45159946802, and its identity must never be reported as that old run.
- Discover exactly that new source once, install one immutable owner binding and one bounded 120-second observer, then authenticate real native results. Preserve this failed run separately.

The source admission path remains valid by construction because the complete control tree is identical and the original candidate remains an ancestor. Root must independently verify the generated child parent/tree and actual remote identity before activating its observer. This document proposes the continuation; it neither creates the child nor performs publication or dispatch.
