# Coherent Release recovery (controller evidence only)

The original combined run 45047830860 completed one Release app/native build and one UI runner build. It executed zero new Release or T5 product tests. The editor destination passed the original create/identity checks and bootstatus. Its redundant postboot scoped inventory then timed out after 120 seconds. A later 2-second process-inventory timeout during cleanup replaced the first failure with a misleading BATCH_BUDGET_EXHAUSTED label. Original worker supervision lasted less than its 6300-second limit.

The audit retains exact original receipt bytes (larger receipts use lossless gzip) and records SHA-256 hashes of both original archives and the complete job log on Oracle. Historical producer Heart results inside the archive are replayed evidence, not newly executed tests. The failed run's successful build binaries were not retained and cannot be reused.

## Changes

- The coherent lanes use the existing owned simulator readiness helper. The exact new device must first be Shutdown, then its bounded boot and bootstatus commands must succeed with proven owned process cleanup. Readiness keeps the original preboot identity, command metadata, and log hashes. It does not perform the redundant postboot inventory or invent a Booted observation.
- Container freshness still comes from creating a new owned destination before its first app installation. A negative container lookup remains explicitly unclassified. Original preparation/UI/postflight result counts, methods, destinations, source/runtime checks, and original receipt revalidation remain required.
- The outer supervisor preserves an already terminal, matching-source original worker failure when later cleanup fails. It records cleanup failure separately. A timeout is a worker budget exhaustion only when its exact command and 6300-second timeout match the worker invocation. Cache publication still requires actual proven cleanup.
- Immediately after each successful native and UI build, the shared early_build_products helper preserves original Build/Products and Xcode configuration before admission. These archives grant no build reuse or acceptance. This change depends on helper commit 02a3873c74230a6932f69aebde6ee454d8a58ca3.
- New readiness command groups are included in final nested cleanup.

## Verification

Five new focused controller controls and one directly affected existing exact-union builder control passed in 0.043 seconds. The exact-union control only gained the required mocked run-attempt identity. The new controls exercise successful readiness, failure to reach readiness, altered original evidence rejection, call ordering, preservation of the actual first worker error, and preservation of native/UI original products before their first failed admission. A replay using the complete original 1 MB worker receipt also preserves the actual 120-second simctl failure. No XCTest, device, or release acceptance is claimed.

The separately committed cleanup fix (04f9067c8652afbeb628660137d7476e08fd72c4) passed three focused controls. It keeps the original 10-second total budget and 2-second maximum per probe, and requires a real numeric process inventory showing zero live owned descendants.

## Minimal next Apple execution

On the final c883-derived acceptance continuation branch with both dependent fixes integrated, dispatch torah-inspector-ipados27.yml with:

- route: wave15-acceptance
- acceptance_lane: coherent-heart-release
- acceptance_device: ipad
- acceptance_language: en
- runtime_profile: r15-attachment-authorized-current-read-v1
- source_run_id: 45046643716

This reuses only the qualified retained Heart producer. The three missing Release lanes and T5 scopes share one native build and one UI runner build. Existing worker and step budgets are unchanged. Any simulator readiness, native, UI, source, signature, or cleanup failure must remain blocked with original evidence.
