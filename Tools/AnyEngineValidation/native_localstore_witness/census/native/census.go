package localstorewitness

import (
	"bytes"
	"context"
	"crypto/sha256"
	"encoding/hex"
	"errors"
	"fmt"
	"math"
	"sort"

	"github.com/anyproto/any-store/anyenc"
)

// This is a structural census of one completed, fixture-owned local witness.
// It neither reconstructs Heart Objects nor grants source or destination authority.
var ErrIncompleteCensus = errors.New("complete captured local witness required")

type CensusLimits struct {
	MaxRows, MaxReferences, MaxIssues int
	MaxPrivateBytes                   int64
}

func DefaultCensusLimits() CensusLimits {
	return CensusLimits{MaxRows: 10000, MaxReferences: 100000, MaxIssues: 100000, MaxPrivateBytes: 64 << 20}
}

func (l CensusLimits) valid() bool {
	m := DefaultCensusLimits()
	return l.MaxRows > 0 && l.MaxRows <= m.MaxRows &&
		l.MaxReferences > 0 && l.MaxReferences <= m.MaxReferences &&
		l.MaxIssues > 0 && l.MaxIssues <= m.MaxIssues &&
		l.MaxPrivateBytes > 0 && l.MaxPrivateBytes <= m.MaxPrivateBytes
}

type censusRow struct {
	collection, ordinal int
	kind                string
	nativeID, id, tree  []byte // typed row encoding plus exact native string bytes
	deleted, derived    int    // -1 means absent; the original typed row remains intact
	unresolved          bool
}

type censusReference struct {
	row, position, target, observed int
	kind, domain, outcome           string
	field, id, tree                 []byte
}

type censusIssue struct {
	collection, row, position int
	code                      string
	field                     []byte
}

type LocalTreeCensus struct {
	witness    *Witness
	limits     CensusLimits
	rows       []censusRow
	references []censusReference
	issues     []censusIssue
	digest     string
	bytes      int64
	complete   bool
}

type CensusCount struct {
	Kind  string
	Count int
}

type CensusReceipt struct {
	Version, Scope, Authority, Representation string
	SourceWitnessSHA256, CensusSHA256         string
	OwnerSHA256, SpaceSHA256                  string
	Generation                                uint64
	Collections, EmptyCollections, Rows       int
	References, ResolvedReferences, Issues    int
	UnresolvedRows, UnknownCollections        int
	PrivateBytes                              int64
	RowsByKind, IssuesByCode                  []CensusCount
	AllCapturedRowsAccounted                  bool
	AllRecognizedReferencesResolved           bool
	SemanticIdentityCensusComplete            bool
	NativeSnapshotProofRequired               bool
	NativeIdentityCensusRequired              bool
	HasNativeSourceAdmission                  bool
	PermitsDestinationWrites                  bool
}

type censusFields struct {
	values map[string][]*anyenc.Value
	order  []string
}

type censusBuilder struct {
	ctx                        context.Context
	c                          *LocalTreeCensus
	acl, settings              []byte
	heads, changes, aclRecords map[string]int
	err                        error
}

