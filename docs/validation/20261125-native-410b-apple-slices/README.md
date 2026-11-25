# Native410b actual two-slice build qualification

Both exact 4,855-file source closures passed the original Apple producer on
Xcode27.0 / Go1.27.4: simulator bind224.213s, device bind114.935s. Every native
source and dependency byte was rechecked, all required Heart/Any/capture/semantic
exports were found, each static archive contains exactly one Go runtime, and
the actual generated Swift import surface typechecked for both platforms.
The simulator ran all three unchanged original mobile-gateway methods; the
device reused that same-source actual proof without repeating those methods.

The simulator binary is349,572,792 bytes, SHA48905b7312d7228fe88a60517ec90c1c23d73f2ada762877c05ace9752103342.
The device binary is349,502,520 bytes, SHA cb22fa4733aa2021214f2fc84699ac137cf12cd37c63de0e02585ccd8308925f.
The two original receipts and the independently verified private source/product
retention receipt are preserved here. Complete native sources, binary Products,
input archives and command evidence were copied outside the Mac builds root at
`/Users/m1/development/anytype-d-active-20261125/native410b`; no source was deleted.
The App backup in that separate retention receipt has not yet had its full
inventory replayed and is explicitly not described as qualified by that copy.

The two Swift runtime-profile constants now name410b. Actual XCFramework assembly,
main App compilation, original-app source-capture UI and affected acceptance
remain required. These results are not a physical-device run, full migration,
Release archive or TestFlight delivery. Native ABI signatures did not change.
