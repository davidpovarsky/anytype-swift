# Page154 explicitly observed simulator pair

The previous Page154 run 45106989988 created an iPad mini A20 Pro on iOS27.2,
then failed its original 180-second bootstatus command. Both owned 30-second
cleanup commands also timed out. No App build, product test or Products archive
existed. Those outcomes remain preserved.

This separate source policy selects one pair that actually ran the earlier
Hanlin native preparation and UI method successfully: iOS27.0 build24A434,
arm64, iPad Pro13-inch M5 (16GB), model iPad17,4. The original Hanlin lane still
failed its separate runtime-observation gate. No cause is inferred for the
Page154 boot timeout, and no Page154 acceptance follows from the earlier pair.

The current runner must still report that exact runtime, build, architecture
and installed device identity, the runtime support matrix must explicitly
include the device, and numeric/text installed type bounds must agree and
permit the runtime. Missing or conflicting evidence fails closed. There is no
automatic alternate or fallback. The shared choose_pair implementation remains
byte-identical and validates the single policy-eligible pair.

The consumer integration changes exactly its selector import and call. It
still preserves the raw inventory commands, creates a fresh nonce-named owned
simulator, reads the new UUID from the create command, and uses the original
90-second boot, 180-second bootstatus and 30-second cleanup budgets. The old
UUID is included only in source-of-choice provenance.

The two original Page inventory logs and original Hanlin preflight member are
preserved byte for byte here. source-review.json binds their exact hashes and
the separate original Hanlin execution receipt. That receipt remains in its
original archive and recovered-source evidence; only its derived device/count
observations are repeated in this review.

At source freeze, the four new policy/refusal/integration controls had not run.
Root reviewed the frozen policy and exact two-line integration before authorizing
only those four new methods. Their actual receipt follows.

## Actual new-control evidence

At frozen source ebabf8dc7d91592ac957414c10cff0daad3f3e3d, exactly four new
methods passed: 4 PASS, 0 FAIL, original unittest duration 0.033 seconds.
All nine source/dependency/raw-input files were byte-identical before and after.
The loaded repository modules were only the new policy, its new test module and
the unchanged shared simulator selector.

The real consumer's inventory/create/boot region was exercised with a controlled
runner to verify that it uses the newly returned UUID and the unchanged180-second
bootstatus deadline. No simulator command, App build or product test actually ran.
All 6,038 Git App/module inputs remain identical to original1e9ee4de; this records
Git source identity, not a sparse-worktree product build. Exact original log,
named events, runner, source inventories and receipt are preserved under attempt1.
