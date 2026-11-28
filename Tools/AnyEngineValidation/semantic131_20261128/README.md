# Semantic verification of the frozen 131-file source graph

This package retains the exact controls, source inputs, reviews, observations and failures for a separate Linux Swift semantic workload. It changes no application or production source.

The immutable parent is foundation evidence commit `c85f8950c3b7b5d2234edaf992b185688ff9fad1`. Its graph at `Tools/AnyEngineValidation/direct_capture_producer_20261128/qualification/SOURCE_GRAPH.json` is Git blob `46476f8b9f48801029d327a84b1c322350aeb5d3`, SHA256 `748a0eb40a29a79198bbc396e7fb03061f7be1988a0259b670a76aeeeddb3597`.

## What this workload can establish

The declared workload covers 127 production files and four complete test files: 131 files / 1,652,921 bytes. It requests six full-body typechecks and five fresh project-module emissions in eleven serial frontend phases. The project graph keeps Core → Kit, the independent Engine module, Integration importing Kit and Engine, then Host importing Engine and Integration. The final test module imports Engine, Integration and Host. Exact existing Crypto and CryptoBoringWrapper imports remain subject to the unchanged C3 qualification before and after the work.

No test method executes. All twenty selected component methods remain unrun. A successful semantic workload would not establish a full component build, object generation, linking, Native97, Swift23, Apple ABI, application behavior, or current whole-App graph equality. The later distinct Ordinary14 source graph is not part of these 131 inputs.

## Retained attempts and the planned successor

| Stage | Exact source | Observed result |
|---|---|---|
| Initial proposal before bounded census corrections | `f6bfb4374dc57a08a867f11442cb6a6094b36c7c` | Python syntax observation only; this controller was never executed. |
| Attempt 1 | `204629a9f0574d39858c68af73d1f73430d04792` / SHA256 `67dab64dd60c571ee4960e06a9eb0b01828042425cf9624259a58b162ba57f6e` | Actual FAIL in the first Core frontend: unable to load the standard library for the target. Zero full typechecks or module emissions completed. |
| Attempt 2 | `a86988c323fd7f73ae653ca5214c0792dc07f06f` / SHA256 `750948d684b813693bfcd61c13a9a37348cae18135a65194686a5b0dc96b7bca` | Actual resource-monitor FAIL during the first frontend. No full typecheck or module emission completed. The primary and fallback terminal are unqualified; source peers and Python AST acceptance remain separate. |
| Attempt 3 candidate | `a50ce7798b1c89be7e155bc3730efb41f174423f` / SHA256 `62a741066bff092cf753c79c79c05a6722703de2a5b62f11e82898899ba8c80d` | Independent N source review is clear and the exact controller has an actual Python AST-only PASS. Its runtime is still planned at this publication snapshot; no staging, import, execution, typecheck, module, test or native acceptance is claimed here. |

Attempt 1's frontend exited 1 normally with positive group absence and no signals, forced cleanup or cleanup errors. Its complete source and original C3 final checks passed. The original receipt, 241-byte log and terminal stdout are retained unchanged under `actual/attempt1`.

The failure archive contains 241 members and has a complete recorded streaming inverse. The later durable copy preserved the exact 1,805,742-byte gzip, 61,564-byte manifest, 63,686-byte failure receipt and 241-byte log on DEV. It did not delete the originals or rerun a semantic phase. The first copy refused an inherited setgid directory mode; both that refusal and the narrowly corrected construction of a new private directory remain in `actual/attempt1-custody`. The physical artifact index gives exact hashes and locations without adding compiler archives to the Git repository.

Attempt 2's coordinator subsequently observed a Clang PCM lock symlink inside its private cache. The existing monitor rejected it before following it; the owned frontend was terminated with signal 15, exited -15 and was positively absent afterward. The original phase log was empty. This is a forced cleanup on a resource-monitor refusal, not a normal compiler diagnostic result. The unqualified primary and fallback terminal must not be treated as acceptance or as proof that final source/C3/archive checks succeeded.

The exact attempt 2 raw primary, phase closure, fallback terminal, NOFOLLOW census and staging/release are retained under `actual/attempt2*`. The three final source/C3/system-module audit flags are FALSE because the guard prevented those checks; no later byte-preservation operation promotes them. The separate durable custody retains all 247 regular members (9,758,684 bytes), 28 directory metadata rows and one exact link record, with a full regular-byte streaming inverse. It neither follows nor recreates the link and leaves the originals in place. Directory/link read access times may advance, as stated in its raw receipt. No physical restoration or semantic acceptance is claimed.

## Loader correction and scope

The first controller's `-disable-implicit-swift-modules` option was broader than its intended policy. The fixed Swift 6.4.3 source shows that it disables ordinary serialized-module discovery as well as textual Swift-module loading, and also disables implicit Clang modules. The installed default resource paths and binary Swift modules were later observed present; a missing default resource path was not established.

