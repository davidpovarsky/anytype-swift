# Pinned Heart inline projection

This small Go command uses github.com/anyproto/any-block/codec/anyblockjson at the exact version in go.mod. It accepts one bounded JSON object with source and literal fields on stdin and emits the semantic projection on stdout. Do not log private user source/output. The result is a conversion input, never an authority capability.

The Swift receiver and converter live in PinkhaAnyIntegration and PinkhaAnyHost. Detailed scope and original execution logs are in docs/validation/20261124-heart-semantic-projection. Unsupported destination semantics are explicit errors.