// LocalTreeCensus performs no live read, transaction, capability acquisition,
// export, file fetch, signature validation, document replay or migration.
// Its authority describes the old capture checkpoint, not a current account.
func (w *Witness) LocalTreeCensus(ctx context.Context, limits CensusLimits) (*LocalTreeCensus, error) {
	if ctx == nil || w == nil || !w.complete {
		return nil, ErrIncompleteCensus
	}
	if !limits.valid() || w.rows > limits.MaxRows {
		return nil, ErrLimit
	}
	if err := ctx.Err(); err != nil {
		return nil, err
	}
	if w.binding.Authority != FixtureOnlyAuthority {
		return nil, ErrOwnership
	}
	h := sha256.New()
	if err := w.writePrivate(h); err != nil || hex.EncodeToString(h.Sum(nil)) != w.digest {
		return nil, ErrIncompleteCensus
	}
	state, err := w.collection("state").stringID(w.binding.SpaceID)
	if err != nil {
		return nil, ErrIncompleteCensus
	}
	acl, err := requiredString(state, "a")
	if err != nil {
		return nil, ErrIncompleteCensus
	}
	settings, err := requiredString(state, "s")
	if err != nil {
		return nil, ErrIncompleteCensus
	}
	c := &LocalTreeCensus{witness: w, limits: limits}
	b := &censusBuilder{ctx: ctx, c: c, acl: []byte(acl), settings: []byte(settings),
		heads: map[string]int{}, changes: map[string]int{}, aclRecords: map[string]int{}}
	for ci, col := range w.collections {
		if err := ctx.Err(); err != nil {
			return nil, err
		}
		known := col.name == "state" || col.name == "heads" || col.name == "changes" || col.name == acl
		if !known {
			code := "unknown_collection"
			if col.name == "_client" {
				code = "opaque_client_collection"
			}
			b.issue(ci, -1, nil, -1, code)
		}
		for ri, raw := range col.rows {
			if len(c.rows) >= limits.MaxRows {
				return nil, ErrLimit
			}
			v, err := anyenc.Parse(raw.value)
			if err != nil {
				return nil, ErrIncompleteCensus
			}
			identity, err := uniqueField(v, "id")
			if err != nil || !bytes.Equal(identity.MarshalTo(nil), raw.id) {
				return nil, ErrIncompleteCensus
			}
			n := len(c.rows)
			c.rows = append(c.rows, censusRow{collection: ci, ordinal: ri, nativeID: raw.id, kind: "unresolved_row", deleted: -1, derived: -1})
			b.classify(n, col.name, v, identity)
			if b.err != nil {
				return nil, b.err
			}
			if err := ctx.Err(); err != nil {
				return nil, err
			}
		}
	}
	if b.err != nil {
		return nil, b.err
	}
	if len(c.rows) != w.rows {
		return nil, ErrIncompleteCensus
	}
	b.resolve()
	if b.err != nil {
		return nil, b.err
	}
	if err := ctx.Err(); err != nil {
		return nil, err
	}
	h = sha256.New()
	count := &censusBoundedWriter{dst: h, limit: limits.MaxPrivateBytes}
	if err := c.writePrivate(count); err != nil {
		return nil, err
	}
	if err := ctx.Err(); err != nil {
		return nil, err
	}
	c.bytes = count.written
	c.digest = hex.EncodeToString(h.Sum(nil))
	c.complete = true
	return c, nil
}

func (b *censusBuilder) issue(collection, row int, field []byte, position int, code string) {
	if b.err != nil {
		return
	}
	if len(b.c.issues) >= b.c.limits.MaxIssues {
		b.err = ErrLimit
		return
	}
	b.c.issues = append(b.c.issues, censusIssue{collection: collection, row: row, field: field, position: position, code: code})
	if row >= 0 {
		b.c.rows[row].unresolved = true
	}
}

func (b *censusBuilder) rowIssue(row int, field string, position int, code string) {
	b.issue(b.c.rows[row].collection, row, []byte(field), position, code)
}

func (b *censusBuilder) fields(row int, v *anyenc.Value, allowed string) censusFields {
	f := censusFields{values: map[string][]*anyenc.Value{}}
	known := map[string]bool{}
	for _, name := range bytes.Fields([]byte(allowed)) {
		known[string(name)] = true
	}
	obj, err := v.Object()
	if err != nil {
		b.rowIssue(row, "", -1, "unsupported_row_shape")
		return f
	}
	position := 0
	obj.Visit(func(key []byte, value *anyenc.Value) {
		if b.err != nil {
			return
		}
		if err := b.ctx.Err(); err != nil {
			b.err = err
			return
		}
		name := string(key)
		if len(f.values[name]) == 0 {
			f.order = append(f.order, name)
		}
		f.values[name] = append(f.values[name], value)
		if !known[name] {
			b.rowIssue(row, name, position, "unknown_field")
		} else if len(f.values[name]) == 2 {
			b.rowIssue(row, name, position, "ambiguous_field")
		}
		position++
	})
	return f
}

