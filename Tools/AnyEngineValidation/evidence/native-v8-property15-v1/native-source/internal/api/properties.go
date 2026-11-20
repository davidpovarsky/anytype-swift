package api

import "encoding/json"

// PropertiesGetResponse is the body of GET /v1/spaces/:spaceId/properties/:objectId.
// Record is the property record rendered as JSON — *anyenc.Value
// converted via FastJson(arena).MarshalTo. Carried as RawMessage so it
// is not double-encoded.
type PropertiesGetResponse struct {
	Record json.RawMessage `json:"record"`
}

// PinkhaPropertiesSetRequest is served ONLY by the opt-in /pinkha/properties
// route. Stock property routes do not enforce these preconditions.
type PinkhaPropertiesSetRequest struct {
	Patch       map[string]any  `json:"patch"`
	IfVersion   json.RawMessage `json:"ifVersion"`
	IfApplySeq  uint64          `json:"ifApplySeq"`
	IfStartedAt string          `json:"ifStartedAt"`
}

type PinkhaPropertiesSetResponse struct {
	ModifyResult
	PropertiesVersion json.RawMessage `json:"propertiesVersion,omitempty"`
	EngineStartedAt   string          `json:"engineStartedAt"`
}
