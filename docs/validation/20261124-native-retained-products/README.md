# Native UI continuation from the preserved build

The original Native UI run [45425747246/1](https://github.com/davidpovarsky/anytype-swift/actions/runs/45425747246) built the App and UI runner successfully at source 95cd30c9e0d70fec368a1605a21b155a652a7afd. Its provider setup failed before any UI method ran. The workflow remains failed. Its original receipts, 828-entry Products inventory, code signatures, source proof and dependency records remain intact.

The new central route is **current-native-ui-retained**. It reuses the existing inline Native UI job and selects native_ui_retained.py. No reusable workflow or job was added: the dispatcher still references the same 50 unique reusable workflow files. The existing current-native-ui-failed route keeps its original fresh build behavior.

## What the continuation admits

The controller accepts only the preserved build from run 45425747246, attempt 1. It verifies the original GitHub run and artifact identity, six original receipt hashes, the archive hash and size, the completed build record, and the failed run's empty stage list. It requires the original Modules and NativeApp Git trees and all six UI test contracts to remain unchanged. Thirteen explicitly reviewed helper paths may differ; their original and current Git identities are recorded. The TLS fixture must have the qualified certificate fix.

The archive is extracted into a fresh owned directory with Python's safe archive filter, then its original directory modes are restored from the fixed inventory. Every original file, symlink, directory, mode and hash must match. The App's original Mach-O hashes and signature and the original test descriptor must also match.

SwiftPM checkouts were preserved with absolute Git alternates pointing to the former workspace. Only the new copied checkout alternates are rebound to the corresponding copied object stores. The controller verifies all other copied bytes and modes, records each relocation, and requires the nine original dependency commit IDs, clean tracked worktrees, canonical Hanlin marker and unchanged workspace-state hash. Original retained directories are never edited.

The common executor then creates fresh owned simulators and the corrected provider. The existing six selectors, assertions, finite provider contract, archive checks, custom-type postflight, source rechecks and cleanup rules remain in use. The first four journeys must pass before custom type and history run. No previously passing historical 22 methods or source-drag method is selected.

New App, UI runner and native-library build counts are zero. The new execution records both the current controller context and the original build context. It does not relabel the old failed workflow or its build source as a new build.

## Verification and limitations

- Six bounded pure admission controls passed. They cover exact original receipts and reviewed helper changes and reject changed compiled trees, changed test contracts, an unqualified TLS helper and modified original source receipts.
- Actual Mac restoration passed for all 828 Products entries, the original signature and code carriers, the unchanged six scoped selectors, and all 5,301 copied dependency entries. All nine original dependency heads and workspace-state hash matched after the explicitly recorded copied-alternates relocation.
- Product hash tampering and an unregistered descriptor were rejected.
- The first restoration check detected directory mode normalization; the second exposed stale absolute SwiftPM alternates. Both failures and their concrete repairs are preserved in separate receipts. These checks executed zero UI methods, builds or simulator operations.

These are restoration and admission results. The six product UI journeys are **NOT_RUN in this continuation** until a real Actions execution produces its own results. A change to Modules, NativeApp, the six contracts or other unreviewed helper paths blocks retained-Products reuse and requires a separately reviewed build/continuation.

## Retained originals

- Mac: /Users/m1/builds/_retained-anytype/45425747246-1/build/current-apple-native-ui-failed-45425747246-1
- Original artifact: Current-NativeApp-Unresolved-UI-45425747246-1, id 14937235337, SHA-256 64474c84d9a3b425a94bf3ecff5addc599abb691556b2400b2ca555fc122c06d
- Products archive: SHA-256 23f47726b5646fcf09876f19073d58f1bb4415c140e11b5e64015ed706c7b2d4, 89,138,665 bytes
- Successful Mac restoration control: /Users/m1/builds/_preflight/anytapy-20261124-native-retained-v3/qualification.json

Before dispatch, integration must rebind the Page controller descriptor for the changed common executor and the SDK dispatcher descriptor for the changed central workflow. Parent integration owns those shared manifests. The candidate intentionally does not overwrite them.
