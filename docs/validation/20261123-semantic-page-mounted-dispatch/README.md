# Page154 mounted workflow dispatch wiring

The existing reusable mounted workflow now selects the reviewed original consumer admission `45116855451-1.json`. The only workflow source edit is that one filename substitution. The obsolete pending admission `45106989988-1.json` is not used.

The central `semantic-page-apple-mounted` choice and reusable job were already present exactly once in the frozen isolated App line. They remain byte-for-byte unchanged. The route still opts in through an exact equality condition; other choices, jobs, permissions and defaults are unchanged.

## Source boundary

Parent: `cb89f4d1118023fa9c6260ea556c691f8f89f400`.

Frozen App origin: `5a6a05d9152553b1bee661eadc7b539b25b10ae1`.

The unchanged mounted controller requires the checkout to match `GITHUB_SHA`, the admission to be committed, all nine source-plan entries to match, and every reused App/Module/UI/project/dependency input to match the original Products source. Its existing `product_inputs` function excludes only `Tools/`, `.github/` and `docs/` from that product comparison, allowing this workflow-only correction.

The static audit verified all 172 qualified control inputs against their original hashes and current Git blobs, the unchanged admission and source plan, and all 6,321 product Git object/mode entries against the frozen origin. Neither workflow is part of the 172-file control closure. The earlier qualification and its first outcomes are unchanged.

## Actual validation

`audit_workflow.py` parsed both workflow documents with duplicate-key rejection, verified the unique central route/reusable call, checked the exact one-token whole-file inverse, and ran `bash -n` on the sole mounted command block. The audit passed; the original stdout/stderr, exact command, source-retention ledger and source-review receipt are retained here.

The current job still checks out the dispatched SHA, uses the existing ARM64 Xcode-27 runner and 120-minute timeout, creates fresh work/evidence paths, and uploads the execution evidence with `always()`, 14-day retention and an error for a missing artifact.

No controller test, prior pair control, simulator action, Apple build, product test, Products restore or workflow dispatch was performed for this correction. Actual mounted preparation and UI acceptance remain NOT_RUN.

## Independent qualification review

`root-mounted-adapter-review/` preserves the parent's original review script, root-review JSON, stdout and stderr byte-for-byte. The original root review SHA-256 is `1b2b226caf961048aa9de29c64ea513e016ca05f3c03b847cd0f08bd92e8faa5`; `root-review-copies.json` binds each original path and copied digest.

Publication and dispatch remain owned by the parent. The intended central route is `semantic-page-apple-mounted` on the reviewed isolated frozen-App line; it reuses the admitted original Products and does not rebuild them.
