# T5 native proof: first actual CI attempt and Linux dependency correction

The native-index attempt [44203267311](https://github.com/davidpovarsky/anytype-swift/actions/runs/44203267311) ran control source `b5dc53b799a70269b8082734106d8cd30a99fc44`, immutable proof source `947fbde24d5657d0e1229f45bb3993648884a8a1`, and Heart `d98420b1113536afd08cde6de9a5816f6d27ffff`.

## Observed result

**INFRA_FAILURE_BEFORE_NATIVE_TESTS: zero native tests executed.** The five Python CI-controller tests passed. The source preflight returned `SOURCE_VERIFIED_BUILD_NOT_RUN`, with approved r15 patch SHA-256 `5a0906158569d47642d9fc978932cdf254550a31c864a1fb34bd1f8e4e7c10f2`. Downloading the requested Tantivy Linux dependency then returned HTTP 404. This run is neither native functional acceptance nor a demonstrated native functional regression.

The complete small CI artifact is retained in `44203267311-native-index/artifact.zip`, together with its extracted source-preflight and CI result. Artifact ID: `14380834850`; SHA-256: `2840b77500c07db0819e559c47950f38abeb2bf9ddec232b4d7f7bf2ddabe69c`. The record in `attempt.json` identifies the run, immutable sources, exact asset, and counts.

## Concrete correction

The driver requested `linux-amd64.tar.gz`, absent from the official pinned release. [Tantivy v1.0.6](https://github.com/anyproto/tantivy-go/releases/tag/v1.0.6) publishes `linux-amd64-musl.tar.gz` with SHA-256 `88b34e006707bfec2d29e8b26405f67cbb975d06fd4ea164da856d0084aaabbc`. The pinned Heart checksum file specifies this same asset and hash. The driver now requests that asset and passes its real extracted directory.

Pinned upstream [Heart Linux build rules](https://github.com/anyproto/anytype-heart/blob/d98420b1113536afd08cde6de9a5816f6d27ffff/makefiles/ci-cross-compile-library.mk) and [Tantivy build rules](https://github.com/anyproto/tantivy-go/blob/v1.0.6/Makefile) use a musl C compiler and static linkage. The Linux proof job now installs `musl-tools`, records its compiler/package versions, and sets `CC=musl-gcc`, `GOFLAGS=-ldflags=-extldflags=-static`, and `GOTOOLCHAIN=local`.

No dependency revision, checksum pin, Heart source, approved patch, native fixture, expected test count, or native assertion changed. The five existing controller tests passed after the correction; source whitespace validation passed. The corrected native run remains pending at this checkpoint. Client enablement stays disabled pending real runtime, reopen, and old/new compatibility evidence.
