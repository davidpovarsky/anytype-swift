# r15 Apple attempt 44235484816 — observed offline module-cache failure

The original GitHub artifact 14398630009 is preserved byte-for-byte. Its outer ZIP is 119,760 bytes with SHA-256 `3b2b74ed086acc94f45e684d297cfd77a33d7c3009f65941fe5872ce76ae8c01`. The run source is `793d09a8d3e22c3ce29cc94e16c614f476cb73d8`; GitHub records failure at 2026-11-18T04:26:23Z.

The preserved `gomobile-preparation.json` confirms the previous init/latest blocker was passed. Both pinned tool builds completed. The original `gomobile-bind.log` then records `go mod tidy` failing because `dmitri.shuralyov.com/gpu/mtl@v0.0.0-20221208032759-85de2813cf6b` was absent with GOPROXY=off. The three generated-module launcher receipts confirm return code 1 for the iOS arm64 and simulator arm64/amd64 tidies. No verified framework artifact was produced; the runtime receipt records zero native invocations, AppGetVersion NOT_RUN_BUILD_ONLY, and Swift pairing NOT_RUN.

The original native resolved-module list had selected/cached the older 2019 MTL revision. The newer version is already required by the pinned mobile tool's Shiny module; exact upstream go.mod/go.sum files and blob/hash provenance are in `dependency-source/`. They establish the declared transitive version and both checksums without changing a Heart or gomobile pin.

`raw-manifest.json` hashes every original artifact member, including the inner ZIP. `run-metadata.json` and `artifact-metadata.json` are API metadata. Files under `github-artifact/`, `dependency-source/`, and ZIP files have scoped Git attributes preserving their original bytes.

The associated source fix prepares an owned copy of the pinned tool's full dependency declarations before offline bind. Its controller checks and Windows Go module-cache experiment are separate evidence directories; neither is an Apple runtime PASS. Product enablement stays disabled.
