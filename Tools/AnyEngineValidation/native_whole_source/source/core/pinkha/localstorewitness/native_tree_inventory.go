//go:build pinkha_loaded_account_witness

package localstorewitness

import (
	"bytes"
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"math"
	"sort"

	"github.com/anyproto/any-store/anyenc"
)

var ErrNativeTreeInventory = errors.New("complete native tree identity inventory required")

// NativeTreeIdentity is a detached private identity. Its accessors copy mutable
// data. It is not account authorization, a signed-history validation, or a token
// that permits destination writes.
type NativeTreeIdentity struct {
	id, commonSnapshot, parentID, rootSHA256, rowSHA256 string
	heads                                               []string
	rootRaw                                             []byte
	deleted                                             int
	derived                                             bool
	changes                                             int
}

func (t NativeTreeIdentity) ID() string             { return t.id }
func (t NativeTreeIdentity) Heads() []string        { return append([]string(nil), t.heads...) }
func (t NativeTreeIdentity) RootRawChange() []byte  { return append([]byte(nil), t.rootRaw...) }
func (t NativeTreeIdentity) CommonSnapshot() string { return t.commonSnapshot }
func (t NativeTreeIdentity) ParentID() string       { return t.parentID }
func (t NativeTreeIdentity) DeletedStatus() int     { return t.deleted }
func (t NativeTreeIdentity) Derived() bool          { return t.derived }

// NativeTreeInventory is issued only from a complete native-owned Witness.
// Existing FixtureOnlyAuthority census behavior remains unchanged.
type NativeTreeInventory struct {
	witness             *Witness
	acl                 NativeACLReadHead
	settingsID          string
	trees               map[string]NativeTreeIdentity
	ids                 []string
	digest              string
	changeRecords       int
	orphanChanges       int
	unresolvedHistory   int
	otherCollections    int
	otherCollectionRows int
	complete            bool
}

type NativeTreeInventoryReceipt struct {
	Version, SourceWitnessSHA256, InventorySHA256  string
	SpaceSHA256, ACLHeadSHA256                     string
	Generation                                     uint64
	Trees, ActiveTrees, DeletedTrees, DerivedTrees int
	ChangeRecords, OrphanChanges                   int
	UnresolvedHistoryReferences                    int
	OtherCollections, OtherCollectionRows          int
	AllHeadRowsAccounted                           bool
	AccountSessionAuthorized                       bool
	HistorySemanticsValidated                      bool
	SemanticCompleteness                           bool
	FilePayloadCompleteness                        bool
	HasNativeSourceAdmission                       bool
	PermitsDestinationWrites                       bool
}

type nativeInventoryChange struct {
	tree, snapshot string
	raw            []byte
	previous       []string
}

