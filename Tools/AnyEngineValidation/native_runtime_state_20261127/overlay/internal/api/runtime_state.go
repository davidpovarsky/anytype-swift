package api

import "time"

// Runtime state is an additive, versioned observation. Missing observations
// are JSON null; an actual numeric zero is always emitted as zero.
type RuntimeScope struct {
	AccountID         string `json:"accountId"`
	NetworkID         string `json:"networkId"`
	SpaceID           string `json:"spaceId"`
	AuthorityIdentity string `json:"authorityIdentity"`
	ACLHeadID         string `json:"aclHeadId"`
}

type RuntimeMemberLimits struct {
	ReadersLimit uint32 `json:"readersLimit"`
	WritersLimit uint32 `json:"writersLimit"`
}

type RuntimeCoordinatorObservation struct {
	FetchedAt time.Time            `json:"fetchedAt"`
	Status    string               `json:"status"`
	IsShared  bool                 `json:"isShared"`
	Limits    *RuntimeMemberLimits `json:"limits"`
}

type RuntimeAccessEvidence struct {
	ACLIsEmpty      bool    `json:"aclIsEmpty"`
	PersonalSpaceID *string `json:"personalSpaceId"`
	Value           *uint8  `json:"value"`
	Reason          string  `json:"reason"`
}

type RuntimeStateResponse struct {
	Contract    string                         `json:"contract"`
	Scope       RuntimeScope                   `json:"scope"`
	CapturedAt  time.Time                      `json:"capturedAt"`
	Coordinator *RuntimeCoordinatorObservation `json:"coordinator"`
	Access      RuntimeAccessEvidence          `json:"access"`
}

type RuntimeObjectSyncObservation struct {
	State      string     `json:"state"`
	Basis      string     `json:"basis"`
	LastSyncAt *time.Time `json:"lastSyncAt"`
}

type RuntimeSpaceSyncObservation struct {
	SpaceID                     string     `json:"spaceId"`
	State                       string     `json:"state"`
	Synced                      int        `json:"synced"`
	Total                       int        `json:"total"`
	NetworkPeers                int        `json:"networkPeers"`
	LocalPeers                  int        `json:"localPeers"`
	GlobalPeers                 int        `json:"globalPeers"`
	P2P                         string     `json:"p2p"`
	LastSyncedAt                *time.Time `json:"lastSyncedAt"`
	NetworkProtocolIncompatible bool       `json:"networkProtocolIncompatible"`
}

type RuntimeObjectStateResponse struct {
	Contract   string                       `json:"contract"`
	Scope      RuntimeScope                 `json:"scope"`
	ObjectID   string                       `json:"objectId"`
	CapturedAt time.Time                    `json:"capturedAt"`
	ObjectSync RuntimeObjectSyncObservation `json:"objectSync"`
	SpaceSync  RuntimeSpaceSyncObservation  `json:"spaceSync"`
}
