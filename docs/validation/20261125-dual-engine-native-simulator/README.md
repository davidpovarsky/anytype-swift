# One native runtime: original Heart and Any, iOS Simulator

The exact 4,852-file source manifest `70fb5342f2ff31d1cf5f7ce44bed7b16f6373f6bf95eb031d165339cf0f26683` compiled both engines in one gomobile invocation on the Scaleway Apple Silicon Mac with Go 1.27.4 and Xcode 27. The original compiler exited 0 in 362.77 seconds. Actual archive symbols contain exactly one `_crosscall2` and one `__cgo_wait_runtime_init_done`; both original Heart service and Any Mobile entry points are present.

The source includes exact Heart Page154 production entries, the native account-source capture/revalidation fix at `a2916b27eaa16fc291f438fe620b3d09bc0a85e0`, Any `cf87c43ff0100c2dc43c3c105c82b1b070b3a7a3`, SDK `e195f6c07a053c6588e39ffe72ee4fc44cf3d953` and the qualified any-sync ACL witness overlay `c005bd6cde8d8f8a6007c35f06894f3d89f9f07c`. Test fixtures are not runtime build tags. Exact Tantivy native machine code, symbols and semantic relocations are preserved by the reviewed legacy LLVM-section transform.

## Original failure and focused repair

The original producer receipt remains FAIL: its final generated Swift probe incorrectly assumed that gomobile free functions import NSError pointers as throwing Swift functions. The original native build itself passed. Commit `1c49ada09a697508925889c3069019539d2547bd` corrected that ABI at the production ProtobufMessages boundary. The focused continuation verified every original native command and source/archive hash, reused the identical library, and actually typechecked both production Swift wrapper files as well as the generated entry probe. Both checks exited 0; the library was not rebuilt or modified.

## Deliverable and scope

- Original framework binary: 353,464,736 bytes, SHA256 `08f8b8dab68ed21cabec955fbde1323983f02f549dd67aa3e2e4d11c4f818bfc`.
- Framework ZIP: 99,419,537 bytes, SHA256 `d8eb21f6fdbe8a8842974d1c2f7c4a6c9d25519af0e9190899133829caea5028`.
- Full 68-file original evidence archive retained here: SHA256 `a8a454a669a8b8fa7c595626e1980aa06b15fc33a79d36044759a2fdae2f52e1`.
- Mac root: `/Users/m1/builds/pinkha-dual-native-v1-70fb5342f2ff-simulator`.

This is actual native compilation, symbol/linkage and Swift ABI proof. Application builds, runtime engine transitions, migration, native acceptance, UI acceptance and physical-device checks were **not executed by this producer**. The device slice and single application integration require their own evidence. The continuation receipt states these limits explicitly.
