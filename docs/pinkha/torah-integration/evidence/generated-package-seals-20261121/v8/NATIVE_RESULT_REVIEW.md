# Anytype original framework v8: native result

Run: https://github.com/davidpovarsky/anytype-swift/actions/runs/44946489804

`F=4ba0c82d22948a414aaf70873b69de9771fbd252`; attempt 1; artifact `14724089732`, 4,065,015 bytes, SHA-256 `1a45863adb5c3d45bfcc290536bda759fa3842b25f3888bf14c7b0d1a681243b`. Both outer/inner ZIP CRC checks passed.

## Proven result

- Original 2,238 Swift-input framework build and all 44 dependency pins passed.
- Original 143 controls plus the 20 constrained AnyCrypto controls: 163 executed, 163 passed, zero errors/failures/skips.
- The exact AnyCrypto-only export seal passed real Apple codesign --verify --strict. Original producer bytes/metadata, Info.plist bytes and every non-signature executable byte remained unchanged. Its original signature offset 126896 was preserved; terminal allocation shrank 1152 to 544 bytes; normalized code payload SHA-256 `f26a59ec81d3cbcb8ecf2b68fa0e94ee059dd23a5a5585b3c3c7be454a57d2a9`.
- The mandatory full strict loop then failed on AppTarget. No external consumer build/runtime observations were executed. Editable mount is NOT_EXPOSED; Native editor UI count remains zero. No qualified framework artifact was uploaded.

## All remaining observed packaging failures

The read-only diagnostics executed before the first acceptance stop. Every row below failed the actual native command with exactly `code has no resources but signature indicates they must be present`; these are no longer inferred failures. Their CodeDirectory flags were 0x20002 (ad hoc, linker-signed); Info.plist was unbound, with no resource seal or identity authority. Each executable was a thin ARM64 iOS Simulator dynamic library with its exact @rpath install name and a terminal code-signature allocation.

| Product | Executable bytes | Original signature offset / allocation | Additional unchanged resource closure |
|---|---:|---:|---|
| `AppTarget_-256A0C750C206F_PackageProduct` | 54904 | 54304 / 600 | None |
| `BigInt_175F1397B99A03_PackageProduct` | 509032 | 504912 / 4120 | None |
| `Crypto_17A3B1FFC41E47_PackageProduct` | 102904 | 101952 / 952 | swift-crypto_Crypto.bundle |
| `Factory_32A9B87E1196645F_PackageProduct` | 430760 | 427248 / 3512 | None |
| `NotificationsCore_5AD5AD79262EBF4_PackageProduct` | 252912 | 250768 / 2144 | None |
| `SwiftProtobuf_7CEE9AB92C12BC6B_PackageProduct` | 4974176 | 4935456 / 38720 | SwiftProtobuf_SwiftProtobuf.bundle |

## Concrete follow-up boundary for review

A follow-up may extend the existing owned-export sealing route only to these six exact generated products. It should retain all current controls and the original strict/symbol/consumer/runtime gates. External BigInt, Factory, Crypto and SwiftProtobuf revisions are already in the observed immutable 44-pin set; AppTarget and NotificationsCore belong to the original Modules tree `c8163bff54e6ba631e82ce5475f226989846d341`. The exact source/package/product mapping must be admitted, not a wildcard suffix.

Crypto and SwiftProtobuf include pre-signed privacy resource bundles. Their complete existing file and metadata closures, including every nested signature byte, must remain equal before/after. Only the owning framework executable’s bounded terminal signature allocation and the new owning `_CodeSignature/CodeResources` are candidates for alteration. Do not use recursive --deep signing or delete nested signatures. Actual post-sign strict verification remains mandatory for every candidate and every original framework in the distribution.

No additional product has been modified, signed or qualified by this diagnosis. The retained raw pre-sign attachments permit structural controls locally; they do not provide native signing credit. A subsequent source-bound native run is required for the six additional seals and for the previously unexecuted external consumer/runtime gates.

## Evidence

- `evidence/anycrypto-simulator-signing.json` and retained original/before/after bytes.
- `evidence/package-product-signature-diagnostics.json`, seven actual strict stderr/command receipts, seven actual codesign display outputs, and every bounded original export attachment.
- `evidence/framework-signature-4.command.json` + stderr (AppTarget acceptance stop).
- `evidence/execution.json`, `source-controls-result.json`, source-before/after and owned-simulator-cleanup receipts.
- `NATIVE_RESULT_SUMMARY.json` records exact binary SHA-256, install names, resource digests and source-bound result.
