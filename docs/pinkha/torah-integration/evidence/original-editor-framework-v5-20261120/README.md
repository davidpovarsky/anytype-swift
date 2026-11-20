# Framework v5: canonical temporary-path controls

Candidate source be2856140b1a5084176d325261dace7e2903a3e1, tree 635e4b32da702deaf3383e0e24b97270311e2382, is an isolated child of the complete v4 failure evidence commit 99ce9f9df4961b06ede70b3081d62837f5907e67. No executable reviewed branch has been created or dispatched by this author. Root owns activation of `codex/otzaria-original-editor-framework-v5-reviewed-20261120`.

## Actual failure and bounded correction

Actual Apple run 44810510321 at frozen 962d050eb36b2511616c771b08d92a78b64d2349 stopped in its prebuild Python gate: 96 methods, 93 PASS, two FAIL and one ERROR. Full original ZIP, canonical metadata/logs, 25 original source files and a read-only verifier are retained in `docs/pinkha/torah-integration/evidence/original-editor-framework-44810510321-20261120` (packet index SHA256 ea959abd4d46debaffcdc8236080bca44ddb7bde9c3214f83f43295715891aef). SDK/Heart preparation, Swift/build/consumer/runtime were NOT_RUN.

The new mutation fixtures compared `Path(source)` from the real exporter, which resolves its products directory, to unresolved TemporaryDirectory paths. If the temporary root contains a real directory alias, the injected write never runs. The raw-source fixture also passed an unresolved root to the original strict source validator, which compares actual resolved compiler paths against a canonical checkout root. The original command already resolves its real checkout/derived roots; no product-path policy is relaxed.

Using the entire unchanged frozen v4 Python source and a real owned symlink TMPDIR on Linux reproduced the exact 93/2/1 outcome and the same three failing method IDs. The actual Mac log did not print its TemporaryDirectory path, so the packet distinguishes this discriminating source/filesystem reproduction from an unrecorded Mac pathname observation.

The correction resolves only two test fixture paths and the raw-source fixture root. Both mutation tests retain their original rejection assertion and now also require exactly one actual mutation plus the precise injected file bytes. Three additive controls invoke those complete original test bodies in fresh Python processes with a real directory alias as TMPDIR. These use actual files, symlinks, copy operations and validators; they are not Apple framework binaries or Swift executions.

## Preserved implementation and scope

All original 96 method declarations remain. The original 54 control bodies are unchanged apart from the exact installer branch literal. No runtime exporter, Darwin ctypes ABI, full closure comparison, source validator, original build/consumer driver, SDK, original application or framework target, public facade, resource, binary/signature check, build flag or timeout changed. The only other edits are five exact branch/pin bindings; the original Heart installer gains one explicit v5 choice while retaining every prior choice. Original 6000-second framework build, 600-second consumer build, 60/180-second boot pair and 140/120-minute job/step limits remain exact.

## Executed controls

- Frozen v4 under a real alias: 96 executed, 93 PASS, two FAIL, one ERROR, exit 1.
- Initial fixture candidate under the same alias: 99/99, exit 0.
- Final exact v5 source under a real alias: 99/99, exit 0.
- Final exact v5 source under the ordinary Linux temporary path: 99/99, exit 0.

The three new parent controls each run one existing case in a bounded child process. They do not represent additional distinct native/editor cases. Every tested source inventory was checked before/after. Both final runs bind the exact published candidate. The intermediate pre-branch-binding projection is reconstructed byte-for-byte from retained baseline/final bytes and verified against every retained executed input digest; it is not represented as a separately captured raw snapshot.

`source-projections.zip` retains baseline, intermediate and final complete bounded source projections plus the exact verification/run drivers. `raw-controls.zip` retains all four attempts, their complete stdout/stderr, input inventories, case results and original synthetic flow receipts. `VERIFY_PACKET.py` reads and checks these records without executing any tests or compiler. `REPLAY.json` is evidence verification only.

Root reviewed the complete 10,511-byte patch (SHA256 75c4d2524365bb3678b4f6ac3a2e96a361237f01f3a9b7d59265b97133aeca4a) and found no source-level blocker. Actual Apple v5 compilation, genuine duplicate-Lib product equality and external-consumer runtime remain NOT_RUN until Root activates and evaluates the new immutable source. Editable host/mount remains NOT_EXPOSED on this framework inspection route.
