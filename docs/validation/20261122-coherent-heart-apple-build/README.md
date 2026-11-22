# Original coherent Apple build and simulator admission repair

The original run [45035194823](https://github.com/davidpovarsky/anytype-swift/actions/runs/45035194823)
at 78b8b6168f0a750d2b742d94b78c95aa4abf579a built separate production and
fixture Heart frameworks. It failed before creating the simulator and did not
execute XCTest or either framework. This directory preserves that outcome.

The proof-original.zip file is the complete, unchanged 106-file evidence
artifact 14759749585. Its SHA-256 is
ff35f54d028057cccc3125d63e681a257e371d37cacd3e7a5ea0aadf1b69b358.
The audit_original_build.py script checks the ZIP, all contained file hashes,
unchanged 139-file native source snapshot, framework/host/descriptor receipt
bindings, retained-control counts, and the original failure. Its replay result
is ORIGINAL_BUILD_AUDIT.json.

The host chose an iPad device independently from the newest iOS 27 runtime.
That runtime advertised phone-specific compatible devices, so CoreSimulator
returned error 403, Incompatible device. The repair chooses an explicit
intersection of installed device types and each runtime's supported types,
product family, architecture and full version bounds. Missing compatibility
metadata is refused. Replaying the original inventories selects a compatible
general iOS 27.2 runtime and iPad; five new selector controls passed. This
inventory replay does not create a simulator or constitute an Apple execution.

The continuation consumes the original production artifact 14759749573 and
fixture artifact 14760192199. It verifies their pinned ZIP, TAR, packaged
receipt and binary hashes before executing the unchanged actual host test.
It preserves the original build origin separately from the new execution
origin. An eventual successful continuation may qualify the original binaries
with new execution evidence; it must not relabel this failed run as a
successful execution producer. The large binary artifacts are not duplicated
in this directory. The independent audit here checks their original receipt
bindings; their actual byte verification belongs to the continuation.

The production binary SHA-256 is
1b317dd0d4a22222f0e2eac7769be65b301ffbf4e45c91be4ab4377b87dfa1d1.
The distinct fixture binary SHA-256 is
84213a9393e7ae17633dce1c60f53afcf7a373f83069e60d9667d53f603642f9.
Original native tests and retained Python/Go controls are not rerun.

Full T2, T5, SDK06, application acceptance and physical iPad acceptance remain
open. This evidence does not authorize release, TestFlight, main/develop
integration, or a claim of production binary execution.
