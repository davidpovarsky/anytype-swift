# Return split focus ownership

The original Release preparation failed after Return because setAndSplit published a request and then assigned a different pending request. TextBlockContentView correctly rejected the first request as superseded. The production edit installs one pending request first and publishes that same request without discarding it, so a row created by the following general event can still consume it.

Three new controls call the real BlockActionService with real EditorCursorManager, Combine publication, general event delivery, native TextBlockContentView and UIWindow. Only the TextServiceProtocol RPC boundary is stubbed. They cover an already rendered destination, a destination created by the actual general event, and a truly later focus request that must win. They verify RPC arguments, insertion registration and native first responder/caret behavior.

Factory 2.3.1's exact push/pop implementation and the text service shared scope are bound in source-qualification.json. The fixture restores the manager's saved registration/cache state and the previous key window; it consumes only its unique insertion id. Select exactly the three named controls without concurrent registration-changing suites.

Oracle's Swift parser establishes syntax only. The controls require a new Apple build containing the changed production source and actual enumeration/execution. Retained older App binaries cannot prove this repair. RTL pre-insertion observation timing and the original simulator clone's unproven cleanup remain separate open findings. Original failed evidence is preserved.
