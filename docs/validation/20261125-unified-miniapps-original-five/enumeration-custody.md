# Original enumeration infrastructure failure

Attempt3 retained exact original execution `ba3cb5d2d8598cdbaa531a74bc3a8ecc11d41ddca15a220b72b93b544babb70c`: both actual apps installed, but the first native-method enumeration exceeded 180 seconds. Cleanup raised EPERM while observing its original group. Zero test-method commands started and zero methods executed; enumeration did start the real application. The initial failure and original log/started receipt remain unchanged.

A separate bounded UID501 process snapshot observed that original group23762 had exited, with no signals. The new wrapper preserves a FAIL command result and exception chain if original cleanup fails before result persistence. It performs only a bounded process read, does not signal unresolved/recycled groups, and never upgrades such a result to PASS.

The next enumeration budget is 360 seconds because original current-platform enumeration has stalled in Xcode Instruments/testmanager launch before test code. This is an infrastructure setup allowance only; the original five methods, 600-second command budgets, source/native/companion identities, actual xcresult counts, native readbacks and every assertion are unchanged. No test method is accepted by this controller change.
