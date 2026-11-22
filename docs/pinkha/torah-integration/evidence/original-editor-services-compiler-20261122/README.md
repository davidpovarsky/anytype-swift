# Original Services compiler boundary repair — 2026-11-22

The actual original-editor producer run [44978502186](https://github.com/davidpovarsky/anytype-swift/actions/runs/44978502186), head cb2df9baa201db0ce404ba37eac853424bae6204, failed while compiling Services. This is not a qualified framework or external consumer result.

The immutable evidence artifact14737027101 is retained here exactly as downloaded once. Its GitHub SHA256 is ee74d656be583028f8891a102197e06378bbd59bcdc282a63afc756400b8b7f0; ZIP members were decoded/CRC-checked. The archive contains the complete build stdout/stderr, actual command, result bundle, source observations and macro receipts.

## Observed result

The actual Xcode27 arm64 build accepted the scoped reviewed Equatable macro tuple, compiled that original macro target and reached Services compilation. The always-run cleanup restored the exact original trust-store state. No skip-validation setting, global default or source replacement was used. The original package closure remained strict. No editor UI/runtime, external consumer, save/reopen or product acceptance follows from this progress.

Six compiler diagnostics have two causes:

- PublishingService rethrows a concrete generated response error across a module boundary. The correction keeps the original caught Swift.Error existential; only the original .null publishing condition becomes nil. The strict original-editor GetStatus response classifier and Invocation implementation remain unchanged.
- TemplatesService referred to two app-only convenience properties. Object-type checks now use the original resolvedLayoutValue.isObjectType definition available inside Services. Template checks follow the original referenced object type and exact .template unique key, using the existing strict same-Space ObjectShow/readback helper.

## Ownership and behavior

The template helper is called only in the existing bound branch. It rejects an absent/NUL type identifier, reads that exact referenced native type, verifies response root/row/object identity and captured Space through the existing helper, and verifies original object-type layout plus template unique key. It does not infer template identity from layout, title or targetObjectType alone.

The new ObjectShow inherits the current InvocationDispatchContext.binding from the retained PreparedEditorChildPreparation.performMutation/document-action lease. No new Task, parent re-entry, account bootstrap or cached app type provider is introduced. The subsequent native mutation still obtains its own current-owner permit immediately before the original native RPC. Cancellation, owner/account/source retirement and errors retain existing failure paths. The unbound legacy TemplatesService route is unchanged.

Both changed original Services files are UPSTREAM_OWNED corrections to explicitly authorized integration. Original upstream/develop was freshly observed at d857b23ea540be33d6faab4f7a7a1a260ab578c1. No Heart/generated protocol, owner implementation, public facade, package pin, macro preparation or canonical source-envelope change is included.

## Verification and remaining work

The two changed files pass Windows Swift6.3.3 syntax admission. That check is explicitly not a Services module typecheck or native execution. The next coherent original framework build must verify these actual module boundaries. Unchanged Publishing classifier controls and unchanged trust helper controls are preserved, not rerun locally. All cross-app A–F product gates remain open.

Rollback is the two exact preimages identified in repair/EDIT_RECEIPT.json and the inverse of the retained two-file patch; no history rewrite is required.
