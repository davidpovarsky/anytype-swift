package space

import (
	"context"
	"errors"
	"time"
)

const (
	RuntimeStateContract       = "pinkha-space-runtime-state-v1"
	RuntimeObjectStateContract = "pinkha-object-runtime-state-v1"
)

var ErrRuntimeObjectIDRequired = errors.New("runtime state: object ID required")

// RuntimeStateProvider is optional. A regular Space may implement it without
// widening the Space interface or changing the existing Info/SyncStatus APIs.
// Both methods fence delivery with the same captured account, loaded Space,
// signed ACL head and current read identity before and after collecting data.
type RuntimeStateProvider interface {
	RuntimeState(context.Context) (RuntimeState, error)
	RuntimeObjectState(context.Context, string) (RuntimeObjectState, error)
}

// RuntimeScope contains public identities, not credentials. AuthorityIdentity
// is the loaded ACL identity, which can differ from AccountID for a guest.
type RuntimeScope struct {
	AccountID         string
	NetworkID         string
	SpaceID           string
	AuthorityIdentity string
	ACLHeadID         string
}

// RuntimeMemberLimits preserves an actually returned zero. A nil Limits in a
// coordinator observation means the original response omitted that message.
type RuntimeMemberLimits struct {
	ReadersLimit uint32
	WritersLimit uint32
}

// RuntimeCoordinatorObservation is the last successful, account/network/Space
// scoped coordinator answer. FetchedAt is never refreshed by a cached read or
// a failed fetch. Status is the original coordinator enum label.
type RuntimeCoordinatorObservation struct {
	FetchedAt time.Time
	Status    string
	IsShared  bool
	Limits    *RuntimeMemberLimits
}

// RuntimeAccessType uses the original Heart access domain. These values must
// not be reconstructed from a role, member count, or generic Derived flag.
type RuntimeAccessType uint8

const (
	RuntimeAccessPrivate RuntimeAccessType = iota
	RuntimeAccessPersonal
	RuntimeAccessShared
)

// RuntimeAccessEvidence keeps the raw evidence when a full classification is
// unavailable. PersonalSpaceID requires positive original native provenance.
// In particular, nil does not mean that the account has no Personal space.
type RuntimeAccessEvidence struct {
	ACLIsEmpty      bool
	PersonalSpaceID *string
	Value           *RuntimeAccessType
	Reason          string
}

type RuntimeState struct {
	Contract    string
	Scope       RuntimeScope
	CapturedAt  time.Time
	Coordinator *RuntimeCoordinatorObservation
	Access      RuntimeAccessEvidence
}

type RuntimeObjectSyncBasis string

const (
	RuntimeSyncPerObjectHooks        RuntimeObjectSyncBasis = "per_object_hooks"
	RuntimeSyncResponsibleSpaceRound RuntimeObjectSyncBasis = "responsible_space_round"
	RuntimeSyncUnobserved            RuntimeObjectSyncBasis = "unobserved"
)

// RuntimeObjectSyncObservation preserves the original tracker semantics.
// LastSyncAt is a HeadsApply or inherited responsible-space confirmation, not
// Heart's syncDate (the time its details updater writes a projection).
type RuntimeObjectSyncObservation struct {
	State      SyncState
	Basis      RuntimeObjectSyncBasis
	LastSyncAt *time.Time
}

// RuntimeSpaceSyncObservation keeps connectivity/protocol state separate from
// an object's historical progress. The original Status rollup supplies State.
// An untracked Space stays unknown even if the separate protocol flag is true.
type RuntimeSpaceSyncObservation struct {
	SpaceID                     string
	State                       SyncState
	Synced                      int
	Total                       int
	NetworkPeers                int
	LocalPeers                  int
	GlobalPeers                 int
	P2P                         P2PState
	LastSyncedAt                *time.Time
	NetworkProtocolIncompatible bool
}

type RuntimeObjectState struct {
	Contract   string
	Scope      RuntimeScope
	ObjectID   string
	CapturedAt time.Time
	ObjectSync RuntimeObjectSyncObservation
	SpaceSync  RuntimeSpaceSyncObservation
}