// NativeTreeIdentities parses the already detached native checkpoint. No DB,
// account, object cache, file, network or destination is opened. Unknown external
// collections remain counted and retained in the original private Witness.
func (w *Witness) NativeTreeIdentities(ctx context.Context) (*NativeTreeInventory, error) {
	if ctx == nil || w == nil || !w.complete || w.binding.Authority != NativeOwnedStoreAuthority {
		return nil, ErrOwnership
	}
	if err := ctx.Err(); err != nil {
		return nil, err
	}
	h := sha256.New()
	if err := w.writePrivate(h); err != nil || hex.EncodeToString(h.Sum(nil)) != w.digest {
		return nil, ErrNativeTreeInventory
	}
	acl, err := w.NativeACLHead()
	if err != nil {
		return nil, err
	}
	state, err := w.collection("state").stringID(w.binding.SpaceID)
	if err != nil {
		return nil, err
	}
	settings, err := requiredString(state, "s")
	if err != nil {
		return nil, err
	}
	heads, changes := w.collection("heads"), w.collection("changes")
	if heads == nil || changes == nil {
		return nil, ErrNativeTreeInventory
	}
	result := &NativeTreeInventory{witness: w, acl: acl, settingsID: settings, trees: map[string]NativeTreeIdentity{}}
	records := map[string]nativeInventoryChange{}
	for _, row := range changes.rows {
		if err := ctx.Err(); err != nil {
			return nil, err
		}
		fields, err := nativeInventoryFields(row, "id t r p i o sz sc a q")
		if err != nil {
			return nil, err
		}
		id, err := nativeInventoryString(fields, "id", true)
		if err != nil {
			return nil, err
		}
		tree, err := nativeInventoryString(fields, "t", true)
		if err != nil {
			return nil, err
		}
		rawValue, exists := fields["r"]
		if !exists {
			return nil, ErrNativeTreeInventory
		}
		raw, err := rawValue.Bytes()
		if err != nil || len(raw) == 0 {
			return nil, ErrNativeTreeInventory
		}
		previous, err := nativeInventoryStrings(fields["p"], false)
		if err != nil {
			return nil, err
		}
		snapshot, err := nativeInventoryString(fields, "i", false)
		if err != nil {
			return nil, err
		}
		if _, exists := records[id]; exists {
			return nil, ErrNativeTreeInventory
		}
		records[id] = nativeInventoryChange{tree: tree, snapshot: snapshot, raw: append([]byte(nil), raw...), previous: previous}
	}
	seen := map[string]bool{}
	for _, row := range heads.rows {
		if err := ctx.Err(); err != nil {
			return nil, err
		}
		fields, err := nativeInventoryFields(row, "id h s d r p q")
		if err != nil {
			return nil, err
		}
		id, err := nativeInventoryString(fields, "id", true)
		if err != nil || seen[id] {
			return nil, ErrNativeTreeInventory
		}
		seen[id] = true
		if id == acl.ACLID() {
			continue // NativeACLHead has separately checked this exact ACL row.
		}
		deleted, err := nativeInventoryDeletion(fields["d"])
		if err != nil {
			return nil, err
		}
		headIDs, err := nativeInventoryStrings(fields["h"], deleted == 0)
		if err != nil {
			return nil, err
		}
		common, err := nativeInventoryString(fields, "s", false)
		if err != nil {
			return nil, err
		}
		parent, err := nativeInventoryString(fields, "p", false)
		if err != nil {
			return nil, err
		}
		derived := false
		if value := fields["r"]; value != nil {
			switch value.Type() {
			case anyenc.TypeTrue:
				derived = true
			case anyenc.TypeFalse:
			default:
				return nil, ErrNativeTreeInventory
			}
		}
		if value := fields["q"]; value != nil {
			n, numberErr := value.Float64()
			if numberErr != nil || math.IsNaN(n) || math.IsInf(n, 0) || n < 0 || math.Trunc(n) != n || n > 1<<53 {
				return nil, ErrNativeTreeInventory
			}
		}
		entry := NativeTreeIdentity{id: id, heads: headIDs, commonSnapshot: common, parentID: parent,
			deleted: deleted, derived: derived, rowSHA256: sum(row.value)}
		root, exists := records[id]
		if exists && root.tree == id {
			entry.rootRaw = append([]byte(nil), root.raw...)
			entry.rootSHA256 = sum(root.raw)
		} else if deleted == 0 {
			return nil, ErrNativeTreeInventory
		}
		for _, head := range headIDs {
			record, exists := records[head]
			if (!exists || record.tree != id) && deleted == 0 {
				return nil, ErrNativeTreeInventory
			}
		}
		if common != "" {
			record, exists := records[common]
			if (!exists || record.tree != id) && deleted == 0 {
				return nil, ErrNativeTreeInventory
			}
		}
		result.trees[id] = entry
		result.ids = append(result.ids, id)
	}
	if !seen[acl.ACLID()] || !seen[settings] || len(seen) != len(heads.rows) {
		return nil, ErrNativeTreeInventory
	}
	sort.Strings(result.ids)
	for _, record := range records {
		entry, exists := result.trees[record.tree]
		if !exists {
			result.orphanChanges++
		} else {
			entry.changes++
			result.trees[record.tree] = entry
		}
		references := append([]string(nil), record.previous...)
		if record.snapshot != "" {
			references = append(references, record.snapshot)
		}
		for _, id := range references {
			referenced, exists := records[id]
			if !exists || referenced.tree != record.tree {
				result.unresolvedHistory++
			}
		}
	}
	result.changeRecords = len(records)
	for _, col := range w.collections {
		if col.name != "state" && col.name != "heads" && col.name != "changes" && col.name != acl.ACLID() {
			result.otherCollections++
			result.otherCollectionRows += len(col.rows)
		}
	}
	// The version binds this deterministic interpretation; the source digest
	// binds every original collection and row, including retained opaque data.
	result.digest = sum([]byte("pinkha-native-tree-identities-v1\x00" + w.digest))
	if err := ctx.Err(); err != nil {
		return nil, err
	}
	result.complete = true
	return result, nil
}

func nativeInventoryFields(row row, allowed string) (map[string]*anyenc.Value, error) {
	value, err := anyenc.Parse(row.value)
	if err != nil {
		return nil, ErrNativeTreeInventory
	}
	object, err := value.Object()
	if err != nil {
		return nil, ErrNativeTreeInventory
	}
	known := map[string]bool{}
	for _, key := range bytes.Fields([]byte(allowed)) {
		known[string(key)] = true
	}
	fields := map[string]*anyenc.Value{}
	invalid := false
	object.Visit(func(key []byte, value *anyenc.Value) {
		name := string(key)
		if fields[name] != nil || !known[name] {
			invalid = true
		}
		fields[name] = value
	})
	if invalid || fields["id"] == nil || !bytes.Equal(fields["id"].MarshalTo(nil), row.id) {
		return nil, ErrNativeTreeInventory
	}
	return fields, nil
}

