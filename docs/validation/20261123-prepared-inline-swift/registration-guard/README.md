# Explicit live HTTP acceptance registration

The environment-dependent HTTP XCTest is now enclosed by PINKHA_PREPARED_INLINE_HTTP_ACCEPTANCE. Its complete previously compiled body is byte-identical to commit 2993ecb04a8f7347398479c6fe03d04e69d9902d. The public client and all twelve qualified portable methods are unchanged.

Actual Swift 6.4.3 compilation and test discovery passed in both modes. The default invocation listed no live HTTP method. The explicit flag invocation listed exactly the intended live method. Neither invocation executed a product test. All 1,461 module Swift source and manifest inputs remained identical during discovery.

Both original failed audit attempts are preserved. The first Sentinel call used a 30-second transport timeout; the remote default compilation/listing nevertheless completed with exit zero before its later output encountered the closed pipe. The second opt-in compile/list completed with exit zero, but the post-build audit looked for an obsolete .xctest product layout. The installed Swift 6.4 SwiftBuild backend instead reports a test runner executable and test shared library. The final qualification reuses both original successful listings, verifies complete source equality, and binds the actual files reported by swift build --show-bin-path. No compilation or product test was repeated to repair these audit steps.

qualified-registration.json contains the source, command, original log and actual runner/library hashes. The earlier AUDIT.json remains the original commit-2993 receipt and has not been relabeled or overwritten. Its unguarded HTTP source digest is historical. This new receipt binds the two guard lines and identical body separately.

The live native HTTP test remains unexecuted at this checkpoint. Its future execution must use the explicit flag, the already-built frozen products, one exact method selector, a fresh nonce-bound native handshake and independent native verification. Apple, device, network and full migration qualification remain separate.
