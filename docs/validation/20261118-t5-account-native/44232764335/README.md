# Actual native account compatibility PASS44232764335

Run44232764335 on source d0080642d08311a953b87868103772b1379a090b completed successfully. Original GitHub evidence artifact14395379724 (286048 bytes, SHA-256 eb69525058b74c8803ce82ff0a2be27f5d5e2451ab1efffe84882fc7e86ca7a6) and every extracted file are preserved unchanged. The separate170 MB binary archive was not downloaded; its identities remain in the original build receipts.

Two actual Linux native binaries execute four passing TestT5AccountCompatibilityPairPhase invocations with distinct processes8994,9034,9060,9081 and distinct nonces: r14 old-create, r15 new-upgrade, r14 old-edit, r15 new-recover. The exact original account/Space/state and canonical/public/block hashes survive all phases. The old-client Page title edit is retained on the final r15 reopen. The original Note title baseline is correctly empty after native Note layout; it remains unchanged throughout.

The archive contains24 actual native exports:12 JSON and12 Protobuf, three target roles across four phases. All export hashes match their native receipts. Every phase verifies AccountStop(false) and the public not-running postcondition before AppShutdown. r15 executes the private indexed query with three document/block/source-quote targets; r14 retains the original one-member public query. Original native logs each contain exactly one named PASS and no skip/failure. Evidence credential scan is PASS.

This proves the Linux same-account/RPC/export compatibility sequence. It does not prove an Apple packaged runtime, Swift host fallback, visual or physical-device acceptance, Space-wide freshness, or full T5 completion. Product enablement remains disabled.
