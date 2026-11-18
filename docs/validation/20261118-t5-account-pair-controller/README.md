# T5 actual account/export controller validation

This source adds a separate four-process native RPC/account/export route. Its native execution is NOT_RUN at this source handoff. Twelve Python controller test functions and 34 subcases passed on Windows with zero skips. Go gofmt parse, Python AST parse, workflow YAML parse, and shell syntax checks passed. These are not native acceptance.

The fixture uses actual service RPC entry points and unchanged Heart d98420b with separate exact r14/r15 inventories. It creates one disposable local-only account, reopens the same account and Space in later processes, preserves real document/block identities, and checks original JSON/Protobuf export bytes. Only an exact named native pass in all four processes can produce NATIVE_ACCOUNT_PAIR_PASS. Apple packaged-app/Swift pairing, physical UI and full T5 acceptance remain unproven; the product flag stays off.

The original component-pair harness remains byte-identical to 01025e412e7382cc6bb8107dd11b2ca7e15f5d7d. The reviewed source/pin for native patches remains 947fbde24d5657d0e1229f45bb3993648884a8a1. The temporary genproto selection reuses c8523ab3d57ad2c8e3b3c11105df068462ecfbd7 and verifies both h1 hashes.

The sibling component-pair re-run was dispatched as 44217298120 on published integration c8e5a0e148021662dd943f93faeb3195c6086888. Its outcome is independent of these controller checks.
