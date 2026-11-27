// Package torahindexcontract describes a bounded local native-index witness.
// It contains no account lookup, index repair, root creation or private payload.
package torahindexcontract

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"slices"
	"strings"

	"github.com/anyproto/any-sync/commonspace/headsync/headstorage"
)

const (
	Contract        = "pinkha-heart-torah-space-index-v1"
	Version         = 1
	MaxObjects      = 10000
	MaxWitnessBytes = 16 * 1024 * 1024
)

var (
	ErrBound          = errors.New("native Torah index witness exceeds its complete-snapshot bound")
	ErrNotLoaded      = errors.New("native Torah index scope is not already loaded")
	ErrSnapshotBusy   = errors.New("native Torah index delivery owner is busy")
	ErrScopeChanged   = errors.New("native Torah index owner or scope changed")
	ErrInvalidWitness = errors.New("invalid native Torah index witness")
)

type Reason string

const (
	NotLoaded                Reason = "not-loaded"
	HeadSetChanged           Reason = "authoritative-head-set-changed"
	MissingNativeRoot        Reason = "native-root-unavailable"
	UnknownNativeRoot        Reason = "native-root-unverified"
	MissingIndexedHeads      Reason = "indexed-heads-missing"
	IndexedHeadsChanged      Reason = "indexed-heads-stale"
	MissingObject            Reason = "indexed-object-missing"
	UnknownObject            Reason = "indexed-object-classification-unknown"
	MissingProjection        Reason = "canonical-projection-missing"
	UnsupportedProjection    Reason = "canonical-projection-unsupported"
	StaleProjection          Reason = "canonical-projection-stale"
	InvalidBinding           Reason = "canonical-binding-unavailable"
	MissingNativeAdmission   Reason = "native-root-index-admission-missing"
	PendingDeletion          Reason = "native-deletion-not-terminal"
	MissingDeletionAdmission Reason = "native-deletion-index-admission-missing"
	StaleDeletionAdmission   Reason = "native-deletion-index-admission-stale"
	StaleReconciliation      Reason = "native-link-reconciliation-stale"
	BoundExceeded            Reason = "complete-snapshot-bound-exceeded"
)

type Readiness struct {
	Version    int    `json:"version"`
	State      string `json:"state"`
	Generation string `json:"generation"`
}

type Result struct {
	Contract                 string    `json:"contract"`
	Version                  int       `json:"version"`
	SpaceID                  string    `json:"spaceId"`
	CanonicalKey             string    `json:"canonicalKey"`
	Readiness                Readiness `json:"readiness"`
	Complete                 bool      `json:"complete"`
	AuthoritativeObjectCount int       `json:"authoritativeObjectCount"`
	IndexedObjectCount       int       `json:"indexedObjectCount"`
	EligibleDocumentCount    int       `json:"eligibleDocumentCount"`
	Reasons                  []Reason  `json:"reasons"`
}

// Head is copied from the original decoder, including fields not used by a
// normal live-head hash. Deletion status and sequence are part of equality.
type Head struct {
	ID             string                    `json:"id"`
	Heads          []string                  `json:"heads"`
	CommonSnapshot string                    `json:"commonSnapshot"`
	DeletedStatus  headstorage.DeletedStatus `json:"deletedStatus"`
	IsDerived      bool                      `json:"isDerived"`
	ParentID       string                    `json:"parentId"`
	LastAddSeq     uint64                    `json:"lastAddSeq"`
}

func CopyHead(entry headstorage.HeadsEntry) Head {
	heads := slices.Clone(entry.Heads)
	slices.Sort(heads)
	return Head{ID: entry.Id, Heads: heads, CommonSnapshot: entry.CommonSnapshot,
		DeletedStatus: entry.DeletedStatus, IsDerived: entry.IsDerived,
		ParentID: entry.ParentId, LastAddSeq: entry.LastAddSeq}
}

func (h Head) Equal(other Head) bool {
	return h.ID == other.ID && slices.Equal(h.Heads, other.Heads) &&
		h.CommonSnapshot == other.CommonSnapshot && h.DeletedStatus == other.DeletedStatus &&
		h.IsDerived == other.IsDerived && h.ParentID == other.ParentID && h.LastAddSeq == other.LastAddSeq
}

// HeadsHash preserves the original core/indexer algorithm exactly: sort without
// removing duplicates, comma join, SHA256; the empty vector yields an empty hash.
func HeadsHash(heads []string) string {
	if len(heads) == 0 {
		return ""
	}
	copy := slices.Clone(heads)
	slices.Sort(copy)
	sum := sha256.Sum256([]byte(strings.Join(copy, ",")))
	return hex.EncodeToString(sum[:])
}

// NativeRoot includes no content. Protocol roots are identified by the exact
// authoritative Space state IDs; all other exclusions need a validated header.
type NativeRoot struct {
	Head           Head   `json:"head"`
	Protocol       bool   `json:"protocol"`
	HeaderSHA256   string `json:"headerSHA256,omitempty"`
	NativeType     uint64 `json:"nativeType,omitempty"`
	HeaderVerified bool   `json:"headerVerified"`
	RootFailure    Reason `json:"rootFailure,omitempty"`
}

