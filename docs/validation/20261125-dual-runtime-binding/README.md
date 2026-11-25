# One Go runtime: actual binding generation and Apple producer

The original shipping Heart app and the separate NativeApp currently link independent Go runtimes. The combined producer selects one gomobile build with Heart service/core and Any's existing typed mobile bridge; it preserves the original Heart exports and adds MobileStartWithResult, MobileStop and MobileVersion.

The source contract binds Heart ea796999d648e27dcb7ad23a0bbd849d35fadc5a, all 154 reviewed Page154 source paths, capture bridge 7796b2a4c8e7d80aae82606ca0bcb83acf84506d, Any cf87c43ff0100c2dc43c3c105c82b1b070b3a7a3 and SDK e195f6c07a053c6588e39ffe72ee4fc44cf3d953. Page154 and the 49 existing C source changes have no overlapping paths. Source manifest SHA256 is 24a2cd5c557c6309e8db8a738e9e7bc72fdfccad340c9128f9b8cba082345599 and verifies 4267 files.

Actual Oracle Go1.27.4 module resolution succeeded. Actual gobind Objective-C generation then exited zero after 342 seconds with no stderr and generated the retained headers. Both source-capture exports and ServicePinkhaSemanticAnchorCapture appear alongside the original Heart API and Any Mobile API.

These facts qualify the module graph and public binding generation only. They do not qualify a linked Apple library, real source capture, two-engine app lifecycle, migration, native runtime acceptance, signed Archive or TestFlight.

The Apple producer builds arm64 device and simulator slices from this exact source, verifies required symbols, preserves original logs and source/byte receipts, and explicitly records zero acceptance tests. It stamps a new combined runtime identity. Existing semantic/T2 profiles must be bound to this reviewed identity when the produced library is consumed; the producer does not impersonate an older qualified binary.

The frozen source archive remains on the authorized Oracle evidence store. Raw user content, accounts, signing keys and credentials are not part of the archive. Native capture keeps permitsDestinationWrites=false until its independent semantic acceptance is satisfied.
