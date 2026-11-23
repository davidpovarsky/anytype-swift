# Native semantic Page acceptance candidate

This source is a separate 154-path candidate: the exact qualified 139-file Heart patch, the current repaired nine semantic component files, three wire codec files, one byte-service entry and two Page test files. `page-source.json` pins every path and the unchanged native module files. It does not modify the frozen 148-path component route or its source manifest.

The service entry and account helper in `page-native` are exact original copies. The Page fixture retains the original checks with its two cache accesses corrected to the pinned Space.Do API. The helper declaration scan found no collision with the composed native service package. They were not compiled or executed by the earlier wire receipts. The later native compile exposed two fixture cache.Do calls whose generic interface does not match clientspace.Space; those two read-only accesses now use the actual Space.Do method, with the same native object lock.

## Selected behavior

Only `TestSemanticAnchorNativePageCaptureAndWire` and `TestSemanticAnchorNativePageColdReopen` may execute. The controller compiles the actual native service package without running its tests. It then invokes these two methods separately with exact selectors and checks the named Go JSON events.

The first method creates a fresh LocalOnly account and Page, proves refusal without history changes for stale text, stale unselected marks and an unknown authority field, performs the capture, and verifies the complete native block, ordinary native response event and signed stored payload. The second process recovers the same disposable account, proves exact durable readback, rejects the duplicate anchor without history changes, and stops the account. The runtime version contains the complete candidate manifest hash.

This gate does not include public HTTP, Swift/Apple bindings, mounted editor routing, clipboard/split/merge/Undo, concurrent editing or complete account race coverage. App capability remains OFF.

## Profiles

| Profile | Runtime | Pinned native dependency |
| --- | --- | --- |
| `oracle-arm64` | Existing ARM64 Alpine 3.24.4 image `sha256:f2f98726820d0342055351c6e9d36e705f5bfffb3dd53ff556325114b08afb6d`; existing static Go 1.27.4 toolchain mounted read-only | `linux-arm64-musl.tar.gz`, SHA-256 `0a4a9143388977df41a174075ce05cd6aee2821da6425b5b9f9d591fe35d3756` |
| `ci-amd64` | Frozen Go 1.26.5 Alpine image `golang:1.26.5-alpine@sha256:111d79159b2326f7e80c4a4706e1ba166acb0e2611df853955f3621828cd49e8` | `linux-amd64-musl.tar.gz`, SHA-256 `88b34e006707bfec2d29e8b26405f67cbb975d06fd4ea164da856d0084aaabbc` |

The ARM64 profile is a new build/execution scope. It does not replace or extend the original amd64 component results. The profile records the actual Go executable hash, compiler target, Alpine release, Tantivy archive, unchanged go.mod/go.sum and the same pinned genproto replacement and checksums.

The isolated Oracle container uses an overridden shell entrypoint, with no PostgreSQL process, service port, live database mount or image pull. Only the required build packages are installed in that disposable container. Source, cache, build and temporary paths are under `/mnt/development`; compilation uses `GOMAXPROCS=2`, `-p 2`, a 3 GiB Go memory limit and a 6 GiB container limit.

## Controller operation

Use a clean controller commit and a separate clean Heart checkout at `d98420b1113536afd08cde6de9a5816f6d27ffff`. Create an owned run directory with `evidence`, `work`, `private`, `cache/go-mod`, `cache/go-build` and `cache/tmp`, using umask 077. For every command supply the same exact controller SHA and selected profile:

```text
python3 -B Tools/PinkhaSemanticAnchorWire/run_page.py prepare --heart HEART --run RUN --expected-app-sha SHA --profile PROFILE
python3 -B Tools/PinkhaSemanticAnchorWire/run_page.py verify-source --heart HEART --run RUN --expected-app-sha SHA --profile PROFILE
python3 -B Tools/PinkhaSemanticAnchorWire/run_page.py build --heart HEART --run RUN --expected-app-sha SHA --profile PROFILE
python3 -B Tools/PinkhaSemanticAnchorWire/run_page.py execute --heart HEART --run RUN --expected-app-sha SHA --profile PROFILE
```

For build/execution, `PINKHA_PAGE_IMAGE` must equal the profile's pinned image value. Build in the compatible musl container with python3, git and build-base. The Oracle launcher uses the same absolute bind-mount paths for both worktrees and their Git metadata. Dependency downloads occur only during build. Before execution, the launcher disconnects that disposable container from its Docker network and records its empty network map. Set `PINKHA_PAGE_NETWORK_DISABLED=1`; the controller also requires that the actual network namespace contains only loopback.

The two methods use separate owned native processes. Wallet/account state, seeds and raw native stdout remain in the private run directory. The public receipt contains selected method names, source/binary hashes and the sanitized synthetic Page artifacts. Export rejects either known wallet secret; private files, account stores and raw test logs are never copied. A failed phase preserves its private log for a bounded source correction and cannot be mistaken for acceptance.

The controller refuses to overwrite an existing build or execution receipt, and rechecks all 154 source paths and the binary after every successful phase. It never selects any previous component, codec or contract method. No protobuf or schema generation is performed.

The Oracle continuation also sets GOPATH to the owned cache/go-path directory. Go stores its checksum-database state there even when GOMODCACHE is set. The original default-/go cache failure is preserved under docs/validation/20261123-semantic-page-native/attempt1-cache-failure; no native method executed in that attempt.

## Project compiler continuation

The Go 1.27.4 ARM64 attempt reached compilation and failed on the original Tantivy archive LTO section. Profile oracle-arm64-go1265 retains the same image, native source154, archive and module pins, while selecting the project-declared Go 1.26.5. Its official ARM64 archive is 63759990 bytes with SHA-256 fe4789e92b1f33358680864bbe8704289e7bb5fc207d80623c308935bd696d49; set PINKHA_PAGE_GO_ARCHIVE to that verified archive and put its extracted bin directory first in PATH. The controller verifies both archive and executable hashes. No global toolchain is replaced. All failed-attempt receipts remain preserved.

## First Page execution and bounded continuation

Attempt4 compiled and actually ran the capture method. It failed the strict complete-block assertion because unchanged native Base.Diff materializes absent Restrictions as a present empty message. Cold reopen did not run. The original failure, metadata and synthetic before/after protobuf are retained under docs/validation/20261123-semantic-page-native/attempt4-restrictions-presence-failure. The new fixture initializes explicit empty Restrictions exactly as the upstream native text fixtures do; all full-block, opaque-field, marks and durable-readback assertions remain unchanged. This fixture does not prove preservation of raw absent/present-empty message identity for arbitrary preexisting blocks.

For a retry with the same immutable dependency graph, --cache-root accepts a stable absolute task-cache path. Its exact spelling and resolved path are recorded in the profile; use the same value for build and execute. This avoids recompiling unchanged dependencies merely because the attempt directory changes. No validation or dependency checksum is disabled. Native receipt accounting now records actual named run and pass events separately, including a failed phase.

Attempt5 stopped before compilation because original AccountStop wrote account_stop.json into the native checkout cwd during the first failed capture. That owned runtime file is preserved privately; all154 source hashes remain unchanged. The controller now runs each selected native test in its own private runtime directory while build commands retain the native source cwd. Exact source guards remain enabled.