Attempt 2 replaces that option with `-module-load-mode only-serialized`. The fixed-release loader source establishes the intended separation: ordinary serialized Swift modules remain discoverable, textual Swift interface loading is omitted, and the previously declared bounded fresh Clang PCM cache remains available. The installed exact frontend accepted this option/value in a source-free `-print-target-info` observation. That observation alone does not prove imports or typechecking succeed.

The correction also admits exactly 24 installed binary Swift modules, totaling 38,729,276 bytes. Their full original observation is retained as raw JSON so integer nanosecond metadata is not regenerated through a floating-point intermediary. Before and after the compiler, every admitted file must retain its bytes, mode, inode, ownership, link count, size, modification time and change time. Only cross-time access-time differences are permitted for these exact 24 inputs and the existing exact frontend executable. Per-read descriptor stability remains strict, and access-time differences are reported without attributing shared changes to the job.

This finite set is not a complete system-header or SDK closure. Four observed interface-only Testing modules are not admitted as binary dependencies, and no textual fallback is requested. Missing or incompatible dependencies must fail. New project modules must come from this exact source cohort.

## Planned private-cache lock correction

Attempt 3 is a separate immutable source candidate. It adds exactly `-Xcc -Xclang -Xcc -fno-implicit-modules-use-lock` to each existing frontend command, changes only the owned prepared/output names to attempt 3, and admits the exact failed attempt2 record as historical evidence.

The fixed LLVM release source resolves `swift-6.4.3-RELEASE` to `fb5f84d903a3b4e7aea15cd5666598a46f56c833`. Its negative cc1 option sets `BuildingImplicitModuleUsesLock=false`, choosing the same module compilation/AST-read implementation without its duplicate-work lock wrapper. The ordinary Swift `-Xcc` path constructs Clang driver arguments, so explicit `-Xclang` forwarding is required. This source trace does not independently reproduce the installed compiler binary or prove installed cc1 option parsing.

The candidate applies only to a freshly owned nonaliased cache under the exclusive attempt 3 namespace. It retains one frontend at a time and positive closure before another phase starts. It does not permit shared-cache lock suppression, symlinks, hard links, alternate final artifacts or extra compiler descendants. The complete namespace, original-input, 24-module, C3/process-owner, resource and finalizer bodies remain unchanged. Its first genuine typecheck, if separately released, still has to establish installed behavior. No source-free target-info result is used for that claim.

The source-free Python observation parsed the exact attempt 3 controller into 15,019 AST nodes, with zero controller imports or executions and zero compiler/native invocations. N's later source peer checked all seven edits, all eleven phase rows and the exact failed-attempt-2 admission. These later observations are retained separately; the original review specification continues to show its earlier pending state. A compiler launch still requires Root's separate current staging, source and resource admission.

## Unchanged resource and ownership policy

All declared output stays in the exclusive owned `/run` tmpfs namespace. The whole prepared-plus-output allocation cap is 256 MiB, with at least a separate 512 MiB tmpfs reserve at admission. The original main/final/outer deadlines remain 900/120/1,080 seconds. One frontend runs at a time; each has CPU 120-second / wall 180-second limits, a hard 2 GiB address-space limit, and core dumps disabled. Current owned-group RSS is sampled against a 1 GiB ceiling; initial/live memory gates remain 3 GiB/1 GiB. Sampled allocation and RSS observations are not a filesystem quota or an unobserved peak guarantee.

This separate semantic workload monitors ROOT at 1 GiB and DEV at 512 MiB. It does not lower or replace the held full-build C20, Native97 or Swift23 resource gates. No global read-only mount or global filesystem-write prohibition is claimed.

The exact f9 process owner is retained. Current child ownership is established with waitid/WNOWAIT before PID/group sampling. Namespace enumeration is bounded during collection. Final artifact membership remains strict; original errors, interrupted work and partial outputs are retained. A failed final audit or terminal persistence check cannot yield an accepted primary receipt. There is no automatic retry or output deletion.

## Evidence structure

- `sources/attempt1`, `sources/attempt2` and the planned `sources/attempt3` contain immutable controls, exact raw source packets and the review specs as they existed at their source freezes.
- `historical` preserves the earlier unrun source and the bounded census/ownership correction.
- `reviews` keeps the independent Root and N source peers and the fixed-release loader-policy peer.
- `observations` and `observers` preserve complete returned text and exact observer source. Capability, Python AST and semantic outcomes stay separate.
- `dependencies` contains the frozen graph and unchanged C3/process-owner helper sources.
- `actual` preserves raw attempt and custody results without editing old statuses or normalizing raw metadata.

The manifest lists every new payload's Git blob, full SHA256 and byte count. The publication proof checks all whole bodies and the complete parent-tree inverse. The only added repository prefix is `Tools/AnyEngineValidation/semantic131_20261128`.
