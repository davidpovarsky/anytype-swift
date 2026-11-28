# Per-member sharing roles — frozen source candidate

Base: `6ade3661c261e66c987b7017a6181bdfcebc1d58` in davidpovarsky/anytype-swift.

This is an isolated five-file source candidate for review. No Git ref/worktree, backend/wire contract, Package, PBX or controller is changed by this evidence transfer. No compiler, tests, account operations, Mac or runtime were invoked.

The current Native adapter exposes invalid Guest upgrades and Writer/Admin-to-Guest choices through a global role list. The candidate separates ordinary approval roles from per-member role changes. Both Owner and Admin retain the valid Reader-to-Guest transition. Guest membership remains independently removable under the original restrictions.

The shared optional map defaults to nil, preserving Heart's current behavior. A supplied map fails closed for missing targets. UI and mutation validation consume the same accessor. All 28 existing sharing accessibility identifiers, including the prior 23 additions, remain exact.

`proposal.json` is the original approved-scope 13,252-byte c21e2727 proposal. `superseded-role-gap-assessment.json` preserves the exact earlier 10,580-byte 46108494 assessment; its conservative removal of Reader-to-Guest is superseded and is not implemented.

`literal-replacements.json` reconstructs every complete candidate from immutable full originals, and reverses the complete candidates to those originals. `source-proof.json` records the exact nine rules, full inverses, retained method bodies and complete test prefixes. Full Swift candidate bodies are under `candidate/`; these are data artifacts, not files installed into an active source tree.

Five new XCTest methods are appended to two existing inputs. The shared class grows from four to seven methods; NativeApplicationTests grows from three to five. Their internal fixture/matrix rows are not extra XCTest leaves. All five new cases are NOT_RUN. Future selection/typecheck/compiled-inventory admission must be explicit; existing accepted cases and runtime gates are not altered.

The exact original Native any-sync v0.13.8 validator/models independently match W1's source pins. Native still authorizes every action. Decline remains identity-only, with no caller expected-record guarantee. W1 owns the consumed-request typed error correction. The historical removed recipient supplies no fresh pending request fixture, and this change claims no recipient convergence, unknown-ACK recovery, Apple UI or Native acceptance.
