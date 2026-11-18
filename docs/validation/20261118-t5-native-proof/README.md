# T5 native proof: first actual CI attempt and Linux dependency correction

The native-index attempt [44203267311](https://github.com/davidpovarsky/anytype-swift/actions/runs/44203267311) ran control source `b5dc53b799a70269b8082734106d8cd30a99fc44`, immutable proof source `947fbde24d5657d0e1229f45bb3993648884a8a1`, and Heart `d98420b1113536afd08cde6de9a5816f6d27ffff`.

## Observed result

**INFRA_FAILURE_BEFORE_NATIVE_TESTS: zero native tests executed.** The five Python CI-controller tests passed. The source preflight returned `SOURCE_VERIFIED_BUILD_NOT_RUN`, with approved r15 patch SHA-256 `5a0906158569d47642d9fc978932cdf254550a31c864a1fb34bd1f8e4e7c10f2`. Downloading the requested Tantivy Linux dependency then returned HTTP 404. This run is neither native functional acceptance nor a demonstrated native functional regression.

The complete small CI artifact is retained in `44203267311-native-index/artifact.zip`, together with its extracted source-preflight and CI result. Artifact ID: `14380834850`; SHA-256: `2840b77500c07db0819e559c47950f38abeb2bf9ddec232b4d7f7bf2ddabe69c`. The record in `attempt.json` identifies the run, immutable sources, exact asset, and counts.

## Concrete correction

The driver requested `linux-amd64.tar.gz`, absent from the official pinned release. [Tantivy v1.0.6](https://github.com/anyproto/tantivy-go/releases/tag/v1.0.6) publishes `linux-amd64-musl.tar.gz` with SHA-256 `88b34e006707bfec2d29e8b26405f67cbb975d06fd4ea164da856d0084aaabbc`. The pinned Heart checksum file specifies this same asset and hash. The driver now requests that asset and passes its real extracted directory.

Pinned upstream [Heart Linux build rules](https://github.com/anyproto/anytype-heart/blob/d98420b1113536afd08cde6de9a5816f6d27ffff/makefiles/ci-cross-compile-library.mk) and [Tantivy build rules](https://github.com/anyproto/tantivy-go/blob/v1.0.6/Makefile) use a musl C compiler and static linkage. The Linux proof job now installs `musl-tools`, records its compiler/package versions, and sets `CC=musl-gcc`, `GOFLAGS=-ldflags=-extldflags=-static`, and `GOTOOLCHAIN=local`.

No dependency revision, checksum pin, Heart source, approved patch, native fixture, expected test count, or native assertion changed. The five existing controller tests passed after the correction; source whitespace validation passed. The corrected native run remains pending at this checkpoint. Client enablement stays disabled pending real runtime, reopen, and old/new compatibility evidence.

## Second actual attempt: linker requirement exposed

Run [44205201082](https://github.com/davidpovarsky/anytype-swift/actions/runs/44205201082), control `7a636325350cad48409621fec4ec616701ba768a`, successfully downloaded and verified the unchanged Tantivy archive. It reached the real native test link, then failed because the archive uses `qsort_r`, absent from Ubuntu 22.04's musl 1.2.2. No native test ran: actual package/top-level/subcase pass counts are all zero. This is a build/link failure, not a T5 assertion result.

The [musl maintainer's 1.2.3 announcement](https://www.openwall.com/lists/musl/2022/04/07/1) identifies the introduction of `qsort_r`. [Ubuntu 24.04 provides musl-tools 1.2.4-2](https://packages.ubuntu.com/noble/musl-tools), while [22.04 provides 1.2.2-4](https://packages.ubuntu.com/jammy/musl-tools). The job therefore moves to Ubuntu 24.04, records the actual toolchain, and links/runs a small static qsort_r probe before compiling the native test. The dependency cache key distinguishes the toolchain. The asset/hash, native source, patch, fixtures and test assertions remain unchanged.

The complete second artifact and extracted receipts/logs are retained in `44205201082-native-index`; its immutable GitHub digest is `b7647ac6d8ad7c78a89c4ac1ce2d732fb642070b83897059b10797da47b47977` (artifact `14383123966`). Corrected native execution remains pending at this checkpoint.

## Third actual attempt: complete C/unwind runtime required

Run [44206578182](https://github.com/davidpovarsky/anytype-swift/actions/runs/44206578182), control `e501746752fb4826eed59366fff3cfe3ea82ec5d`, passed the qsort_r link/run probe on recorded musl 1.2.4. The full native test link then exposed a different issue: the Ubuntu musl wrapper linked GCC13's glibc unwind archive, which references `_dl_find_object`. Zero native tests executed. The exact artifact `14383657999` is retained with SHA-256 `dc722168176cf2ded71014f1f257c1bd758d7823eea806faa411894120ac159d`.

The corrected job runs the unchanged proof inside official `golang:1.26.5-alpine`, pinned to the linux/amd64 manifest `sha256:111d79159b2326f7e80c4a4706e1ba166acb0e2611df853955f3621828cd49e8`. Docker Hub metadata is retained in `official-go-image.json`. The Go version and musl compiler target are checked before the component; package/compiler/image metadata are retained. Both the control and immutable fixture checkout are mounted read-only. Only the CI job's disposable Heart, proof and compiled-cache paths are writable. Two CPUs, 6 GiB memory and 512 process IDs bound the container; the existing component test deadline remains unchanged. The source, patches, Tantivy checksum and native test assertions do not change.

Local validation of the correction: YAML parse, shell syntax, existing five CI-controller tests and source whitespace passed. Actual corrected native execution remains pending at this checkpoint.
