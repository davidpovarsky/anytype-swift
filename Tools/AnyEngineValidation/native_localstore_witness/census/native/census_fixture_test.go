//go:build pinkha_localstore_witness

package localstorewitness

import (
	"bytes"
	"context"
	"encoding/binary"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"testing"

	anystore "github.com/anyproto/any-store"
	"github.com/anyproto/any-store/anyenc"
	"github.com/anyproto/any-store/query"
	"github.com/anyproto/any-sync/commonspace/object/tree/objecttree"
	"github.com/anyproto/any-sync/commonspace/object/tree/treechangeproto"
	"github.com/anyproto/any-sync/commonspace/object/tree/treestorage"
	nativecrypto "github.com/anyproto/any-sync/util/crypto"
)

// These fixtures use native storage APIs, not a Heart Object creation or ACL
// authorization claim. Their signed storage payloads remain opaque to census.
type censusNativeTree struct {
	store   objecttree.Storage
	root    *treechangeproto.RawTreeChangeWithId
	key     nativecrypto.PrivKey
	builder objecttree.ChangeBuilder
	aclHead string
	next    int
}

func newCensusNativeTree(t *testing.T, f *fixture, seed, parent string) *censusNativeTree {
	t.Helper()
	ctx := context.Background()
	key, _, err := nativecrypto.GenerateRandomEd25519KeyPair()
	must(t, err)
	acl, err := f.storage.AclStorage()
	must(t, err)
	head, err := acl.Head(ctx)
	must(t, err)
	builder := objecttree.NewChangeBuilder(nativecrypto.NewKeyStorage(), nil)
	var root *treechangeproto.RawTreeChangeWithId
	if parent == "" {
		_, root, err = builder.BuildRoot(objecttree.InitialContent{
			AclHeadId: head, PrivKey: key, SpaceId: f.storage.Id(), Seed: []byte(seed),
			ChangeType: "census-opaque-storage-fixture-v1", ChangePayload: []byte("private-census-" + seed), Timestamp: 1})
	} else {
		_, root, err = builder.BuildDerivedRoot(objecttree.InitialDerivedContent{
			SpaceId: f.storage.Id(), ParentId: parent, ChangeType: "census-opaque-storage-fixture-v1",
			ChangePayload: []byte("private-census-derived-" + seed)})
	}
	must(t, err)
	store, err := f.storage.CreateTreeStorage(ctx, treestorage.TreeStorageCreatePayload{RootRawChange: root})
	must(t, err)
	return &censusNativeTree{store: store, root: root, key: key, aclHead: head,
		builder: objecttree.NewChangeBuilder(nativecrypto.NewKeyStorage(), root)}
}

func appendCensusNativeChange(t *testing.T, tree *censusNativeTree, payload string) string {
	t.Helper()
	ctx := context.Background()
	heads, err := tree.store.Heads(ctx)
	must(t, err)
	tree.next++
	_, raw, err := tree.builder.Build(objecttree.BuilderContent{
		TreeHeadIds: heads, AclHeadId: tree.aclHead, SnapshotBaseId: tree.root.Id,
		PrivKey: tree.key, Unencrypted: true, Content: []byte(payload), Timestamp: int64(tree.next + 1),
		DataType: "opaque-census-fixture"})
	must(t, err)
	root, err := tree.store.Root(ctx)
	must(t, err)
	change := objecttree.StorageChange{
		Id: raw.Id, RawChange: raw.RawChange, PrevIds: heads, SnapshotId: tree.root.Id,
		SnapshotCounter: 1, ChangeSize: len(raw.RawChange), OrderId: root.OrderId + fmt.Sprintf("c%06d", tree.next)}
	must(t, tree.store.AddAll(ctx, []objecttree.StorageChange{change}, []string{raw.Id}, tree.root.Id))
	return raw.Id
}

func censusCapture(t *testing.T, f *fixture, db anystore.DB) (*Witness, *LocalTreeCensus) {
	t.Helper()
	w, err := Capture(context.Background(), f.capability(db), DefaultLimits())
	must(t, err)
	c, err := w.LocalTreeCensus(context.Background(), DefaultCensusLimits())
	must(t, err)
	return w, c
}