func nativeInventoryString(fields map[string]*anyenc.Value, key string, required bool) (string, error) {
	value := fields[key]
	if value == nil {
		if required {
			return "", ErrNativeTreeInventory
		}
		return "", nil
	}
	raw, err := value.StringBytes()
	if err != nil || (required && len(raw) == 0) {
		return "", ErrNativeTreeInventory
	}
	return string(raw), nil
}

func nativeInventoryStrings(value *anyenc.Value, required bool) ([]string, error) {
	if value == nil {
		if required {
			return nil, ErrNativeTreeInventory
		}
		return nil, nil
	}
	values, err := value.Array()
	if err != nil || (required && len(values) == 0) {
		return nil, ErrNativeTreeInventory
	}
	result := make([]string, 0, len(values))
	seen := map[string]bool{}
	for _, value := range values {
		raw, err := value.StringBytes()
		if err != nil || len(raw) == 0 || seen[string(raw)] {
			return nil, ErrNativeTreeInventory
		}
		seen[string(raw)] = true
		result = append(result, string(raw))
	}
	sort.Strings(result)
	return result, nil
}

func nativeInventoryDeletion(value *anyenc.Value) (int, error) {
	if value == nil {
		return 0, nil
	}
	n, err := value.Float64()
	if err != nil || math.IsNaN(n) || math.IsInf(n, 0) || math.Trunc(n) != n || n < 0 || n > 2 {
		return 0, ErrNativeTreeInventory
	}
	return int(n), nil
}

func (c *NativeTreeInventory) SpaceID() string {
	if c == nil || !c.complete {
		return ""
	}
	return c.witness.binding.SpaceID
}

func (c *NativeTreeInventory) TreeIDs() []string {
	if c == nil || !c.complete {
		return nil
	}
	return append([]string(nil), c.ids...)
}

func (c *NativeTreeInventory) Tree(id string) (NativeTreeIdentity, error) {
	if c == nil || !c.complete {
		return NativeTreeIdentity{}, ErrNativeTreeInventory
	}
	entry, exists := c.trees[id]
	if !exists {
		return NativeTreeIdentity{}, ErrNativeTreeInventory
	}
	entry.heads = entry.Heads()
	entry.rootRaw = entry.RootRawChange()
	return entry, nil
}

// MatchObject joins an actual locked native object to this old checkpoint.
// Success establishes byte/identity equality only, never current authorization.
func (c *NativeTreeInventory) MatchObject(spaceID, objectID, rootID string, rootRaw []byte, heads []string) error {
	entry, err := c.Tree(objectID)
	if err != nil || spaceID != c.SpaceID() || rootID != objectID || entry.deleted != 0 ||
		len(entry.rootRaw) == 0 || !bytes.Equal(entry.rootRaw, rootRaw) || len(heads) != len(entry.heads) {
		return ErrNativeTreeInventory
	}
	ordered := append([]string(nil), heads...)
	sort.Strings(ordered)
	for i := range ordered {
		if ordered[i] != entry.heads[i] {
			return ErrNativeTreeInventory
		}
	}
	return nil
}

// SameCheckpoint is deliberately strict: even retained opaque source rows must
// remain identical. It does not reauthorize either detached witness.
func (c *NativeTreeInventory) SameCheckpoint(other *NativeTreeInventory) error {
	if c == nil || other == nil || !c.complete || !other.complete ||
		c.witness.binding != other.witness.binding || c.witness.digest != other.witness.digest || c.digest != other.digest {
		return ErrNativeTreeInventory
	}
	return nil
}

func (c *NativeTreeInventory) Receipt() (NativeTreeInventoryReceipt, error) {
	if c == nil || !c.complete || c.witness == nil {
		return NativeTreeInventoryReceipt{}, ErrNativeTreeInventory
	}
	r := NativeTreeInventoryReceipt{
		Version: "native-tree-identity-inventory-v1", SourceWitnessSHA256: c.witness.digest, InventorySHA256: c.digest,
		SpaceSHA256: sum([]byte(c.SpaceID())), ACLHeadSHA256: sum([]byte(c.acl.HeadID())), Generation: c.witness.binding.Generation,
		Trees: len(c.ids), ChangeRecords: c.changeRecords, OrphanChanges: c.orphanChanges,
		UnresolvedHistoryReferences: c.unresolvedHistory, OtherCollections: c.otherCollections,
		OtherCollectionRows: c.otherCollectionRows, AllHeadRowsAccounted: true,
	}
	for _, entry := range c.trees {
		if entry.deleted == 0 {
			r.ActiveTrees++
		} else {
			r.DeletedTrees++
		}
		if entry.derived {
			r.DerivedTrees++
		}
	}
	return r, nil
}

// String contains only safe receipt metadata, never native IDs or row bytes.
func (c NativeTreeInventory) String() string {
	r, err := c.Receipt()
	if err != nil {
		return "NativeTreeInventory{incomplete}"
	}
	raw, _ := json.Marshal(r)
	return string(raw)
}
