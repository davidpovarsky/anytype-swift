package anytype

import "github.com/anyproto/any-sync-sdk/internal/schema"

// FieldPinkhaLastOpenedV1 is an explicit device-local value on every object.
// It is separate from imported source-system last-opened metadata. No type or
// collection creation is required before a current Reader can use it.
const FieldPinkhaLastOpenedV1 = "pinkhaLastOpenedV1"

const PinkhaLastOpenedContractV1 = "pinkha-last-opened-local-v1"

// The existing native datetime kind stores Unix milliseconds. The descriptor's
// whole-second precision is a consumer contract: clients write seconds*1000.
// XFormat is descriptive metadata, not a new SDK rounding or sync rule.
var pinkhaLastOpenedProperty = BuiltInProperty{
	Id:          FieldPinkhaLastOpenedV1,
	Name:        "Last opened",
	Description: "Last opened instant on this device; never synced. Separate from imported source-system metadata.",
	Kind:        schema.KindDatetime,
	Scope:       schema.ScopeLocal,
	XFormat: map[string]any{
		"type":      "datetime",
		"contract":  PinkhaLastOpenedContractV1,
		"precision": "seconds",
	},
}
