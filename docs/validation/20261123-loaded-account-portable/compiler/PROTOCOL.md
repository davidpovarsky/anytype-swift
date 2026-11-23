# C/MIG01 ARM64 compiler producer

Status: source only; no producer execution, native build, or native control has run.
The four loaded-account native methods remain NOT_RUN. The Oracle profile at
1eefb4c9fc02e780d8c178f8d2941a1f96131290 remains BLOCKED_COMPILER_SUPPORT.

## Purpose and source boundary

This additive producer prepares only the missing C/C++ compiler prerequisite on
a fresh GitHub ubuntu-24.04-arm runner. It accepts no source archive, Heart tree,
Go executable, native test selector, user database, or caller-selected image.
Only this controller directory and two fresh output directories are bind-mounted.

The base repository association is the original 1,180-byte image-identity.json
(SHA-256 3fc8c63f8bd3c0b7bc38e762c0388029ef37ceb4f573ec8d87700e5d7d61a2cc).
The immutable layer proof remains byte-identical at native-compiler-support.json
(ca681802575e0fd0d135be251184b89949dde0f46a957755ff2c019fa5013a76).

The registry index is f2f98726820d0342055351c6e9d36e705f5bfffb3dd53ff556325114b08afb6d.
Its linux/arm64/v8 child is ddc1c45d23db7f0702f5a2727e28f24cbb75746f625c8c5083a190e50cf01740,
and that child's configuration is 31b7df755869f3d5b0a8a87e0f29ea85cac62a522f008681d304e311160d181f.
The actual fresh-runner Docker image ID is recorded separately. The producer
requires the requested repository digest, ARM64/Linux, and all ten exact
uncompressed layer digests. It does not treat an engine image ID as a registry
manifest digest.

A bounded read of the already-bound original layers established Alpine 3.24.4,
apk-tools 3.0.9-r0, and the existing v3.24 main/community HTTPS repositories.
It read no compiler source, package payload, private fixture, or credential.
The initial read's ASCII decoding failure on UTF-8 package metadata was a
read-only inspection failure; the corrected UTF-8 read was distinct.

## Finite sequence

1. Admit actual GitHub run/attempt/ref/HEAD, current clean physical/Git controller
   files, original compiler-absence proof, actual loaded Python source, and host
   tool identities. The workflow checks out github.sha with credentials removed.
2. Pull only the fixed repository digest and bind its actual inspection.
3. Create one labelled acquisition container. Its PostgreSQL entrypoint is
   replaced by the fixed shell script, and the inherited data volume is covered
   by a private 16 MiB tmpfs. No PostgreSQL server starts.
4. Preserve base signing keys, installed-package metadata, repository bytes, and
   actual apk version. Run apk update, recursively fetch gcc/g++/musl-dev/binutils,
   require cached index bytes unchanged across fetch, and run apk verify on every
   acquired APK using the unchanged base trust store.
5. Create one separate installation container with network none. It sees the
   exact acquisition directory read-only, verifies the same APK signatures, and
   installs only those files with apk --no-network add. Preserve original logs
   and before/after package and trust-key bytes.
6. Observe the eight actual compiler/binutils executables, their resolved paths,
   file hashes/metadata, versions, and exact musl target. Observe five compiler
   support executable identities. No C/C++ source is compiled.
7. Commit the stopped installation container to a new image. Require all original
   layers plus exactly one new layer. Save its exact image tar and independently
   read it back completely. Record the actual image ID and archive SHA/size.
8. Stop only exact current labelled containers, require Pid=0/Running=false, and
   independently finish current-source/tool/loaded-source and resource checks.
   Preserve stopped containers and images through artifact upload.

All command Popen objects have their own process group. TERM/KILL cleanup follows
group existence even after the leader exits. The first command error remains
primary; later group/receipt errors are recorded separately. No caller PID or
generic cleanup path is accepted. No daemon restart, prune, retry, or old image
removal occurs.

An original failed install container remains stopped. Only a recorded complete
image tar is claimed to preserve its filesystem; a failed unarchived writable
layer is not claimed retained after GitHub destroys the runner. Raw command
logs, package/index/key originals, phase records and partial archive bytes are
still included in the artifact.

## Resource profile

This producer is separate from the unchanged native execution profile.
It requires 8 GiB free disk and 9 GiB MemAvailable before work, and at least
2,950,000,000 free disk bytes / 1 GiB MemAvailable while active and at final
admission. Each container is limited to 2 GiB memory, 2 GiB total memory+swap,
2 CPU and 128 PIDs. The controller has a 512 MiB soft address-space limit;
its owned host CLI children have a separate 4 GiB virtual-address-space limit.
This allows Go-based Docker CLI virtual reservations without giving the Python
controller an unbounded heap. No native compiler process runs.

Controller deadline: 1,200 seconds; workflow: 30 minutes.
Per-command deadlines: fixed 15/20/30/60/180/240/300-second bounds in source.
Output logical ceiling: 3 GiB; one image tar: 2 GiB; acquired originals: 512 MiB;
installation records: 32 MiB; each command stream: 8 MiB.
The output ceiling is observed by polling, not a filesystem quota. Docker's
image/layer storage is additional; the 8 GiB launch floor leaves room for both.
Exact final resources are recorded after all final audits.

## Artifact and admission

The Actions artifact contains public package/source/tool/image data only.
There are no account keys, native fixtures or private test logs in this producer.
A producer success is named
COMPILER_PRODUCED_REQUIRES_INDEPENDENT_ARTIFACT_ADMISSION. It does not authorize
native execution. Root must first independently bind the actual run/attempt,
source, artifact, image tar, image ID and original package verification records,
then commit a fixed consumer admission. No caller-provided hash override exists.

The future portable consumer must retain the exact native 24dc6393/c005bd6c
source and four selectors; capture true new-host physical origins; preserve
private native logs/fixtures through an appropriate private custody route; and
keep semantic census, file completeness and destination-write authorization
false. That consumer/exporter is a separate source scope.

## Source review, not runtime evidence

Only Python AST/JSON parsing and shell syntax checks are performed before review.
No repository module is imported and no package command, Docker operation,
compiler, Go query or native test runs during this source freeze.
The central dispatcher is unchanged in this commit. A separate two-hunk patch
adds one route option and one reusable-job call; root composes it with other
reviewed routes, preserving every existing job and option.

Primary package-manager documentation was read from the Alpine project's
apk-tools repository: apk-fetch(8), apk-query(8), apk-verify(8), and apk-add(8).
Those documentation bytes explain the used options; the actual base executable
and signed package results, not a documentation version assumption, establish
the producer outcome.
