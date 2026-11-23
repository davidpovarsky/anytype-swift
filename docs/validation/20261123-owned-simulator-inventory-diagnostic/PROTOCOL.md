# One owned simulator post-boot inventory diagnostic

## Status and authorization

This is a new source-only diagnostic candidate. No simulator command, product build, product method, CI dispatch, or diagnostic execution was performed during authoring. Root owns review, integration, activation and execution. The SDK donor 226934b0d3b324056116fb71495a0a60d9d6a6d7 and all existing current-Apple files remain unchanged.

## Concrete question

The independently qualified NativeUI run45264357685/1 at56b4caafae1c0898b483717abed495f2e3b9281b completed bootstatus with exit0, then its exact-owned-UUID inventory timed out after30seconds. Its cleanup inventory also timed out. The original group records establish final ESRCH; they do not identify pre-signal group members or prove that a service descendant was killed.

Current Commands.run starts a new session for every command and calls the qualified TERM/KILL helper even after successful exit. SDK's inner build_custom_heart.command uses ordinary Popen and does not terminate a per-command group. That source difference is concrete. It is not a demonstrated cause of the post-boot timeout.

The new diagnostic retains the current per-command session and signal policy. It adds exact signal-call outcomes and bounded process snapshots immediately before and after cleanup of boot, bootstatus and the inventory observations. Observation itself adds time; it is explicitly marked in each command record. There is no claim that a sampled process table proves complete ancestry, service health, or causation.

## Fixed scope

One new simulator only:
- runtime com.apple.CoreSimulator.SimRuntime.iOS-27-0, version27.0, build24A434;
- installed device type com.apple.CoreSimulator.SimDeviceType.iPad-Pro-13-inch-M5-16GB;
- arm64 compatibility must appear in the actual runtime support matrix and type bounds;
- Xcode developer directory /Applications/Xcode_27.app/Contents/Developer;
- fresh exact run/attempt name and UUID, with baseline, creation intent and original creation log.

The original post-boot inventory command has exactly30seconds. Only its exact TimeoutExpired, after the owned command group has a timely ESRCH observation, permits one further read-only invocation of the same UUID query with120seconds. This is a separately named diagnostic observation. Its success never changes the original30second outcome or permits product work. There are no query loops or automatic repeats. Repeating this read-only inventory after the first process has been reaped does not create, modify or delete a device.

No App/native/UI build, project generator, product test, product installation, artifact download, provider or native library work exists in this program. xcodebuild is used only with -version. The workflow uses an already installed ARM64 Python3.12 and refuses if none is found; it does not install a runtime.

## Ownership and first error

Each diagnostic child gets start_new_session=True, merged stdout/stderr in an exclusive original regular log, original argv/cwd, a durable start record, the current TERM/KILL sequence, and the unchanged exact kernel ESRCH helper. The signal wrapper only records the same killpg call's returned result or exception and rethrows the same exception. No service PID from a process snapshot is signaled.

The exact newly created UUID is captured before later callback/group failure. The controller retains memory ownership even if the journal write itself fails. Independent cleanup admits the preserved intent, fresh UUID, exact create argv/context, start record and original create-log bytes. A creation attempt with no provable UUID is INCOMPLETE, never NOT_CREATED.

The original qualified60second shutdown/delete function is copied literally. Its existing deadline and strict exact-UUID reconciliation are unchanged. Unlike the failing current-Apple outer adapter, this diagnostic does not insert another live inventory before that qualified cleanup. This difference is explicit and local to the diagnostic. It does not repair or change any product controller. COMPLETE under that policy means the exact shutdown/delete commands met its conditions; an independent empty inventory is claimed only if its reconciliation actually ran and passed.

A durable cleanup-start claim prohibits repeated cleanup actions if an earlier invocation was interrupted. Workflow cleanup may recover a journaled UUID if the first controller ended before cleanup started. It reuses an existing terminal cleanup receipt and never repeats a failed cleanup attempt. The original global deadline also applies to the cleanup entrypoint.

The first failure is retained separately from later observation, cleanup, source, capacity and persistence errors. A final-save or signal-restoration failure cannot turn a failed original operation into success. Compact stdout and actual exit remain authoritative if the last durable result could not be written.

## Source and metadata

Only the new run.py is loaded from the repository, under Python -I -B. The script, profile and standalone workflow have fixed SHA256/byte/mode rows. The manifest is additionally bound to the executing Git tree. Exact current SHA, branch, physical Git blobs/modes and actual repository-loaded module origins are checked before and after. Extra repository modules are rejected. The standalone workflow is a fixed source input even when Root copies its job inline into the central dispatcher.

Process snapshots use PID, PPID, PGID, state and comm only; no command arguments or environment dump. The raw bounded outputs remain private evidence. Apple publishes the selected keyword meanings and empty-header syntax in its ps manual source:
https://github.com/apple-oss-distributions/adv_cmds/blob/main/ps/ps.1
Relevant source sections: -o; KEYWORDS comm, pid, ppid, pgid, state/stat. This is syntax documentation, not a proof of the actual runner's process state.

## Resource profile and its limits

The global controller deadline is1200seconds with240seconds reserved from normal commands for cleanup and final source checks. The workflow has a22minute diagnostic step, a3minute cleanup step and a30minute job limit. Every child has a fixed command timeout; TERM/KILL waits remain5+5seconds and the exact kernel check has its own10second bound.

The profile admits at least1GiB free disk and stops on sampled evidence usage above8MiB logical or allocated bytes, including directories. It admits at most56 command log files and512 evidence entries, with256KiB per log/record and128KiB reserved for final records. Regular-file output is retained to preserve the existing command I/O topology. Size checks occur at100ms waits and at finalization. These are sampled stop limits, not hard filesystem quotas: a producer can overshoot between observations. Such a limit failure stays an actual diagnostic failure; no output is truncated or normalized. No RLIMIT or environment change is propagated to simulator descendants.

Only one finite list of12 or fewer already installed Python candidates can be checked by the workflow setup step, under its2minute limit. No container, remote command or package installation is involved.

## Routing

The standalone workflow and data-only INLINE-central-packet.json are additive. The packet adds one route choice and one inline job. It does not add a reusable workflow reference, edit the central file, or dispatch anything. Root composes it with current central routes and any SDK current-controller row.

## Acceptance boundary

This diagnostic can qualify its own observations, provenance and cleanup. It cannot award application acceptance, turn an earlier timeout into a pass, or establish a causal service failure merely from temporal correlation. No historical control or product method is selected.