func censusModify(t *testing.T, f *fixture, collection string, id any, update func(*anyenc.Arena, *anyenc.Value)) {
	t.Helper()
	coll, err := f.db.OpenCollection(context.Background(), collection)
	must(t, err)
	_, err = coll.UpdateId(context.Background(), id, query.ModifyFunc(func(a *anyenc.Arena, v *anyenc.Value) (*anyenc.Value, bool, error) {
		update(a, v)
		return v, true, nil
	}))
	must(t, err)
}

func censusInsert(t *testing.T, f *fixture, collection string, value *anyenc.Value) {
	t.Helper()
	coll, err := f.db.OpenCollection(context.Background(), collection)
	must(t, err)
	must(t, coll.Insert(context.Background(), value))
}

func censusIssueCount(c *LocalTreeCensus, code string) int {
	count := 0
	for _, issue := range c.issues {
		if issue.code == code {
			count++
		}
	}
	return count
}

func censusRowFor(t *testing.T, c *LocalTreeCensus, collection, id string) censusRow {
	t.Helper()
	for _, row := range c.rows {
		if c.witness.collections[row.collection].name == collection && bytes.Equal(row.id, []byte(id)) {
			return row
		}
	}
	t.Fatal("expected typed native row missing")
	return censusRow{}
}

func censusReferenceOutcome(c *LocalTreeCensus, kind, id, outcome string) bool {
	for _, ref := range c.references {
		if ref.kind == kind && bytes.Equal(ref.id, []byte(id)) && ref.outcome == outcome {
			return true
		}
	}
	return false
}

func censusDuplicateField(t *testing.T, value *anyenc.Value, name string, extra *anyenc.Value) *anyenc.Value {
	t.Helper()
	raw := value.MarshalTo(nil)
	if len(raw) < 2 || raw[0] != byte(anyenc.TypeObject) || raw[len(raw)-1] != 0 {
		t.Fatal("expected native object encoding")
	}
	raw = append(raw[:len(raw)-1], []byte(name)...)
	raw = append(raw, 0)
	raw = extra.MarshalTo(raw)
	raw = append(raw, 0)
	result, err := anyenc.Parse(raw)
	must(t, err)
	return result
}

func censusReadFrame(t *testing.T, r *bytes.Reader) []byte {
	t.Helper()
	var size [8]byte
	_, err := io.ReadFull(r, size[:])
	must(t, err)
	n := binary.BigEndian.Uint64(size[:])
	if n > uint64(r.Len()) {
		t.Fatal("private census frame exceeds original container")
	}
	raw := make([]byte, int(n))
	_, err = io.ReadFull(r, raw)
	must(t, err)
	return raw
}

func retainCensusPrivate(t *testing.T, f *fixture, label string, w *Witness, c *LocalTreeCensus) {
	t.Helper()
	var original, encoded bytes.Buffer
	must(t, w.WritePrivate(&original))
	must(t, c.WritePrivate(&encoded))
	reader := bytes.NewReader(encoded.Bytes())
	if string(censusReadFrame(t, reader)) != "pinkha-local-tree-storage-census-v1" ||
		string(censusReadFrame(t, reader)) != "local-structural-identities-no-source-admission" ||
		string(censusReadFrame(t, reader)) != w.digest ||
		!bytes.Equal(censusReadFrame(t, reader), original.Bytes()) {
		t.Fatal("private census lost exact original witness binding")
	}
	for _, value := range []struct {
		suffix string
		data   []byte
	}{
		{".witness.bin", original.Bytes()}, {".census.bin", encoded.Bytes()},
	} {
		path := filepath.Join(f.root, label+value.suffix)
		file, err := os.OpenFile(path, os.O_CREATE|os.O_EXCL|os.O_WRONLY, 0600)
		must(t, err)
		n, writeErr := file.Write(value.data)
		closeErr := file.Close()
		must(t, writeErr)
		must(t, closeErr)
		if n != len(value.data) {
			t.Fatal("private evidence short write")
		}
		info, err := os.Lstat(path)
		must(t, err)
		if !info.Mode().IsRegular() || info.Mode().Perm() != 0600 {
			t.Fatal("private census evidence permissions differ")
		}
	}
	receipt, err := c.Receipt()
	must(t, err)
	safe, err := json.Marshal(receipt)
	must(t, err)
	fmt.Printf("LOCAL_TREE_CENSUS_RECEIPT %s %s\n", label, safe)
}

type censusShortWriter struct{}

func (censusShortWriter) Write(raw []byte) (int, error) { return 0, nil }
