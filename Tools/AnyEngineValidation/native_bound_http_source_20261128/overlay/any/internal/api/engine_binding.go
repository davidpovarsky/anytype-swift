package api

// EngineBindingContract names the explicitly bound HTTP routes. It is not
// a credential; the existing managed control-token policy still applies.
const EngineBindingContract = "pinkha-any-http-engine-binding-v1"

const (
	ExpectedAccountHeader = "X-Any-Expected-Account-Id"
	ExpectedRunHeader     = "X-Any-Expected-Run-Id"
	BindingContractHeader = "X-Any-Binding-Contract"
	BoundAccountHeader    = "X-Any-Bound-Account-Id"
	BoundRunHeader        = "X-Any-Bound-Run-Id"
)

// EngineBindingResponse is one admitted engine instance. RunId is random
// per successful boot and is never restored from account storage.
type EngineBindingResponse struct {
	Contract  string `json:"contract"`
	NetworkId string `json:"networkId"`
	AccountId string `json:"accountId"`
	RunId     string `json:"runId"`
}
