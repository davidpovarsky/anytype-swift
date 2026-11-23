# Exact original native RPC input composition

This is an inert source inventory and handoff. It contains no generated Import/Cancel outputs, compiled native library, activated producer/profile, account execution or new native result.

## Exact native tree

The original Heart base is d98420b1113536afd08cde6de9a5816f6d27ffff, tree 3d5c0ac2b15840e71693a7a94e229bb605d5f0f6. A private bare repository and a separate owned index were used for source assembly; canonical Heart refs and other worktrees were untouched.

| Stage | Exact source | Operation and boundary |
| --- | --- | --- |
| Original r14 and frozen B1/C | r14 at d02a4972e7f124bc97a577e1c6d448d4797acf22; B1/C62e5f1c9d62c99cc00debfe7e1975557eeec32fa | The exact r14 patch checks all35 original preimages. Forty-three retained original afterimages and twelve accepted B1/C source files follow in their recorded order. All90 transforms and83 final changed paths reproduce the accepted source manifest. |
| Existing schema endpoint and IDL | 7496e47fa4d37b0117abeae6b35ca5f4c8eaf638 | The unchanged core/annotation_schema.go and the two original schema IDL afterimages are added. The endpoint bytes match the actual five-case native endpoint run45108043207 source53b52d380c3a87d25275bb391367b37eb5428d3d. This preserves historical acceptance without replaying it. |
| New owned Import/Cancel boundary | 0a232149712dbdb925cec96e565dae925b2e09c3 | Six reviewed product paths add the original application registry binding, new core handler, two IDLs and exact two-method gRPC payload exclusions. These RPC paths remain ungenerated and unqualified natively. |

The resulting **pre-generation tree is 16764dde5a16208b778e1a37e41bc05ef1735677**. It has99 ordered transforms and88 final changed paths. Native-afterimages contains only those88 changed source files; overlaying them on the exact original Heart tree reconstructs the same complete tree.

ORDERED_SOURCE_TRANSFORMS.json records full before/after byte counts, SHA256 and Git blob identities for every transform. FINAL_NATIVE_AFTERIMAGES.json binds each retained final source to its original and final identity. RPC_SOURCE_OVERLAPS.json verifies that all five existing-file RPC preimages are exactly the bytes produced by the earlier stages. Applying the full existing-file inverse and removing only the new core handler restored the complete staged schema tree987a2f71dd40705ae85f22c6b9008cb83f8d8f7d.

The B1/C-only tree before the schema boundary is d7a1cd4434765f8858a4ffa28caba9645a50f093. Original go.mod, go.sum and tantivity_sha256.txt remain exact d984 bytes. The two retained r14 test files are original source inputs; no tests were run during this inventory.

## Generated outputs are still pending

The full inert Git tree deliberately retains the original d984 versions of pb/commands.pb.go, pb/service/service.pb.go, clientlibrary/service/service.pb.go and docs/proto.md. The source inputs require actual original generation before this new RPC composition can compile. No generated file was handwritten, copied forward as an Import/Cancel implementation or produced by this work.

The authenticated prior schema-generation archive from run45101449367 is bound by SHA256 ec13df1db9405ffa42b2ef76ec1bda7988ecee8dff1c3fcb1fd01c556a7cf80e and retained evidence commit f9b37d7809c08a100a10417a7f699302c758ca8f. Its exact four native, five Swift and six middleware delta identities are retained in INHERITED_GENERATED_OUTPUT_BOUNDARY.json. They describe the old Schema.Register generation, not a fabricated new generation result.

The original native generation is expected to update the actual Go command models, native gRPC service, mobile C wrapper and protocol documentation from the new IDL. The original Swift route must then determine its actual split files and invocation/localization changes. Existing schema split files may remain unchanged or be updated by the actual generator; this packet does not invent new file hashes or an exhaustive expected delta. The complete new output inventory must be observed.

## Original generation route and pins

GENERATOR_INPUTS.json retains35 actual original source inputs. Original Heart and Swift files were re-read from their immutable Git revisions. The original custom gogo Makefile and SwiftProtobuf Package.swift were retrieved from exact primary-source commits and matched their already recorded SHA256, Git blob and byte count.

The original route is:

1. In Heart, make setup-protoc-go.
2. In Heart, make protos-go protos-server swift-protos.
3. Use the original middleware copy/composition route, then in Swift, make generate-middle.

These are retained source commands, not executed commands in this packet. The original scripts, templates and module pins are unchanged. Original generated middleware .bak/import-flattening behavior is preserved in the source and historical artifact; it must not be silently replaced with handwritten generated files.

| Input | Pinned source/version |
| --- | --- |
| Go | 1.26.5; actual future tool identity must be recorded |
| protoc | 32.1; original Darwin ARM64 archive and binary hashes in TOOL_PINS.json |
| gogo | require github.com/gogo/protobuf v1.3.2; exact anyproto/protobuf replacement v1.3.3-0.20240201225420-6e325cf0ac38 |
| SwiftProtobuf | 1.32.0 at c6fe6442e6a64250495669325044052e113e990c |
| Sourcery | 2.2.6 |
| SwiftGen | 6.6.4-alpha.0 |
| Original file splitter | Exact original Swift source, swift-syntax600.0.1 and swift-argument-parser1.2.1 from the original Package.resolved |
| Original codegen executable | Git blob931bfcf515613b67ad59d8927af08d6059272b49; SHA25656ad3a9accfd6c86af6aca7a4f51e8989b0499c2f637d7c4c883bf4dcee48482 |

The codegen executable was read and hashed but was neither duplicated nor executed. Historical tool executable hashes are retained as historical measurements. A newly built generator's binary identity must be recorded independently; matching version text does not imply a matching binary.

The exact accepted Swift source base is f8bc89c6a96552582ecf070ff920cc86f92868d4. FROZEN_SWIFT_GENERATOR_CORRESPONDENCE.json verifies all23 selected original Swift generator files, including the codegen executable, are byte-identical to the original generation base3be6ecab805b17e2c90fee897fdab45a0b03bfdc. The accepted source inventory at64aa43a7d640a6c758f60e0f133d5c3e9d18e6f8 is retained separately. This does not compose root's later Invocation997e285 changes, a future closed import facade or unobserved generated outputs into a finished production ABI.

## Ownership and acceptance boundary

Root coordinates the new production tooling and actual generation. This packet only supplies exact native input assembly and original generator correspondence. It changes no tooling path, canonical native source, Swift product source, dependency pin, profile, workflow or deployment.

The three new RPC boundary-test source files are listed separately in RPC_BOUNDARY_TEST_INPUTS.json and are not injected into the production input tree. They still require genuine generated types and their reviewed execution gate. The actual existing Native9 run45172604455 uses the separate frozen B1/C qualification source; it does not compile or qualify this RPC composition.

A native Import/Cancel boundary still needs genuine generated dispatch, actual application/account/selected-Space admission, same-owner cancellation/history joining, complete bounded response copy and original cleanup. Swift Invocation/Lib linkage, the closed selected-Space owner, Host saved-row/body/revision readback and final acknowledgement remain distinct acceptance gates. No prior schema, lifetime, export or source-only result grants those outcomes.

An initial private-index removal command refused to run without a worktree. PREPARATION_BOUNDARY.json retains that source-assembly failure and the correction to the documented zero-mode index-info removal. No generator, compiler, native account or CI run was involved in either assembly attempt.