func (b *censusBuilder) field(row int, f censusFields, name string, required bool) *anyenc.Value {
	values := f.values[name]
	if len(values) == 1 {
		return values[0]
	}
	if len(values) == 0 && required {
		b.rowIssue(row, name, -1, "missing_field")
	}
	return nil
}

func (b *censusBuilder) stringField(row int, f censusFields, name string, required, nonempty bool) []byte {
	v := b.field(row, f, name, required)
	if v == nil {
		return nil
	}
	raw, err := v.StringBytes()
	if err != nil || (nonempty && len(raw) == 0) {
		b.rowIssue(row, name, -1, "unsupported_string_field")
		return nil
	}
	return raw
}

func (b *censusBuilder) binaryField(row int, f censusFields, name string) {
	v := b.field(row, f, name, true)
	if v == nil {
		return
	}
	raw, err := v.Bytes()
	if err != nil || len(raw) == 0 {
		b.rowIssue(row, name, -1, "opaque_payload_shape")
	}
}

func (b *censusBuilder) numericMetadata(row int, f censusFields, names ...string) {
	for _, name := range names {
		v := b.field(row, f, name, false)
		if v != nil && v.Type() != anyenc.TypeNumber {
			b.rowIssue(row, name, -1, "unsupported_numeric_metadata")
		}
	}
	// Number bits remain in the original row. No uint64 conversion, global
	// watermark, timestamp, ordering or original-integer precision is inferred.
}

func (b *censusBuilder) ref(row int, field string, position int, kind, domain string, id, tree []byte) {
	if b.err != nil {
		return
	}
	if len(b.c.references) >= b.c.limits.MaxReferences {
		b.err = ErrLimit
		return
	}
	b.c.references = append(b.c.references, censusReference{row: row, position: position,
		target: -1, observed: -1, kind: kind, domain: domain, field: []byte(field),
		id: id, tree: tree, outcome: "not_in_capture"})
}

func (b *censusBuilder) stringArrayRefs(row int, f censusFields, name string, required bool, kind, domain string, tree []byte) {
	v := b.field(row, f, name, required)
	if v == nil {
		return
	}
	values, err := v.Array()
	if err != nil {
		b.rowIssue(row, name, -1, "unsupported_reference_array")
		return
	}
	if required && len(values) == 0 {
		b.rowIssue(row, name, -1, "empty_head_list")
	}
	seen := map[string]bool{}
	for i, value := range values {
		if b.err != nil {
			return
		}
		if err := b.ctx.Err(); err != nil {
			b.err = err
			return
		}
		raw, err := value.StringBytes()
		if err != nil || len(raw) == 0 {
			b.rowIssue(row, name, i, "unsupported_reference_identity")
			continue
		}
		if seen[string(raw)] {
			b.rowIssue(row, name, i, "duplicate_reference")
		}
		seen[string(raw)] = true
		b.ref(row, name, i, kind, domain, raw, tree)
	}
	if domain == "acl" && name == "h" && len(values) != 1 {
		b.rowIssue(row, name, -1, "acl_head_cardinality")
	}
}

func (b *censusBuilder) addIdentity(index map[string]int, id []byte, row int) {
	if len(id) == 0 {
		return
	}
	if _, found := index[string(id)]; found {
		b.err = ErrIncompleteCensus
		return
	}
	index[string(id)] = row
}

