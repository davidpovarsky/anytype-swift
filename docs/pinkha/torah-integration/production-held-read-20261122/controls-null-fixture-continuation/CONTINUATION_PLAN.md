# Fixture-only continuation after the first compiler failure

The complete first attempt is frozen in ../controls/RED_INDEX.json (170 payloads, 5668098 bytes, SHA256 2eaa54a08ca04cb3b99acc6370326fd719d7784d480de2b5282336dc58329ac4). It exited 1 before any test case or test binary. Its exact logs, compiler source archive, inputs, platform warnings and root review remain unchanged.

Only the unsupported null-value convenience constructor in HeldReadTests.swift:351 changes to Google_Protobuf_Value.with { $0.nullValue = .nullValue }. The actual locked SwiftProtobuf Message.with and Google_Protobuf_Value.nullValue setter were read from c6fe6442e6a64250495669325044052e113e990c and bound in PINNED_NULL_VALUE_API.json. The setter assigns the null oneof kind. The malformed-present-state negative assertion and all other test/helper bytes remain unchanged; exact inverse transformation is required.

Candidate dcb942bb, every original dependency, the whole application adapter, all 26 method names, all assertions and the actual swift command remain unchanged. The 116-entry continuation INPUTS.json changes only this test source's bytes/hash and explicitly references original retained source copies; it does not duplicate or rewrite those files.

The runner verifies the entire frozen first RED index before and after execution. It verifies all 116 existing actual compiler input copies against the prior manifest before replacing only the one test source in the existing owned Temp harness. It records existing compiled module hashes and reuses the exact original build cache. No prior case passed or ran, and no older suite is invoked.

The same 900-second owned command / finite outer budget, raw output/status, exact 26-name xUnit gate, exactly-one-regular-MZ-binary gate, full 115-target-Swift-source archive coverage, and complete before/after source/dependency checks remain required. Package.swift stays explicitly excluded from target source coverage. Any new failure will be retained; no automatic retry is part of the runner.
