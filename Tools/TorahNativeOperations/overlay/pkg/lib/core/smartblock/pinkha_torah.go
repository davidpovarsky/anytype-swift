package smartblock

// SmartBlockTypePinkhaTorahOperations is a fork-local allocation approved for
// the private ChangeType pinkha.torah.operations.v1. It is intentionally not
// advertised as an upstream protobuf enum allocation. Its native header is the
// versioned private root, never an anytype.object/ObjectChangePayload carrying
// this integer. TypeProvider rejects that forged generic representation.
// Before changing the Heart pin, the collision test must pass against the new
// generated model enum. Do not silently reuse or renumber a persisted type.
const SmartBlockTypePinkhaTorahOperations SmartBlockType = 0x504B0001