type NativeSnapshot struct {
	SpaceID    string       `json:"spaceId"`
	ACLID      string       `json:"aclId"`
	SettingsID string       `json:"settingsId"`
	Roots      []NativeRoot `json:"roots"`
}

func (s NativeSnapshot) Equal(other NativeSnapshot) bool {
	if s.SpaceID != other.SpaceID || s.ACLID != other.ACLID || s.SettingsID != other.SettingsID || len(s.Roots) != len(other.Roots) {
		return false
	}
	for n, root := range s.Roots {
		b := other.Roots[n]
		if !root.Head.Equal(b.Head) || root.Protocol != b.Protocol || root.HeaderSHA256 != b.HeaderSHA256 || root.NativeType != b.NativeType || root.HeaderVerified != b.HeaderVerified || root.RootFailure != b.RootFailure {
			return false
		}
	}
	return true
}

type NativeAdmission struct {
	Version      int    `json:"version"`
	SpaceID      string `json:"spaceId"`
	RootID       string `json:"rootId"`
	HeaderSHA256 string `json:"headerSHA256"`
	NativeType   uint64 `json:"nativeType"`
	HeadsHash    string `json:"headsHash"`
}

func (a NativeAdmission) Matches(space string, root NativeRoot) bool {
	return a.Version == Version && a.SpaceID == space && a.RootID == root.Head.ID &&
		root.HeaderVerified && a.HeaderSHA256 == root.HeaderSHA256 && a.NativeType == root.NativeType &&
		a.HeadsHash != "" && a.HeadsHash == HeadsHash(root.Head.Heads)
}

// DeletionAdmission is stored by the same transaction as the actual original
// object-index tombstone. A queued native tuple can bind only its exact expected
// terminal state. It never proves a new head, sequence, root or resurrection.
type DeletionAdmission struct {
	Version    int    `json:"version"`
	SpaceID    string `json:"spaceId"`
	Provenance string `json:"provenance"`
	Terminal   Head   `json:"terminal"`
}

func (a DeletionAdmission) Matches(space string, head Head) bool {
	return a.Version == Version && a.SpaceID == space &&
		(a.Provenance == "captured-before-native-delete" || a.Provenance == "retained-terminal-and-original-tombstone") &&
		head.DeletedStatus == headstorage.DeletedStatusDeleted && a.Terminal.Equal(head)
}

type IndexedWitness struct {
	ID              string             `json:"id"`
	HeadsHash       string             `json:"headsHash,omitempty"`
	Native          *NativeAdmission   `json:"native,omitempty"`
	Deletion        *DeletionAdmission `json:"deletion,omitempty"`
	ProjectionProof string             `json:"projectionProof,omitempty"`
	Classification  string             `json:"classification"`
	ReconcileMarker string             `json:"reconcileMarker,omitempty"`
}

type IndexSnapshot struct {
	SpaceID               string           `json:"spaceId"`
	RunID                 string           `json:"runId"`
	CanonicalKey          string           `json:"canonicalKey"`
	BindingGeneration     string           `json:"bindingGeneration"`
	Witnesses             []IndexedWitness `json:"witnesses"`
	Reasons               []Reason         `json:"reasons"`
	IndexedObjectCount    int              `json:"indexedObjectCount"`
	EligibleDocumentCount int              `json:"eligibleDocumentCount"`
}

func AddReason(reasons []Reason, reason Reason) []Reason {
	if reason == "" || slices.Contains(reasons, reason) {
		return reasons
	}
	return append(reasons, reason)
}

// Generation binds the current owned run, account/ACL and complete captured
// witnesses. It is never an index timestamp, cached all-peer assertion or query
// coverage token. The caller releases it only after the final authority fence.
func Generation(account, aclHead string, native NativeSnapshot, index IndexSnapshot) (string, error) {
	if account == "" || aclHead == "" || native.SpaceID == "" || index.SpaceID != native.SpaceID || len(index.RunID) != 64 {
		return "", ErrInvalidWitness
	}
	value := struct {
		Domain  string         `json:"domain"`
		Version int            `json:"version"`
		Account string         `json:"account"`
		ACLHead string         `json:"aclHead"`
		Native  NativeSnapshot `json:"native"`
		Index   IndexSnapshot  `json:"index"`
	}{Contract, Version, account, aclHead, native, index}
	data, err := json.Marshal(value)
	if err != nil {
		return "", err
	}
	if len(data) > MaxWitnessBytes {
		return "", ErrBound
	}
	sum := sha256.Sum256(data)
	return hex.EncodeToString(sum[:]), nil
}

// DeliveryFence performs only nonblocking identity checks and a tiny completed-result
// callback. It must never wait for a tree, database, owner lock or queued work.
type DeliveryFence func(visit func() error) error
