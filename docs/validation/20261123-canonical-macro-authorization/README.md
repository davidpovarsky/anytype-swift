# Canonical Anytype SDK macro authorization

## Exact original failure

Run45127350746 attempt1 at5f00e14996d3ef8b4d93290a80db21797cb928ce failed in BUILD before compilation or XCTest. Xcode's dependency graph rejected EquatableMacros because its package fingerprint had not been authorized. There was no simulator failure: the original disposable iPad booted. Native preparation1 and UI1 are NOT_RUN; no current screenshots exist.

The original artifact14798256276 is656496bytes, SHA2566f4901a830ba81e0bfdd05c22a57b4ec4038f7feb3d11b3b281b1301d7035ade. SHA, size and both ZIP layers' CRC were verified. The original execution, compiler log, SDK snapshot and runtime installation receipt are preserved as deterministic gzip files here; the complete extracted artifact remains in build/canonical-native-admission-20261123/original-artifact.

## Narrow correction

The new downstream prebuild helper resolves only versions from the existing Package.resolved. It then verifies the exact original Equatable1.4.1 commit597c2bb34af0c51331eb3b5e705f942d8ee20daa, every tracked blob and executable mode, all compilation-source membership, and a clean checkout. It authorizes only the EquatableMacros target/revision fingerprint, atomically preserving existing compiler trust entries and permissions. Normal Xcode macro validation stays enabled. No global or command-scoped macro-validation bypass is used.

This follows the exact fingerprint mechanism already proven by the original Maktabah native run45125110974. The actual upstream manifest at the pinned commit was also read: Git blob2cb7e844884a029dd205d12e8b26224a710eb17c, SHA25621f122fb50207cf54b2177b6fcf85841ad40371769ba0d6587828748cc8b60f3.

SwiftPM's original GitRepository.createWorkingCopy uses a shared clone from its local repository cache for non-editable dependencies. Therefore the working-copy origin may legitimately be a local path; the helper records it and binds authorization to the immutable lock and content-addressed source commit instead of requiring the origin URL to be remote.
Primary source: https://github.com/swiftlang/swift-package-manager/blob/main/Sources/SourceControl/GitRepository.swift

The existing controller only adds disableAutomaticPackageResolution to the isolated canonical branch's plain hanlin-native build. The workflow prebuild step has the same exact branch/lane condition. Original preparation/UI selection, runtime installer/qualification, simulator isolation, native observation and receipt guards are unchanged. No host Swift, Heart, protobuf, module, native engine, SDK pin or original SDK06 owner's selector work is modified.

## Focused verification and evidence retention

- Four new macro controls passed in0.362s: exact target-only authorization and idempotence; dirty/hidden changes; pin/revision/source drift; malformed or linked authorization store.
- The initial checkout-origin guard was then corrected to match actual SwiftPM local-cache semantics. The affected pin/revision/source control plus a real git clone --shared local-cache reproduction passed in0.125s. The superseded remote-origin rejection is not claimed as a current contract.
- Three affected fixed-policy retention controls passed in1.370s: exact69 binding, rejection of changed runtime/candidate source, rejection of forged policy changes. Original69 controller tests were not executed.
- Actual Python imports were observed separately:28 original modules, exactly matching the new immutable import receipt. The retained policy still covers29 inputs including the original core-test manifest. Whole-file reconstruction permits only the prior reviewed branch/pin-reader changes plus the exact lock-only compile flag.
- The old owner proof files and their failure conclusions remain unchanged. Current app compilation and native1/UI1 remain required.

The next eligible retry selects only the same original native preparation1 and UI1 on the disposable iPad, with qualified runtime45091223011 and the existing SDK d49 pin. SDK23/32, ACK7, broad application tests, device distribution and the live provider are outside this retry.