func (b *censusBuilder) classify(row int, collection string, v, identity *anyenc.Value) {
	r := &b.c.rows[row]
	if collection != "state" && collection != "heads" && collection != "changes" && collection != string(b.acl) {
		r.kind = "unknown_collection_row"
		if collection == "_client" {
			r.kind = "opaque_client_row"
		}
		r.unresolved = true
		return
	}
	id, err := identity.StringBytes()
	if err != nil || len(id) == 0 {
		b.rowIssue(row, "id", -1, "unsupported_native_identity")
		return
	}
	r.id = id
	switch collection {
	case "state":
		r.kind = "space_state"
		f := b.fields(row, v, "id a s e nh oh h")
		a := b.stringField(row, f, "a", true, true)
		s := b.stringField(row, f, "s", true, true)
		b.binaryField(row, f, "e")
		if !bytes.Equal(id, []byte(b.c.witness.binding.SpaceID)) || !bytes.Equal(a, b.acl) || !bytes.Equal(s, b.settings) {
			b.err = ErrIncompleteCensus
			return
		}
		b.ref(row, "a", -1, "state_acl_head", "acl_head", a, nil)
		b.ref(row, "a", -1, "state_acl_root", "acl_root", a, nil)
		b.ref(row, "s", -1, "state_settings_head", "tree_head", s, nil)
		b.ref(row, "s", -1, "state_settings_root", "tree_root", s, s)
	case "heads":
		r.kind = "tree_head"
		domain := "change"
		if bytes.Equal(id, b.acl) {
			r.kind, domain = "acl_head", "acl"
		}
		b.addIdentity(b.heads, id, row)
		f := b.fields(row, v, "id h s d r p q")
		b.stringArrayRefs(row, f, "h", true, "head", domain, id)
		if r.kind == "tree_head" {
			b.ref(row, "id", -1, "tree_root", "tree_root", id, id)
		}
		if value := b.stringField(row, f, "s", false, false); len(value) > 0 {
			if r.kind == "acl_head" {
				b.rowIssue(row, "s", -1, "acl_tree_metadata")
			} else {
				b.ref(row, "s", -1, "common_snapshot", "change", value, id)
			}
		}
		if value := b.stringField(row, f, "p", false, false); len(value) > 0 {
			if r.kind == "acl_head" {
				b.rowIssue(row, "p", -1, "acl_tree_metadata")
			} else {
				b.ref(row, "p", -1, "parent_tree", "tree_head", value, nil)
			}
		}
		if value := b.field(row, f, "d", false); value != nil {
			d, err := value.Float64()
			if err != nil || math.IsNaN(d) || math.IsInf(d, 0) || d != math.Trunc(d) || d < 0 || d > 2 {
				b.rowIssue(row, "d", -1, "unknown_deletion_state")
			} else {
				r.deleted = int(d)
			}
		}
		if value := b.field(row, f, "r", false); value != nil {
			switch value.Type() {
			case anyenc.TypeTrue:
				r.derived = 1
			case anyenc.TypeFalse:
				r.derived = 0
			default:
				b.rowIssue(row, "r", -1, "unsupported_derived_state")
			}
		}
		b.numericMetadata(row, f, "q")
	case "changes":
		b.addIdentity(b.changes, id, row)
		f := b.fields(row, v, "id t r p i o sz sc a q")
		tree := b.stringField(row, f, "t", true, true)
		if len(tree) == 0 {
			return
		}
		r.tree, r.kind = tree, "tree_change"
		if bytes.Equal(id, tree) {
			r.kind = "tree_root"
		}
		b.binaryField(row, f, "r")
		b.stringField(row, f, "o", false, false)
		b.numericMetadata(row, f, "sz", "sc", "a", "q")
		b.ref(row, "t", -1, "change_tree_head", "tree_head", tree, nil)
		b.stringArrayRefs(row, f, "p", false, "predecessor", "change", tree)
		if value := b.stringField(row, f, "i", false, false); len(value) > 0 {
			b.ref(row, "i", -1, "snapshot_base", "change", value, tree)
		}
	default: // Exact ACL collection from the captured, bound state row.
		r.kind = "acl_record"
		if bytes.Equal(id, b.acl) {
			r.kind = "acl_root"
		}
		b.addIdentity(b.aclRecords, id, row)
		f := b.fields(row, v, "id r p o sz")
		b.binaryField(row, f, "r")
		b.numericMetadata(row, f, "o", "sz")
		if value := b.stringField(row, f, "p", false, false); len(value) > 0 {
			b.ref(row, "p", -1, "acl_predecessor", "acl", value, nil)
		}
	}
}

