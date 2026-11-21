# Heart authorized-read Apple simulator candidate — original build proof

GitHub run [44958624297](https://github.com/davidpovarsky/anytype-swift/actions/runs/44958624297),
job 137012224439, completed successfully from exact App source
`0712b0492361e422c5b0cffdf0a95374f29eb305`.

All 70 original producer proof files are retained byte for byte. The original
proof ZIP has SHA-256 `b42c603a15a8871175d14a5f689255a53b88b3fc3680ba8afeff2426da8e0d5b`;
`evidence.json` records each original file hash, source and artifact identity.

## Qualified result

- Exactly one ARM64 iOS Simulator framework was built with Xcode 27.0
  (27A266a), SDK 27.0 and the pinned Go compiler.
- Candidate identity is `69b6b3fc8616b11230cbc45ced0635f60098950a1e611a089ab73baf70550b67`.
- All eight qualified input groups match native run 44954793488: 85 source
  files, four actual generated Go bindings, native modules, protobuf inputs,
  and the source inventories. The candidate identity was recomputed from them.
- All 36 controller commands and 23 actual Go launcher commands completed
  successfully. The actual generated module has one scope, with both build
  and tidy recorded as `ios/arm64`, `iphonesimulator`, `GOWORK=off` and the
  same pinned dependency contract. No r15 product evidence is relabelled.
- The nine-file framework inventory binds the actual binary to SHA-256
  `8fefe0d25fecf116ef3b46b07def04e7a3a613b5513bd8fd6e2a9ba28f5ef8b0` and
  the complete `AppGetVersion` marker recorded in the original receipt.
- Eight controller admission controls passed. The previously qualified
  native 71 cases and two real account processes were retained by exact
  source equality; **no native test ran again**.

## Consumer and claim boundary

The framework artifact is `Pinkha-Heart-Authorized-Read-Simulator-v1`, ID
14729089597. Its GitHub ZIP digest is
`1002db53095f5e0f0b7b2250902f5a78ccf69686b35d4b8e92ece3e0f531c206`;
its contained tar digest is
`79414b311d736e2499264efd29949b01ab3f1caeaac6be6fbae07a5068738f1e`.
The large framework was not downloaded again for this report. The fixed25
SwiftPM iOS host verifies the entire downloaded framework inventory against
this successful producer before execution, then checks the actual full
native version inside its process.

This receipt proves a source-qualified simulator build, **not iOS execution**.
The fixed25 Heart iOS methods, fresh iOS-process reopen and two-App-client
acceptance are not asserted here. Full T2/App capability remains OFF; the
App's default and corrected-r15 runtimes remain unchanged.
