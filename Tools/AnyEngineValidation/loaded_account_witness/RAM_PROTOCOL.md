# Separate RAM-cache source-query profile

This is a new, opt-in source-enumeration profile. The original graph.py (SHA-256 6aacb0c911aed49d88d9f0e7ef82b08a5ceab431139bb7b71f17c7d0aedfd23d), its 2.65/2.60/2.50 GB resource limits, and the native 2.95/2.60/2.50 GB limits remain unchanged. No native build or test method is authorized by this profile.

The original direct launch refused before graph startup. Its subsequent finite 120-second resource window completed NOT_RUN with launch_count=0; result SHA-256 410cb924fca4cef40d4ed806b83f4fe0caee9372430eb4366b2d952e977b9d21. No source query, container, build or test occurred in either path. The new profile does not relabel those outcomes.

## Exact computation

Heart24dc6393b30e6d1d80ec28ff624060af9bb4327a, tracked any-sync c005bd6cde8d8f8a6007c35f06894f3d89f9f07c, Go1.26.5, the fixed ARM64 musl image, candidate.mod/sum, feature and acceptance tags, and Tantivy inputs remain exact. The sole Go argv is list -deps -test -json with the fixed modfile and ./core/application. There is no export, compiled, build, test execution, download or module mutation.

Original sources, toolchain, module cache and Tantivy are mounted read-only at their existing paths. GOMODCACHE stays explicit; changing GOPATH cannot redirect it. The original go-build cache is not mounted. Cache-derived stale/build-ID observations are not used as source identity.

## New resource admission

The source query alone uses disk start >= 1 GiB + 16 MiB and active/final >= 1 GiB. MemAvailable must be >= 4 GiB at start and >= 2 GiB during/after the query. The existing one-CPU, six-GiB container and three-GiB Go memory limit remain. Query time is 120 seconds; stdout is bounded to 8 MiB, stderr to 1 MiB, and all controller-owned durable attempt evidence to 16 MiB. Docker logging is disabled for this container; only the bounded parent pipe collector retains query output. Ordinary small Docker control metadata is recorded through the fixed identity receipts, not treated as a compiler cache or a claim of zero disk activity.

A fresh, fixed-name host tmpfs under /dev/shm has a hard 64 MiB limit and 8192 inode limit, mode0700, uid/gid1001, and nodev/nosuid/noexec. The original ancestor identity, newly created mountpoint inode, mount ID, device, source label, flags, effective limits and private owner are checked. Only its go-cache, gopath and tmp subdirectories are writable by Go; the durable attempt path is read-only inside the container. No other host mount or directory is changed.

## Custody and cleanup

The exact generated test-main exception remains limited to the application.test main package, GoFiles, a content-addressed two-hex/64-hex-d cache path, and <=128 KiB with the expected generated header and content hash. Its actual RAM path and complete original tuple are retained. Verbatim bytes are separately written, fsynced and read back into the durable attempt before mount cleanup. This is ephemeral source-graph provenance; it does not claim that a later native build consumes that same physical cache path.

After the exact owned container and launcher group are stopped, the program independently rechecks the container identity before reading RAM. All remaining regular files and directories are inventoried with type, mode, owner, size, nanosecond metadata and content hashes. Cache entries remain opaque cache data and are never admitted as compiled-product evidence. Unexpected scratch or executable/archive signatures are recorded and retain the mount with an overall failure.

A complete bounded tar.gz of RAM contents is written within the remaining evidence budget (at most5 MiB), fsynced, and streamed back to compare every member's type/mode/owner/size/hash, complete membership and gzip trailer. The original RAM inventory must remain unchanged. Only then can a normal, exact-path umount occur, followed by removal of the same original empty mountpoint inode. There is no forced/lazy unmount, recursive deletion or cache eviction.

If preservation cannot fit, unknown filesystem objects appear, a container may still be live, or any readback/identity check fails, the original query error remains primary and the RAM mount is retained. Partial preservation files and distinct cleanup errors remain original evidence. A source-query PASS requires successful source integrity, memory/disk final admission, and complete preservation/cleanup; named native test counts remain zero.

## Review and execution

The exact new program has a literal inverse to the untouched original graph source. All native/fork/controller source snapshots and actual loaded repository Python sources are bound before/after. No repository imports are introduced: tarfile and all other imports are Python stdlib.

This source freeze is unexecuted. Parent and SDK source review precede the single actual source query. No automatic retry, cache-size expansion, module-pin repair or native compilation follows a failure.
