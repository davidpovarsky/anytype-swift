# Offline pinned Apple bind controls

The actual first r15 build failed because upstream gomobile init requested gobind@latest with GOPROXY=off. The fix uses the already built and source-verified pinned gobind, creates only a fresh owned Apple GOPATH/pkg/gomobile, and explicitly preserves the original GOMODCACHE.

The full runtime controls passed: source/module/slice guards plus real filesystem checks for the selected tool hash/path, offline module resolution, original module cache and refusal to reuse/delete an existing workspace. This is build-input validation, not an Apple compilation or native runtime test. The original r14 helper hash is unchanged.
