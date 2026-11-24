# Canonical Hanlin provider schema binding

The actual Native UI continuation45438097556 reached the owned TLS provider
but its selected-context method failed with tool_schema. The original failure
is preserved. This change corrects the finite test provider's exact expected
schema, not the product or the canonical Hanlin engine.

At canonical Hanlin116cc6be0654a5d11bc56ba00e0310031107ee36,
HanlinJSONSchemaDocument.init inserts its explicit $schema dialect when absent.
The shared read/create host tools use decodeCanonicalJSON with draft2020_12.
HanlinAgentSession derives provider schemas from the descriptor's canonical
bytes, and HanlinHostSchemaValidation.providerSchema verifies projection
fidelity before returning the original bytes. The test provider omitted that
exact dialect member and rejected the otherwise declared schema.

Both expected schemas now contain exactly
https://json-schema.org/draft/2020-12/schema. Their property names, required
fields, bounds, additionalProperties=false, consent-dependent catalog, exact
tool aliases, finite requests and no-disclosure assertions remain unchanged.
Missing, foreign, and boolean dialect values are rejected for both tools.
The original boolean-minLength and extra-title-argument refusals remain tested.
The complete finite six-round positive contract and read-consent catalog
control also pass. These five focused Python controls are not an Apple UI pass.

The source manifests bind the reviewed helper tree. The retained-product route
allows only the two additional reviewed protocol/test helper paths; compiled
App/UI product trees are unchanged. Actual UI continuation remains pending.