func (b *censusBuilder) resolve() {
	for i := range b.c.references {
		if err := b.ctx.Err(); err != nil {
			b.err = err
			return
		}
		ref := &b.c.references[i]
		index := b.changes
		switch ref.domain {
		case "tree_head", "acl_head":
			index = b.heads
		case "acl", "acl_root":
			index = b.aclRecords
		}
		target, found := index[string(ref.id)]
		if found {
			ref.observed = target
			row := b.c.rows[target]
			switch {
			case ref.domain == "tree_head" && row.kind != "tree_head":
				ref.outcome = "wrong_namespace"
			case ref.domain == "acl_head" && row.kind != "acl_head":
				ref.outcome = "wrong_namespace"
			case ref.domain == "acl_root" && row.kind != "acl_root":
				ref.outcome = "wrong_root"
			case (ref.domain == "change" || ref.domain == "tree_root") && len(row.tree) == 0:
				ref.outcome = "target_unresolved"
			case (ref.domain == "change" || ref.domain == "tree_root") && !bytes.Equal(row.tree, ref.tree):
				ref.outcome = "cross_tree"
			case ref.domain == "tree_root" && row.kind != "tree_root":
				ref.outcome = "wrong_root"
			default:
				ref.outcome, ref.target = "resolved_identity_only", target
			}
		}
		if ref.target < 0 {
			b.rowIssue(ref.row, string(ref.field), ref.position, ref.outcome)
		}
		if b.err != nil {
			return
		}
	}
}

func censusCounts(values map[string]int) []CensusCount {
	keys := make([]string, 0, len(values))
	for k := range values {
		keys = append(keys, k)
	}
	sort.Strings(keys)
	out := make([]CensusCount, 0, len(keys))
	for _, k := range keys {
		out = append(out, CensusCount{Kind: k, Count: values[k]})
	}
	return out
}

func (c *LocalTreeCensus) Receipt() (CensusReceipt, error) {
	if c == nil || !c.complete || c.witness == nil || !c.witness.complete {
		return CensusReceipt{}, ErrIncompleteCensus
	}
	wr, err := c.witness.Receipt()
	if err != nil {
		return CensusReceipt{}, err
	}
	r := CensusReceipt{Version: "native-local-tree-storage-census-v1", Scope: "captured-local-tree-storage-only",
		Authority: wr.Authority, Representation: wr.Encoding, SourceWitnessSHA256: wr.WitnessSHA256,
		CensusSHA256: c.digest, OwnerSHA256: wr.OwnerSHA256, SpaceSHA256: wr.SpaceSHA256, Generation: wr.Generation,
		Collections: len(c.witness.collections), Rows: len(c.rows), References: len(c.references),
		Issues: len(c.issues), PrivateBytes: c.bytes, AllCapturedRowsAccounted: len(c.rows) == wr.Rows,
		NativeSnapshotProofRequired: true, NativeIdentityCensusRequired: true}
	kinds, issues := map[string]int{}, map[string]int{}
	for _, col := range c.witness.collections {
		if len(col.rows) == 0 {
			r.EmptyCollections++
		}
	}
	for _, row := range c.rows {
		kinds[row.kind]++
		if row.unresolved {
			r.UnresolvedRows++
		}
	}
	for _, ref := range c.references {
		if ref.target >= 0 {
			r.ResolvedReferences++
		}
	}
	for _, issue := range c.issues {
		issues[issue.code]++
		if issue.code == "unknown_collection" {
			r.UnknownCollections++
		}
	}
	r.AllRecognizedReferencesResolved = r.ResolvedReferences == r.References && r.UnresolvedRows == 0 && r.UnknownCollections == 0
	r.RowsByKind, r.IssuesByCode = censusCounts(kinds), censusCounts(issues)
	return r, nil
}

// String intentionally contains no native ID, collection name, payload or nonce.
func (c LocalTreeCensus) String() string {
	return fmt.Sprintf("LocalTreeCensus{rows:%d references:%d issues:%d sha256:%s}", len(c.rows), len(c.references), len(c.issues), c.digest)
}
