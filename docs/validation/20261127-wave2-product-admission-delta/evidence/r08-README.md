# T5 R08: exact localized startup warning

This source-only correction lets the existing T5 startup helper recognize the exact production middleware warning in the language requested by the original test. R08 explicitly launches Hebrew, while the current helper recognizes only English. The preceding actual English core2 startup failure remains retained; this source change does not create a new UI result.

Base: `cee06ac951f735514059e616fbea48f07d4e7c09`, tree `7a1793b6fb4f074653814642fdae56b5e8a21633`.

Changed downstream-owned test file: `PinkhaStage1Acceptance/Tests/PinkhaT5NativeAcceptanceUITests.swift`.

- Original: SHA256 `698f4ed7f1f81fe567b94b531f43e14259d08e6acbf79d72e132a5b9b6b941a7`,34098bytes, Git blob `58a2e07fb3a2737ebfa1fb939bb7ab7f45da2f1f`.
- Candidate: SHA256 `b43f97b3c1283f05b728b15cc9871bfecc1692ca55563f1e2c1f1886ecd38d5e`,34629bytes.
- Production `Auth.xcstrings`: SHA256 `8ee4b81dfe98236853f6ba3949148ca2c2c8ca78aefdaf676c40aa128aa33161`, Git blob `86c6301edc3c17fe01eb563bb045161eb397c8f2`.

Only `launch()` and its existing warning helper change. Each chooses the exact requested language's title, full message, Continue and Logout labels. Setup already restricts the language to en/he and Hebrew to the separately reported R08 lane. The helper still requires the original source/run/token/disposable-account binding, one unique alert, exactly two distinct actions, and an enabled/hittable Continue. It taps only Continue. The original total120-second startup deadline remains.

English strings and original actions remain identical. The final readiness check deliberately becomes stronger for both languages by requiring zero alerts, so an unknown or returned dialog is left untouched and cannot establish successful startup. This is not a generic dismissal, authentication bypass, logout/reset, timeout extension or new source/fixture contract.

All three original test methods, setup, fixture model, observations, captures and all other helpers are byte-identical. There are zero new methods or cases. The seven exact substitutions invert to the complete original source. `prepare_source.py` produced the source inverse only; no Swift compiler, XCTest, UI, simulator or Native call ran. Root's independent review is retained unchanged as `root-independent-review.json`, SHA `8401c0031cc84e58cfa189e8083f6813e7039e430342f71f8da0ef8db5dbeed1`.

The exact file must enter the next shared UI build and its real compiler inventory. Only after the matching producer/consumer admission may the original core2 and R08 he-light/he-dark run. The three methods and existing result/attachment validators remain their acceptance authority. Current renderer, Page154, T5 freshness and other product/controller sources are not changed here. Historical36+9 Native calls are not selected or replayed.

## Publication and retention boundary

The isolated publication uses a new owned GitHub branch, `codex/chatgpt-wave15-wave2-t5-r08-warning-20261127`, while Oracle capacity is held. It is an API Git tree/commit/ref publication, not a CLI push or a locally clean worktree claim. No existing ref is updated and no workflow is dispatched.

The original full recursive tree read returned `Transport closed`; that response is retained. Root approved the complete finite Merkle comparison: every root entry/mode/type/SHA stays exact except the UI and docs trees; all thirteen existing UI leaves are compared, with only this test blob changing; every docs child and all621 existing validation children remain exact, with one new scoped evidence subtree. Equal untouched subtree IDs preserve all their descendants. The exact new subtree leaves must match the local packet before commit/ref creation.

The original source-retention gate protects Anytype/Sources, AnyTypeTests, Modules and selected Tools paths. This downstream UI target is outside those protected paths and is not referenced by the130-row map. The gate, protected roots, inventories and map stay under unchanged subtree IDs. Parent130 acceptance is inherited at that precise source-retention scope, as reported by W3's actual source milestone1220950559845512; no new source-retention execution or runtime PASS is claimed.

All83 current YAML workflow sources were independently matched to their Git blobs and parsed. No create trigger exists, and none of the five push-branch filters matches this isolated branch. Workflow files remain unchanged. Original test/runtime/consumer gates remain closed pending the actual shared product.

The readiness subfolder retains the finite T5/Page154 selector queue and specific missing Native wire/current-Space/accepted Reader fixture handoffs. That queue is evidence context, not a new execution framework.
