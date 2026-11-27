# Ordinary native attachment source checkpoint — 27 November 2026

**Status: SOURCE_ONLY.** The new adapter and 30 declared component methods have not been compiled or executed. This checkpoint does not qualify native end-to-end, Apple/App, crash-journal, cloud, ACL or release acceptance.

The additive Engine adapter uses the original raw FilesV2 attachment route, bounded file fingerprinting and staging, and bounded response transport. Host owns one durable action reservation and known-ID reconciliation through the existing shared journal. `AnyNativeObjectCreator` adds only the `fileAttachment` identity kind and a typed factory retaining the original client, workspace and journal. The original object creation and recovery bodies are preserved.

See the contract in `docs/architecture/ordinary-file-attachment-contract-20261127.md`, the exact candidate and test inventories, the primary original source manifests and the source review here. Original source findings and predecessor hashes and diffs are preserved as source findings; they are not labelled as executed failures.

The checkpoint is intended for a normal isolated commit in the canonical Oracle worktree after capacity admission. It does not change the final integration branch, App/Package/native pins or workflows, and does not dispatch CI. All 83 original YAML workflow definitions were read at the exact parent: no push/create trigger matches this branch. Oracle remains the component and native qualification environment under its unchanged resource and ownership admissions. Wave 3 owns final integration and release.
