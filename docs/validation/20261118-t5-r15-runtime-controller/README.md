# r15 Apple runtime controller handoff

Nine Python control tests and 15 subcases passed on Windows with zero skips. Source AST and workflow YAML parse passed. The existing r14 builder remains unchanged, LF SHA-256 0ebbe2f6227418eac2c532b0058290158319ba9f786baaf445de444887e8c669. No Apple framework or native test was built/executed by this local validation. Apple build, actual AppGetVersion and Swift pairing are NOT_RUN.

The new isolated reusable workflow requires exact source947 r15 patch/inventory, native Heart d98420b, Go1.26.5 ARM64 macOS and Xcode27. It verifies the effective genproto version and both h1 checksums in the native graph and all three generated gobind module builds, and binds the full runtime and Heart markers to all three original device/simulator binary slices. Original generated go.mod text/hashes and explicit launcher scopes are retained; no native source/go.mod or gomobile implementation is changed.

The pending actual-account/export run 44221823767 was still executing on published integration 9f600ac63041543b1093a2aea34fb6529c4e6fa3 at this validation milestone. Its original status snapshot is retained without claiming a native pass.

The parent dispatcher and all r14/Startup/UI files are unchanged. A successful later runtime build must still be reported as build-only, with zero native application test invocations, product flag OFF, and full F10 NOT_PROVEN.
