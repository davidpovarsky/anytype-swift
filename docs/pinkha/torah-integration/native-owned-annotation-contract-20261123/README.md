# Native owned annotation import: source contract checkpoint

Status: **DOCUMENTATION ONLY — no new native route, generated method, importer activation, or runtime acceptance**.

Base: `cfc71a30498bba772aaf33f1ac08fdf65d1e0e3a` in `davidpovarsky/anytype-swift`. The actual original Heart base remains `d98420b1113536afd08cde6de9a5816f6d27ffff`; the reviewed owned-import and application-lifetime overlays are identified in SOURCE_INVENTORY.json. This packet does not edit the active endpoint or lifetime-repair branches.

## Proposed implementation decision

Use the existing original owned import operation and application registry. Add a closed native owner for bounded archive bytes and a per-member disposition enforced before assignment and at the actual create boundary. Expose Start, Observe, Cancel, and Release only after that closure is qualified. Do not introduce another importer, injected executor, callback-supplied completion, or caller-controlled update flag.

The candidate new-graph path has three dispositions: **create a genuinely new object**, **reuse a verified schema object without entering any mutation path**, or **reject the whole graph**. A known historical mapping reopens the original mapped object; it is never submitted to import again. An unknown prior outcome requires recovery/readback, not an automatic second import.

The candidate supported member set is still unqualified. No authenticated native annotation export graph was found in the narrow retained-evidence search recorded in EXPORT_EVIDENCE_STATUS.json. Existing fixture constructors, synthetic collector reports and distribution ZIPs do not fill that gap. The first implementation slice therefore collects a genuine original export from a disposable native annotation and implements the byte/archive admission boundary; it does not activate Start.

## Why a wrapper around ObjectImport is insufficient

The original existing-object resolver searches oldAnytypeID and uniqueKey before the optional update-existing lookup. Derived objects force the additional existing lookup. A false update flag does not stop reuse. FileObject assignment itself can upload a file before ObjectCreator.Create is entered.

ObjectCreator.Create can mutate workspace/widget objects early, install bundled schema, reset existing objects, set favorite/archive state, and synchronize links/files. Its createNewObject method turns a real ErrTreeExists into a successful existing-object read. Several later errors are logged rather than returned. A root-only preflight or a complete mapping observation cannot establish that the requested body was created.

The native export path also normalizes context.Canceled to a nil error while retaining the original ExportReport. Readback must inspect the report and the actual context/result, not just the RPC error field. These facts are bound to exact source bytes in SOURCE_INVENTORY.json.

## Evidence reused without replay

- Original RPC generation 45101449367 / source 7496e47fa4d37b0117abeae6b35ca5f4c8eaf638 passed generation, generated Go package compilation and Swift protocol typechecking. It did not compile the endpoint or qualify the production import boundary.
- Original lifetime run 45105771388 / source 54169c763c2178fc1e796dfbe92a675d9c21a0b3 compiled all 28 product files. Its prestart cancellation leaf passed; the first import/mapping leaf failed.
- The reviewed repair preserves original NewNoOp's legitimately empty progress ID. Its focused native run is 45116895060 / source cfc71a30498bba772aaf33f1ac08fdf65d1e0e3a. It was observed queued when this packet was prepared; no outcome is inferred here.
- Endpoint run 45108043207 / source 53b52d380c3a87d25275bb391367b37eb5428d3d remains a separate five-case native schema gate. It does not qualify this proposed import RPC.
- Swift closed account/selected-Space composition and archive audit are owned by the original_sdk agent. The production source prerequisite is 89926d7839c09a629c195ec6dd9812fe56aad069; the documentation audit is 642a8b9cd9cd243e820db154ea2471b6882e2a94. No generated import method is assumed to exist.

See CONTRACT.md for the lifecycle and semantic boundary, PROPOSED_PRODUCT_PATHS.json for the staged source allowlist, and QUALIFICATION.md for the required discriminating tests. All additional product paths are proposed and remain unapproved at this checkpoint.
