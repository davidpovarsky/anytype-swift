# Embedded startup reservation and drain source delivery

Status: **SOURCE_ONLY_NOT_COMPILED_NOT_RUN**.

This carrier follows boot-identity commit f372f5e243427822df27bf8bd2ba51bf8206c644. It addresses the engine lifecycle interval identified in W3 Asana story1220965191752036: two native callers could both pass the running-handle check before either listener became Ready, and a restart could miss a graceful stop's teardown. The implementation and new tests have independent whole-source review and actual stdin-only gofmt parsing. They have not been compiled or executed.

## Behavior

The shared embedded core reserves one generation under its existing mutex before waiting for a prior drain or validating a new start. Both legacy Start and StartBound use this same core and canonical server.RunWith. A competing call receives ErrAlreadyRunning while startup is pending or a server is running.

Both stop modes retain the stopped generation's completion barrier before releasing its handle. A later start may reserve its own generation, but cannot launch until its predecessor fully drains. Cancelling that waiting start retains the transitive barrier; another restart cannot skip the older teardown. StopNow initiates cancellation without waiting for startup or teardown. Graceful Stop also waits when an earlier StopNow is still draining.

Ready and completion act only on their own generation. A late Ready cannot republish a stopped engine; an older completion cannot clear a successor's reservation. Original boot failure causes remain available through BootError. Existing option validation, configuration/defaults, legacy exports and ABI layouts are retained. The private controlled-runner seam has no global override; production always supplies canonical RunWith.

The original f372 packet remains byte-identical. Its historical sentence saying the original concurrent-start contract was unchanged describes that earlier source delivery. This successor supplies the new reservation/drain behavior. The expected-network contract and its matching-native-export requirement remain unchanged.

## Exact inputs and composition

Apply the Runtime18 base, exact N24 carrier94fd763d459210b496557894628333d466abae73, the seven f372 boot Go files, and then this two-file lifecycle overlay. Check complete hashes and modes before each replacement. The lifecycle implementation replaces f372's embedded.go3b734dd4; the new lifecycle_reservation_test.go must be absent.

The N24 and boot path sets are disjoint. This lifecycle overlay supersedes only boot embedded.go and adds one test file. The full prospective maps are:

| Map | Files | Bytes | SHA256 |
| --- | ---: | ---: | --- |
| Native production |1648|372320|5206276e3071eeac65784c08a6981b5300eb9017b084c0052db0b2afe46dc74e|
| Native qualification |1656|374143|8c263f483b327c76d511b6b5786654f64743df9a300741f0ef8760f25b216c3c|

The SDK production projection remains byte-identical to N24's755-file map. The qualification SDK projection contains756 files. The complete inverse restores both exact N24 maps, then N24's retained inverse restores the1638/SDK750 Runtime18 base. Existing modes are preserved; new boot/lifecycle files have explicitly specified0644 modes. These are prospective source specifications, not filesystem or native-product observations.

See overlay-manifest.json, composition-manifest.json, inverse-manifest.json and maps/ in the carrier. All source inputs, before-images and external carrier references have exact hashes. No original native profile or framework identity is replaced by these source maps.

## Test selection and actual evidence

Seven new lifecycle parents contain six explicit child cases. Six parents exercise the real lifecycle state machine with controlled runners. The seventh calls the real legacy/bound exports concurrently eight times against a fresh managed, account-free, custom-network runtime and checks the real health response. This describes pending test code, not an executed runtime.

The real-export test owns the whole caller cohort. Early failure cannot remove its fixture before every launched caller returns and the final generation drains. A failed fixture is retained. Incomplete custody produces a test failure and abort rather than allowing later tests to inherit an unknown engine.

The exact pending union is17 parents plus16 named children:7 lifecycle parents,6 boot parents and4 affected existing lifecycle parents. TestStartAddressStop appears only once. The four legacy tests retain their original source and standalone fixtures; they are not relabeled as managed controls. Together with N24's9 parents/15 children, the prospective combined union is26 parents/31 children/57 run-and-pass events. The selection does not replay unchanged migration, network, ACL or P2P evidence.

Two actual final gofmt stdin commands exited0 and left both inputs unchanged. The original stdout is retained verbatim. These commands invoked no compiler, native server or test and wrote no project file. The prior source/formatter evidence and the closed early-cleanup source finding remain preserved.

## W3 delivery

W3 owns the coherent materialized native source, generated headers/ABI, version/profile updates, Apple products, final integration and release. It should compose the exact N24 and boot sources with this successor before producing the native product that W2's consumers require. The old8ac framework lacks bound-start exports and cannot qualify those consumers.

The host-visible Swift changes remain the three exact files in f372; this successor changes no Swift application or other lane's app. No extra public ABI export is introduced here. A Linux wrapper/core test cannot qualify a generated Apple ABI.

Pending: exact physical source/toolchain/resource admission, selected native execution, matching Apple compile and lifecycle method, application mounting/account/Space behavior and release acceptance. Existing capacity gates and accepted historical evidence remain unchanged.
